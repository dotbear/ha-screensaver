#!/usr/bin/env python3
"""
Home Assistant Screensaver - Python Flask Application

A web server that serves a screensaver application for Home Assistant.
It displays the HA dashboard and switches to a photo slideshow after idle time.
"""

import hashlib
import os
import json
import logging
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Dict, Any, Optional, Tuple

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import safe_join

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app)

CONFIG_FILE = Path("/app/config.json")
if not CONFIG_FILE.exists():
    CONFIG_FILE = Path("config.json")

DEFAULT_CONFIG = {
    "home_assistant_url": "http://homeassistant:8123",
    "photos_folder": "/media",
    "photos_source": "media",
    "idle_timeout_seconds": 60,
    "slide_interval_seconds": 5,
    "clock_position": "bottom-center",
    "weather_entity": "",
    "media_player_entity": "",
    "media_player_sources": "",
    "night_mode_enabled": True,
    "night_mode_start": "21:00",
    "night_mode_end": "05:00",
    "night_mode_brightness": 15,
    "motion_photos_enabled": True
}


# ============================================================================
# PHOTO FORMATS AND DERIVED-FILE CACHE
# ============================================================================

# HEIC/HEIF is listed here but no browser renders it, so those files are
# decoded to JPEG on demand (see heif_jpeg)
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}
HEIF_EXTENSIONS = {'.heic', '.heif'}
JPEG_EXTENSIONS = {'.jpg', '.jpeg'}

# Sidecar clips for iOS Live Photos (IMG_0001.HEIC next to IMG_0001.MOV)
VIDEO_EXTENSIONS = ('.mov', '.MOV', '.mp4', '.MP4', '.m4v', '.M4V')

# Decoded stills and motion clips are written here rather than back into the
# user's media folder. /app is the add-on container; ./cache is local dev.
APP_DIR = Path("/app") if Path("/app").is_dir() else Path(".")
CACHE_DIR = APP_DIR / "cache"
CACHE_MAX_BYTES = 2 * 1024 * 1024 * 1024

HEIF_JPEG_QUALITY = 90

# Motion photos: "Live" on iOS (a sidecar .MOV), "Motion" on Android (an MP4
# appended to the still itself)
MOTION_MIN_FILE_BYTES = 256 * 1024      # nothing smaller holds a video
MOTION_MIN_OFFSET = 512                 # a clip never starts at the very top
MOTION_XMP_HEAD_BYTES = 256 * 1024      # where Google writes its XMP marker
MOTION_TAIL_SCAN_BYTES = 12 * 1024 * 1024
MOTION_MAX_BOXES = 64
MOTION_MAX_CANDIDATES = 8
MOTION_SNIFF_BYTES = 1024 * 1024
MOTION_MAX_SECONDS = 6
MOTION_MAX_EDGE = 1280

# Both decoders are optional -- the add-on image ships them, a bare checkout
# used for local development may not have them
HEIF_CONVERT_BIN = shutil.which('heif-convert')
FFMPEG_BIN = shutil.which('ffmpeg')

if not HEIF_CONVERT_BIN:
    logger.warning("heif-convert not found - HEIC/HEIF photos will be skipped")
if not FFMPEG_BIN:
    logger.warning("ffmpeg not found - motion clips are served untranscoded")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file, or return defaults if file doesn't exist."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return {**DEFAULT_CONFIG, **config}
        return DEFAULT_CONFIG.copy()
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load config: {e}")
        return DEFAULT_CONFIG.copy()


