#!/usr/bin/env python3
"""
Home Assistant Screensaver - Python Flask Application

A web server that serves a screensaver application for Home Assistant.
It displays the HA dashboard and switches to a photo slideshow after idle time.
"""

import os
import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

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
    "media_player_entity": ""
}

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


# -----------------------------------------------------------------

def get_image_files(folder_path: str) -> List[Dict[str, Any]]:
    """
    Scan a folder for image files and return their URLs with EXIF metadata.
    GPS coordinates are reverse-geocoded to city/country names (cached to disk).
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

    photos = []
    folder = Path(folder_path)

    if not folder.exists():
        logger.warning(f"Photos folder does not exist: {folder_path}")
        return []

    if not folder.is_dir():
        logger.warning(f"Photos path is not a directory: {folder_path}")
        return []

    try:
        for file_path in folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in image_extensions:
                    photo_url = f"/photos/{file_path.name}"
                    exif = extract_exif(str(file_path))
                    photos.append({"url": photo_url, "exif": exif})

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
    photos = get_image_files(photos_folder)
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
    """GET /photos/<filename> - Serve a photo file."""
    config = load_config()
    photos_folder = config.get('photos_folder', '/media')

    try:
        # send_from_directory prevents directory traversal attacks automatically
        return send_from_directory(photos_folder, filename)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except PermissionError:
        logger.error(f"Permission denied accessing file: {filename}")
        return jsonify({"error": "Permission denied"}), 403


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
    logger.info(f"Server listening on: http://0.0.0.0:8080")
    logger.info("=" * 60)

    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False
    )