def _gps_to_decimal(coords, ref) -> Optional[float]:
    """Convert GPS EXIF coordinates (degrees, minutes, seconds) to decimal."""
    if not coords or not ref:
        return None
    try:
        degrees = float(coords[0])
        minutes = float(coords[1])
        seconds = float(coords[2])
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in ('S', 'W'):
            decimal = -decimal
        return decimal
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def extract_exif(file_path: str) -> Dict[str, Any]:
    """Extract date taken and raw GPS coordinates from image EXIF data."""
    if not HAS_PILLOW:
        return {}
    try:
        img = Image.open(file_path)
        exif_data = img._getexif()
        if not exif_data:
            return {}

        result = {}

        # DateTimeOriginal (EXIF tag 36867)
        date_taken = exif_data.get(36867)
        if date_taken:
            try:
                dt = datetime.strptime(date_taken, "%Y:%m:%d %H:%M:%S")
                result['date'] = f"{dt.strftime('%B')} {dt.day}, {dt.year}"
            except (ValueError, TypeError):
                pass

        # GPSInfo (EXIF tag 34853) -- return raw coordinates for geocoding
        gps_info = exif_data.get(34853)
        if gps_info:
            lat = _gps_to_decimal(gps_info.get(2), gps_info.get(1))
            lng = _gps_to_decimal(gps_info.get(4), gps_info.get(3))
            if lat is not None and lng is not None:
                result['lat'] = lat
                result['lng'] = lng

        return result
    except Exception:
        return {}


# --------------- Reverse geocoding with disk cache ---------------

GEOCACHE_FILE = Path("/app/geocache.json")


def _load_geocache() -> Dict[str, Optional[str]]:
    try:
        if GEOCACHE_FILE.exists():
            with open(GEOCACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_geocache(cache: Dict[str, Optional[str]]) -> None:
    try:
        GEOCACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GEOCACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def _nominatim_reverse(lat: float, lng: float) -> Optional[str]:
    """Reverse-geocode via OpenStreetMap Nominatim (free, no API key)."""
    try:
        url = (
            f"https://nominatim.openstreetmap.org/reverse?"
            f"format=json&lat={lat}&lon={lng}&zoom=10&accept-language=en"
        )
        req = urllib.request.Request(url, headers={
            'User-Agent': 'HAScreensaver/1.1'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        addr = data.get('address', {})
        city = (addr.get('city') or addr.get('town') or
                addr.get('village') or addr.get('hamlet') or
                addr.get('municipality') or '')
        country = addr.get('country', '')

        if city and country:
            return f"{city}, {country}"
        return city or country or None
    except Exception as e:
        logger.warning(f"Reverse geocoding failed for {lat},{lng}: {e}")
        return None


def _format_coords(lat: float, lng: float) -> str:
    """Fallback: format coordinates as a human-readable string."""
    lat_dir = 'N' if lat >= 0 else 'S'
    lng_dir = 'E' if lng >= 0 else 'W'
    return f"{abs(lat):.1f}\u00b0{lat_dir}, {abs(lng):.1f}\u00b0{lng_dir}"


# ============================================================================
# HEIC STILLS AND MOTION PHOTOS
# ============================================================================

def _cache_key(path: Path) -> Optional[str]:
    """Stable id for a source file that changes whenever the file does."""
    try:
        stat = path.stat()
    except OSError:
        return None
    raw = f"{path}|{stat.st_size}|{int(stat.st_mtime)}"
    return hashlib.sha1(raw.encode('utf-8', 'replace')).hexdigest()


def _cache_file(name: str) -> Path:
    """Path inside the derived-file cache. Names are hashes we generate."""
    return CACHE_DIR / name


def _prune_cache() -> None:
    """Drop the oldest derived files once the cache passes its size cap."""
    try:
        entries = []
        total = 0
        for path in CACHE_DIR.iterdir():
            try:
                stat = path.stat()
            except OSError:
                continue
            entries.append((stat.st_mtime, stat.st_size, path))
            total += stat.st_size

        if total <= CACHE_MAX_BYTES:
            return

        for _, size, path in sorted(entries):
            if total <= CACHE_MAX_BYTES:
                break
            try:
                path.unlink()
                total -= size
            except OSError:
                pass
        logger.info(f"Pruned derived-file cache to {total // (1024 * 1024)} MB")
    except OSError:
        pass


def _ensure_cache_dir() -> bool:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        logger.error(f"Cannot create cache directory {CACHE_DIR}: {e}")
        return False


def _run_tool(command: List[str], timeout: int) -> bool:
    """Run an external decoder, logging rather than raising on failure."""
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        logger.warning(f"{command[0]} timed out after {timeout}s")
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b'').decode('utf-8', 'replace').strip()
        logger.warning(f"{command[0]} failed: {stderr[-300:]}")
    except OSError as e:
        logger.warning(f"Could not run {command[0]}: {e}")
    return False


def heif_jpeg(path: Path, decode: bool = True) -> Optional[Path]:
    """
    Return a cached JPEG rendering of a HEIC/HEIF file.

    heif-convert carries the EXIF block across intact, so the cached JPEG is
    also what the EXIF reader gets pointed at. With decode=False this only
    reports an already-converted file, which keeps the photo scan fast --
    decoding happens when the browser actually asks for the image.
    """
    key = _cache_key(path)
    if key is None:
        return None

    cached = _cache_file(f"{key}.jpg")
    if cached.exists():
        return cached
    if not decode or not HEIF_CONVERT_BIN or not _ensure_cache_dir():
        return None

    # libheif refuses a file whose trailing bytes aren't part of the image, so
    # a HEIF motion photo has to have its clip trimmed off before decoding
    source = path
    trimmed = None
    clip_offset = _find_embedded_video(path)
    if clip_offset is not None:
        trimmed = _cache_file(f"{key}.{os.getpid()}.still.heic")
        if _copy_span(path, 0, clip_offset, trimmed):
            source = trimmed
        else:
            trimmed = None

    # heif-convert picks its encoder from the suffix, so the scratch file has
    # to keep a .jpg ending. Files holding several images are written out as
    # <stem>-1.jpg, <stem>-2.jpg ... and no <stem>.jpg at all.
    stem = f"{key}.{os.getpid()}.tmp"
    scratch = _cache_file(f"{stem}.jpg")
    decoded = _run_tool(
        [HEIF_CONVERT_BIN, '-q', str(HEIF_JPEG_QUALITY), str(source), str(scratch)],
        timeout=120
    )
    if trimmed is not None:
        trimmed.unlink(missing_ok=True)
    if not decoded:
        scratch.unlink(missing_ok=True)
        return None

    extras = sorted(CACHE_DIR.glob(f"{stem}-*.jpg"))
    produced = scratch if scratch.exists() else (extras.pop(0) if extras else None)
    for extra in extras:
        extra.unlink(missing_ok=True)

    if produced is None:
        logger.warning(f"heif-convert produced no output for {path.name}")
        return None

    try:
        os.replace(produced, cached)
    except OSError as e:
        logger.warning(f"Could not store converted {path.name}: {e}")
        produced.unlink(missing_ok=True)
        return None

    _prune_cache()
    return cached


# --------------- Motion photo discovery ---------------

# Google records the clip length in XMP; the clip is always the file's tail
_MICRO_VIDEO_RE = re.compile(rb'MicroVideoOffset["\s>=]+(\d+)')
_MOTION_ITEM_RE = re.compile(
    rb'Item:Mime="video/[\w.+-]+"[^>]{0,240}Item:Length="(\d+)"'
    rb'|Item:Length="(\d+)"[^>]{0,240}Item:Mime="video/[\w.+-]+"'
)
_BOX_TYPE_RE = re.compile(rb'[A-Za-z0-9 _.-]{4}')


def _iter_boxes(handle, start: int, size: int) -> Iterator[Tuple[int, bytes, int]]:
    """Yield (offset, type, length) for top-level ISOBMFF boxes from start."""
    position = start
    for _ in range(MOTION_MAX_BOXES):
        if position >= size:
            return
        handle.seek(position)
        header = handle.read(8)
        if len(header) < 8:
            return
        box_size = int.from_bytes(header[:4], 'big')
        box_type = header[4:8]
        if not _BOX_TYPE_RE.fullmatch(box_type):
            return
        if box_size == 1:                       # 64-bit extended size
            extended = handle.read(8)
            if len(extended) < 8:
                return
            box_size = int.from_bytes(extended, 'big')
        elif box_size == 0:                     # box runs to end of file
            box_size = size - position
        if box_size < 8 or position + box_size > size:
            return
        yield position, box_type, box_size
        position += box_size


def _is_mp4_to_eof(handle, offset: int, size: int) -> bool:
    """True when a complete MP4 box chain starts at offset and fills the file."""
    end = -1
    has_media = False
    first = True
    for position, box_type, box_size in _iter_boxes(handle, offset, size):
        if first:
            if box_type != b'ftyp':
                return False
            first = False
        if box_type in (b'moov', b'mdat'):
            has_media = True
        end = position + box_size
    return has_media and end == size


def _find_embedded_video(path: Path) -> Optional[int]:
    """
    Byte offset of an MP4 stored inside a still image, or None.

    Android "Motion Photos" append the clip after the image. HEIF files are
    box containers, so a second 'ftyp' box gives the offset directly; for
    JPEG the file simply grows past its end-of-image marker.
    """
    try:
        size = path.stat().st_size
        if size < MOTION_MIN_FILE_BYTES:
            return None

        suffix = path.suffix.lower()
        with open(path, 'rb') as handle:
            if suffix in HEIF_EXTENSIONS:
                for position, box_type, _ in _iter_boxes(handle, 0, size):
                    if position > 0 and box_type == b'ftyp':
                        return position if _is_mp4_to_eof(handle, position, size) else None
                return None

            if suffix not in JPEG_EXTENSIONS:
                return None

            handle.seek(size - 2)
            if handle.read(2) == b'\xff\xd9':
                return None                     # ends cleanly, nothing appended

            handle.seek(0)
            head = handle.read(MOTION_XMP_HEAD_BYTES)
            for match in (_MICRO_VIDEO_RE.search(head), _MOTION_ITEM_RE.search(head)):
                if not match:
                    continue
                length = int(next(group for group in match.groups() if group))
                offset = size - length
                if offset >= MOTION_MIN_OFFSET and _is_mp4_to_eof(handle, offset, size):
                    return offset

            # No usable XMP (Samsung, older tools): find the appended header
            window_start = max(0, size - MOTION_TAIL_SCAN_BYTES)
            handle.seek(window_start)
            tail = handle.read(size - window_start)
            index = tail.rfind(b'ftyp')
            for _ in range(MOTION_MAX_CANDIDATES):
                if index < 0:
                    break
                offset = window_start + index - 4
                if offset >= MOTION_MIN_OFFSET and _is_mp4_to_eof(handle, offset, size):
                    return offset
                index = tail.rfind(b'ftyp', 0, index)
    except OSError as e:
        logger.warning(f"Could not scan {path.name} for motion: {e}")
    return None


def sidecar_video(image_path: Path) -> Optional[Path]:
    """iOS Live Photos land as IMG_0001.HEIC alongside IMG_0001.MOV."""
    for extension in VIDEO_EXTENSIONS:
        candidate = image_path.with_suffix(extension)
        if candidate.is_file():
            return candidate
    return None


MOTIONCACHE_FILE = APP_DIR / "motioncache.json"


def _load_motioncache() -> Dict[str, int]:
    try:
        if MOTIONCACHE_FILE.exists():
            with open(MOTIONCACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_motioncache(cache: Dict[str, int]) -> None:
    try:
        MOTIONCACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MOTIONCACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def _has_motion(path: Path, cache: Dict[str, int], seen: Dict[str, int]) -> bool:
    """
    Whether a photo has motion to play, reusing the on-disk scan results.

    Reading a file to look for an appended clip is the expensive part, so the
    offset (or -1 for "none") is remembered per file version.
    """
    if sidecar_video(path) is not None:
        return True

    key = _cache_key(path)
    if key is None:
        return False
    if key in cache:
        offset = cache[key]
    else:
        found = _find_embedded_video(path)
        offset = -1 if found is None else found
    seen[key] = offset
    return offset >= 0


# --------------- Motion clip delivery ---------------

def _sniff_video_codec(source: Path) -> str:
    """Phones write their moov box at either end, so check both."""
    try:
        size = source.stat().st_size
        with open(source, 'rb') as handle:
            chunk = handle.read(MOTION_SNIFF_BYTES)
            if size > MOTION_SNIFF_BYTES:
                handle.seek(max(MOTION_SNIFF_BYTES, size - MOTION_SNIFF_BYTES))
                chunk += handle.read(MOTION_SNIFF_BYTES)
    except OSError:
        return ''
    if b'hvc1' in chunk or b'hev1' in chunk:
        return 'hevc'
    if b'avc1' in chunk:
        return 'h264'
    return ''


def _copy_span(path: Path, start: int, length: Optional[int], dest: Path) -> bool:
    """Copy a byte range out of a file; length=None runs to the end."""
    try:
        with open(path, 'rb') as source, open(dest, 'wb') as out:
            source.seek(start)
            if length is None:
                shutil.copyfileobj(source, out)
            else:
                remaining = length
                while remaining > 0:
                    chunk = source.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)
        return True
    except OSError as e:
        logger.warning(f"Could not read part of {path.name}: {e}")
        dest.unlink(missing_ok=True)
        return False


def _normalise_clip(source: Path, key: str, dest: Path) -> Optional[Path]:
    """
    Rewrap (or transcode) a motion clip into an MP4 browsers will play.

    iPhone Live Photos are HEVC, which most non-Apple browsers refuse, so
    those are re-encoded to H.264; H.264 sources are only remuxed.
    """
    scratch = _cache_file(f"{key}.{os.getpid()}.tmp.mp4")

    if FFMPEG_BIN:
        command = [
            FFMPEG_BIN, '-nostdin', '-loglevel', 'error', '-y',
            '-i', str(source), '-an', '-t', str(MOTION_MAX_SECONDS),
            '-movflags', '+faststart'
        ]
        if _sniff_video_codec(source) == 'h264':
            command += ['-c:v', 'copy']
        else:
            command += [
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-vf', (f"scale='if(gt(iw,ih),min({MOTION_MAX_EDGE},iw),-2)'"
                        f":'if(gt(iw,ih),-2,min({MOTION_MAX_EDGE},ih))'")
            ]
        command.append(str(scratch))
        if not _run_tool(command, timeout=180):
            scratch.unlink(missing_ok=True)
            return None
    else:
        # Without ffmpeg, hand the clip over untouched and let the browser try
        try:
            shutil.copyfile(source, scratch)
        except OSError as e:
            logger.warning(f"Could not stage motion clip: {e}")
            return None

    try:
        os.replace(scratch, dest)
    except OSError as e:
        logger.warning(f"Could not store motion clip: {e}")
        scratch.unlink(missing_ok=True)
        return None

    _prune_cache()
    return dest


def motion_clip(image_path: Path) -> Optional[Path]:
    """Cached, browser-playable MP4 of a photo's motion, or None."""
    key = _cache_key(image_path)
    if key is None:
        return None

    cached = _cache_file(f"{key}.mp4")
    if cached.exists():
        return cached
    if not _ensure_cache_dir():
        return None

    scratch = None
    source = sidecar_video(image_path)
    if source is None:
        offset = _find_embedded_video(image_path)
        if offset is None:
            return None
        scratch = _cache_file(f"{key}.{os.getpid()}.raw.mp4")
        if not _copy_span(image_path, offset, None, scratch):
            return None
        source = scratch

    try:
        return _normalise_clip(source, key, cached)
    finally:
        if scratch is not None:
            scratch.unlink(missing_ok=True)


def resolve_photo(folder: str, filename: str) -> Optional[Path]:
    """
    Resolve a requested photo name to a file inside the photos folder.

    safe_join is the same guard send_from_directory uses internally: it
    returns None for anything that would escape the folder.
    """
    if Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        return None
    joined = safe_join(folder, filename)
    if joined is None:
        return None
    return Path(joined)


# -----------------------------------------------------------------

def get_image_files(folder_path: str, motion_enabled: bool = True) -> List[Dict[str, Any]]:
    """
    Scan a folder for image files and return their URLs with EXIF metadata.
    GPS coordinates are reverse-geocoded to city/country names (cached to disk).

    HEIC/HEIF files are listed under their real name and decoded to JPEG when
    the browser requests them, so a folder full of iPhone photos doesn't hold
    the loading screen open while every one of them is converted up front.
    Their EXIF comes from the decoded copy, so it appears from the next scan
    onwards.
    """
    photos = []
    folder = Path(folder_path)

    if not folder.exists():
        logger.warning(f"Photos folder does not exist: {folder_path}")
        return []

    if not folder.is_dir():
        logger.warning(f"Photos path is not a directory: {folder_path}")
        return []

    try:
        motion_cache = _load_motioncache()
        seen_motion: Dict[str, int] = {}

        for file_path in folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in IMAGE_EXTENSIONS:
                    exif_source = file_path
                    if ext in HEIF_EXTENSIONS:
                        if not HEIF_CONVERT_BIN:
                            continue        # nothing here can render it
                        exif_source = heif_jpeg(file_path, decode=False)

                    photo = {
                        "url": f"/photos/{file_path.name}",
                        "exif": extract_exif(str(exif_source)) if exif_source else {}
                    }
                    if motion_enabled and _has_motion(file_path, motion_cache, seen_motion):
                        photo["motion_url"] = (
                            f"/api/motion/{urllib.parse.quote(file_path.name)}"
                        )
                    photos.append(photo)

        # Forget files that are gone or have changed since the last scan
        if motion_enabled and seen_motion != motion_cache:
            _save_motioncache(seen_motion)

        # Batch reverse-geocode any new GPS coordinates
        geocache = _load_geocache()
        needs_save = False

        for photo in photos:
            exif = photo.get('exif', {})
            lat, lng = exif.pop('lat', None), exif.pop('lng', None)
            if lat is None or lng is None:
                continue

            cache_key = f"{lat:.2f},{lng:.2f}"
            if cache_key not in geocache:
                geocache[cache_key] = _nominatim_reverse(lat, lng)
                needs_save = True
                time.sleep(1)  # Nominatim rate limit: 1 req/s

            location = geocache.get(cache_key)
            exif['location'] = location if location else _format_coords(lat, lng)

        if needs_save:
            _save_geocache(geocache)

        logger.info(f"Found {len(photos)} photos in {folder_path}")
        return sorted(photos, key=lambda p: p["url"])

    except PermissionError as e:
        logger.error(f"Permission denied reading folder {folder_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error scanning photos folder: {e}")
        return []


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/config', methods=['GET'])
def get_config():
    """GET /api/config - Return current configuration."""
    config = load_config()
    return jsonify(config)


@app.route('/api/photos', methods=['GET'])
def get_photos():
    """GET /api/photos - Return list of photo URLs with EXIF metadata."""
    config = load_config()
    photos_folder = config.get('photos_folder', '/media')
    photos = get_image_files(
        photos_folder,
        motion_enabled=config.get('motion_photos_enabled', True) is not False
    )
    return jsonify(photos)


@app.route('/api/weather', methods=['GET'])
def get_weather():
    """GET /api/weather - Proxy weather data from Home Assistant."""
    config = load_config()
    weather_entity = config.get('weather_entity', '')

    if not weather_entity:
        return jsonify(None)

    supervisor_token = os.environ.get('SUPERVISOR_TOKEN', '')
    if not supervisor_token:
        logger.warning("No SUPERVISOR_TOKEN available for weather API")
        return jsonify(None)

    try:
        url = f'http://supervisor/core/api/states/{weather_entity}'
        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {supervisor_token}',
            'Content-Type': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())

        attrs = data.get('attributes', {})
        return jsonify({
            'condition': data.get('state', ''),
            'temperature': attrs.get('temperature'),
            'temperature_unit': attrs.get('temperature_unit', '°C')
        })
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return jsonify(None)


@app.route('/api/media', methods=['GET'])
def get_media():
    """GET /api/media - Return current media player state from Home Assistant."""
    config = load_config()
    media_entity = config.get('media_player_entity', '')

    if not media_entity:
        return jsonify(None)

    supervisor_token = os.environ.get('SUPERVISOR_TOKEN', '')
    if not supervisor_token:
        logger.warning("No SUPERVISOR_TOKEN available for media API")
        return jsonify(None)

    try:
        url = f'http://supervisor/core/api/states/{media_entity}'
        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {supervisor_token}',
            'Content-Type': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())

        state = data.get('state', '')
        attrs = data.get('attributes', {})

        entity_picture = attrs.get('entity_picture', '')
        image_url = None
        if entity_picture:
            if entity_picture.startswith('/'):
                # Relative HA URL — proxy through our endpoint
                image_url = f'/api/media/image?url={urllib.parse.quote(entity_picture)}'
            else:
                # Absolute URL (e.g. Spotify CDN) — use directly
                image_url = entity_picture

        return jsonify({
            'state': state,
            'source': attrs.get('source', ''),
            'title': attrs.get('media_title', ''),
            'artist': attrs.get('media_artist', ''),
            'album': attrs.get('media_album_name', ''),
            'image_url': image_url,
            'volume_level': attrs.get('volume_level')
        })
    except Exception as e:
        logger.error(f"Error fetching media: {e}")
        return jsonify(None)


@app.route('/api/media/image', methods=['GET'])
def get_media_image():
    """GET /api/media/image - Proxy album art image from Home Assistant."""
    image_path = request.args.get('url', '')
    if not image_path or not image_path.startswith('/api/'):
        return jsonify({"error": "Invalid image URL"}), 400

    supervisor_token = os.environ.get('SUPERVISOR_TOKEN', '')
    if not supervisor_token:
        return jsonify({"error": "No auth token"}), 500

    try:
        url = f'http://supervisor/core{image_path}'
        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {supervisor_token}'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            image_data = response.read()
            content_type = response.headers.get('Content-Type', 'image/jpeg')

        return Response(image_data, content_type=content_type)
    except Exception as e:
        logger.error(f"Error fetching media image: {e}")
        return jsonify({"error": "Failed to fetch image"}), 500


def _call_media_service(service: str, extra_data: Optional[Dict] = None) -> bool:
    """Call a Home Assistant media_player service."""
    config = load_config()
    media_entity = config.get('media_player_entity', '')
    if not media_entity:
        return False

    supervisor_token = os.environ.get('SUPERVISOR_TOKEN', '')
    if not supervisor_token:
        return False

    try:
        url = f'http://supervisor/core/api/services/media_player/{service}'
        body = {"entity_id": media_entity}
        if extra_data:
            body.update(extra_data)
        data = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={
            'Authorization': f'Bearer {supervisor_token}',
            'Content-Type': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
        return True
    except Exception as e:
        logger.error(f"Error calling media_player/{service}: {e}")
        return False


@app.route('/api/media/play_pause', methods=['POST'])
def media_play_pause():
    """POST /api/media/play_pause - Toggle play/pause."""
    ok = _call_media_service('media_play_pause')
    return jsonify({"ok": ok})


@app.route('/api/media/next', methods=['POST'])
def media_next():
    """POST /api/media/next - Skip to next track."""
    ok = _call_media_service('media_next_track')
    return jsonify({"ok": ok})


@app.route('/api/media/previous', methods=['POST'])
def media_previous():
    """POST /api/media/previous - Skip to previous track."""
    ok = _call_media_service('media_previous_track')
    return jsonify({"ok": ok})


@app.route('/api/media/volume', methods=['POST'])
def media_volume():
    """POST /api/media/volume - Set volume level (0.0 - 1.0)."""
    body = request.get_json(silent=True) or {}
    volume = body.get('volume_level')
    if volume is None:
        return jsonify({"error": "volume_level required"}), 400
    volume = max(0.0, min(1.0, float(volume)))
    ok = _call_media_service('volume_set', {"volume_level": volume})
    return jsonify({"ok": ok})


@app.route('/photos/<path:filename>', methods=['GET'])
def serve_photo(filename: str):
    """GET /photos/<filename> - Serve a photo file, decoding HEIC on demand."""
    config = load_config()
    photos_folder = config.get('photos_folder', '/media')

    if Path(filename).suffix.lower() in HEIF_EXTENSIONS:
        source = resolve_photo(photos_folder, filename)
        if source is None or not source.is_file():
            return jsonify({"error": "File not found"}), 404
        decoded = heif_jpeg(source)
        if decoded is None:
            return jsonify({"error": "Could not decode image"}), 415
        # Cache names are hashes we generated, so this stays inside CACHE_DIR
        return send_from_directory(decoded.parent, decoded.name,
                                   mimetype='image/jpeg')

    try:
        # send_from_directory prevents directory traversal attacks automatically
        return send_from_directory(photos_folder, filename)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except PermissionError:
        logger.error(f"Permission denied accessing file: {filename}")
        return jsonify({"error": "Permission denied"}), 403


@app.route('/api/motion/<path:filename>', methods=['GET'])
def serve_motion(filename: str):
    """GET /api/motion/<filename> - Serve a photo's motion clip as MP4."""
    config = load_config()
    if config.get('motion_photos_enabled', True) is False:
        return jsonify({"error": "Motion photos disabled"}), 404

    source = resolve_photo(config.get('photos_folder', '/media'), filename)
    if source is None or not source.is_file():
        return jsonify({"error": "File not found"}), 404

    clip = motion_clip(source)
    if clip is None:
        return jsonify({"error": "No motion available"}), 404

    return send_from_directory(clip.parent, clip.name, mimetype='video/mp4')


@app.route('/api/demo/config', methods=['GET'])
def demo_config():
    """GET /api/demo/config - Return demo configuration for local UI testing."""
    config = {
        **DEFAULT_CONFIG,
        "home_assistant_url": "about:blank",
        "idle_timeout_seconds": 1,
        "slide_interval_seconds": 30,
        "weather_entity": "weather.demo",
        "media_player_entity": "media_player.demo",
        "clock_position": "bottom-center"
    }
    # ?night=1 forces the night window open so it can be previewed at any hour
    if request.args.get('night') == '1':
        config["night_mode_start"] = "00:00"
        config["night_mode_end"] = "23:59"
    return jsonify(config)


@app.route('/api/demo/weather', methods=['GET'])
def demo_weather():
    """GET /api/demo/weather - Return mock weather data."""
    return jsonify({
        'condition': 'cloudy',
        'temperature': 2,
        'temperature_unit': '°C'
    })


@app.route('/api/demo/media', methods=['GET'])
def demo_media():
    """GET /api/demo/media - Return mock media player data."""
    return jsonify({
        'state': 'playing',
        'title': 'Undernoise',
        'artist': 'Måns & Dotter',
        'album': 'Undernoise',
        'image_url': 'https://picsum.photos/seed/album/600/600',
        'volume_level': 0.5
    })


@app.route('/', methods=['GET'])
def serve_index():
    """GET / - Serve the main HTML page."""
    return send_file('static/index.html')


@app.route('/<path:path>', methods=['GET'])
def serve_static(path: str):
    """GET /<path> - Serve static files (CSS, JS, etc.)."""
    try:
        return send_from_directory('static', path)
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    config = load_config()
    logger.info("=" * 60)
    logger.info("Home Assistant Screensaver Starting")
    logger.info("=" * 60)
    logger.info(f"Photos folder: {config.get('photos_folder')}")
    logger.info(f"Idle timeout: {config.get('idle_timeout_seconds')} seconds")
    logger.info(f"HEIC decoder: {HEIF_CONVERT_BIN or 'not installed'}")
    logger.info(f"Motion transcoder: {FFMPEG_BIN or 'not installed'}")
    logger.info(f"Server listening on: http://0.0.0.0:8080")
    logger.info("=" * 60)

    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False
    )
