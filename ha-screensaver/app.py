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
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    import requests
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False
    logger.warning("Google Auth libraries not available - Google Photos integration disabled")

from flask import Flask, jsonify, request, send_file, send_from_directory, redirect, session
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'ha-screensaver-secret-key-change-me')
CORS(app)

CONFIG_FILE = Path("/app/config.json")
GOOGLE_TOKENS_FILE = Path("/app/google_tokens.json")
GOOGLE_PHOTOS_CACHE = Path("/app/google_photos_cache.json")

DEFAULT_CONFIG = {
    "home_assistant_url": "http://homeassistant:8123",
    "photos_folder": "/media",
    "photos_source": "media",
    "idle_timeout_seconds": 60,
    "slide_interval_seconds": 5,
    "clock_position": "bottom-center",
    "weather_entity": "",
    "google_photos_enabled": False,
    "google_photos_client_id": "",
    "google_photos_client_secret": "",
    "google_photos_refresh_interval": 3600
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

# --------------- Google Photos integration ---------------

def _load_google_tokens() -> Optional[Dict[str, Any]]:
    """Load saved Google OAuth tokens from disk."""
    try:
        if GOOGLE_TOKENS_FILE.exists():
            with open(GOOGLE_TOKENS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load Google tokens: {e}")
    return None


def _save_google_tokens(tokens: Dict[str, Any]) -> None:
    """Save Google OAuth tokens to disk."""
    try:
        GOOGLE_TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GOOGLE_TOKENS_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save Google tokens: {e}")


def _get_google_credentials() -> Optional[Credentials]:
    """Get valid Google OAuth credentials, refreshing if necessary."""
    if not HAS_GOOGLE_AUTH:
        return None

    tokens = _load_google_tokens()
    if not tokens:
        return None

    try:
        creds = Credentials(
            token=tokens.get('token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri=tokens.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=tokens.get('client_id'),
            client_secret=tokens.get('client_secret'),
            scopes=tokens.get('scopes', ['https://www.googleapis.com/auth/photospicker.mediaitems.readonly'])
        )

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_google_tokens({
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            })

        return creds
    except Exception as e:
        logger.error(f"Failed to get Google credentials: {e}")
        return None


def _create_google_picker_session() -> Optional[Dict[str, Any]]:
    """Create a new Google Photos Picker session."""
    if not HAS_GOOGLE_AUTH:
        return None

    creds = _get_google_credentials()
    if not creds:
        return None

    try:
        response = requests.post(
            'https://photospicker.googleapis.com/v1/sessions',
            headers={
                'Authorization': f'Bearer {creds.token}',
                'Content-Type': 'application/json'
            },
            json={}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to create Google Photos picker session: {e}")
        return None


def _get_google_picker_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a Google Photos Picker session."""
    if not HAS_GOOGLE_AUTH:
        return None

    creds = _get_google_credentials()
    if not creds:
        return None

    try:
        response = requests.get(
            f'https://photospicker.googleapis.com/v1/sessions/{session_id}',
            headers={
                'Authorization': f'Bearer {creds.token}'
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get Google Photos picker session: {e}")
        return None


def _get_google_media_items(session_id: str) -> List[Dict[str, Any]]:
    """Get media items from a Google Photos Picker session."""
    if not HAS_GOOGLE_AUTH:
        return []

    creds = _get_google_credentials()
    if not creds:
        return []

    try:
        media_items = []
        next_page_token = None

        while True:
            params = {'sessionId': session_id}
            if next_page_token:
                params['pageToken'] = next_page_token

            response = requests.get(
                'https://photospicker.googleapis.com/v1/mediaItems',
                headers={
                    'Authorization': f'Bearer {creds.token}'
                },
                params=params
            )
            response.raise_for_status()
            data = response.json()

            items = data.get('mediaItems', [])
            media_items.extend(items)

            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break

        logger.info(f"Retrieved {len(media_items)} media items from Google Photos")
        return media_items
    except Exception as e:
        logger.error(f"Failed to get Google Photos media items: {e}")
        return []


def _load_google_photos_cache() -> Dict[str, Any]:
    """Load cached Google Photos data."""
    try:
        if GOOGLE_PHOTOS_CACHE.exists():
            with open(GOOGLE_PHOTOS_CACHE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load Google Photos cache: {e}")
    return {'photos': [], 'last_updated': 0}


def _save_google_photos_cache(data: Dict[str, Any]) -> None:
    """Save Google Photos data to cache."""
    try:
        GOOGLE_PHOTOS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(GOOGLE_PHOTOS_CACHE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save Google Photos cache: {e}")


def _format_google_photo(media_item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a Google Photos media item to our photo format."""
    try:
        media_file = media_item.get('mediaFile', {})
        base_url = media_file.get('baseUrl', '')
        filename = media_file.get('filename', 'unknown.jpg')

        # Construct image URL with size parameters (e.g., =w2048-h1024)
        photo_url = f"/api/google-photos/proxy-image?url={base_url}=w2048-h1024"

        exif = {}

        # Extract date from createTime
        create_time = media_item.get('createTime')
        if create_time:
            try:
                dt = datetime.fromisoformat(create_time.replace('Z', '+00:00'))
                exif['date'] = f"{dt.strftime('%B')} {dt.day}, {dt.year}"
            except Exception:
                pass

        # Note: Google Photos Picker API doesn't provide location data for privacy
        # Location will be empty for Google Photos images

        return {
            'url': photo_url,
            'exif': exif,
            'source': 'google_photos',
            'filename': filename,
            'id': media_item.get('id', '')
        }
    except Exception as e:
        logger.error(f"Failed to format Google Photo: {e}")
        return None


def get_google_photos() -> List[Dict[str, Any]]:
    """Get photos from Google Photos cache, refreshing if necessary."""
    config = load_config()

    if not config.get('google_photos_enabled', False):
        return []

    if not HAS_GOOGLE_AUTH:
        logger.warning("Google Auth libraries not available")
        return []

    # Check cache
    cache = _load_google_photos_cache()
    refresh_interval = config.get('google_photos_refresh_interval', 3600)
    current_time = time.time()

    # Return cached photos if still valid
    if cache.get('photos') and (current_time - cache.get('last_updated', 0)) < refresh_interval:
        logger.info(f"Returning {len(cache['photos'])} cached Google Photos")
        return cache['photos']

    # Cache is stale or empty - user needs to pick photos via the UI
    # Return cached photos anyway (might be empty)
    return cache.get('photos', [])

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

# --------------- Google Photos API endpoints ---------------

@app.route('/api/google-photos/status', methods=['GET'])
def google_photos_status():
    """GET /api/google-photos/status - Check if Google Photos is authenticated."""
    if not HAS_GOOGLE_AUTH:
        return jsonify({'authenticated': False, 'error': 'Google Auth libraries not available'})

    config = load_config()
    if not config.get('google_photos_enabled', False):
        return jsonify({'authenticated': False, 'error': 'Google Photos not enabled'})

    creds = _get_google_credentials()
    cache = _load_google_photos_cache()

    return jsonify({
        'authenticated': creds is not None,
        'photos_count': len(cache.get('photos', [])),
        'last_updated': cache.get('last_updated', 0)
    })


@app.route('/api/google-photos/auth-url', methods=['GET'])
def google_photos_auth_url():
    """GET /api/google-photos/auth-url - Get Google OAuth authorization URL."""
    if not HAS_GOOGLE_AUTH:
        return jsonify({'error': 'Google Auth libraries not available'}), 500

    config = load_config()
    client_id = config.get('google_photos_client_id', '')
    client_secret = config.get('google_photos_client_secret', '')

    if not client_id or not client_secret:
        return jsonify({'error': 'Google Photos client ID and secret not configured'}), 400

    try:
        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [request.url_root.rstrip('/') + '/api/google-photos/callback']
                }
            },
            scopes=['https://www.googleapis.com/auth/photospicker.mediaitems.readonly']
        )

        flow.redirect_uri = request.url_root.rstrip('/') + '/api/google-photos/callback'
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        session['google_oauth_state'] = state
        return jsonify({'authorization_url': authorization_url})
    except Exception as e:
        logger.error(f"Failed to create OAuth URL: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/google-photos/callback', methods=['GET'])
def google_photos_callback():
    """GET /api/google-photos/callback - Handle OAuth callback from Google."""
    if not HAS_GOOGLE_AUTH:
        return "Google Auth libraries not available", 500

    config = load_config()
    client_id = config.get('google_photos_client_id', '')
    client_secret = config.get('google_photos_client_secret', '')

    try:
        state = session.get('google_oauth_state')
        if not state:
            return "Invalid state", 400

        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [request.url_root.rstrip('/') + '/api/google-photos/callback']
                }
            },
            scopes=['https://www.googleapis.com/auth/photospicker.mediaitems.readonly'],
            state=state
        )

        flow.redirect_uri = request.url_root.rstrip('/') + '/api/google-photos/callback'
        flow.fetch_token(authorization_response=request.url)

        creds = flow.credentials
        _save_google_tokens({
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        })

        logger.info("Google Photos authentication successful")
        return """
        <html>
        <head>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .container {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 2rem;
                    border-radius: 10px;
                    backdrop-filter: blur(10px);
                }
                .checkmark {
                    font-size: 64px;
                    margin-bottom: 1rem;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="checkmark">✓</div>
                <h2>Authentication Successful!</h2>
                <p id="message">Redirecting back to app...</p>
            </div>
            <script>
                // Try to close the window (works for popups)
                const canClose = window.opener !== null;
                if (canClose) {
                    document.getElementById('message').textContent = 'You can close this window.';
                    window.close();
                } else {
                    // Full page redirect (mobile)
                    document.getElementById('message').textContent = 'Redirecting...';
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1500);
                }
            </script>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                }}
                .container {{
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 2rem;
                    border-radius: 10px;
                    backdrop-filter: blur(10px);
                }}
                .error-icon {{
                    font-size: 64px;
                    margin-bottom: 1rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">✗</div>
                <h2>Authentication Failed</h2>
                <p>{str(e)}</p>
                <p id="message">Redirecting back...</p>
            </div>
            <script>
                const canClose = window.opener !== null;
                if (canClose) {{
                    document.getElementById('message').textContent = 'You can close this window.';
                    setTimeout(() => window.close(), 3000);
                }} else {{
                    setTimeout(() => window.location.href = '/', 3000);
                }}
            </script>
        </body>
        </html>
        """, 400


@app.route('/api/google-photos/create-session', methods=['POST'])
def google_photos_create_session():
    """POST /api/google-photos/create-session - Create a Google Photos Picker session."""
    if not HAS_GOOGLE_AUTH:
        return jsonify({'error': 'Google Auth libraries not available'}), 500

    session_data = _create_google_picker_session()
    if not session_data:
        return jsonify({'error': 'Failed to create picker session. Make sure you are authenticated.'}), 500

    return jsonify(session_data)


@app.route('/api/google-photos/poll-session/<session_id>', methods=['GET'])
def google_photos_poll_session(session_id: str):
    """GET /api/google-photos/poll-session/<session_id> - Poll the status of a picker session."""
    if not HAS_GOOGLE_AUTH:
        return jsonify({'error': 'Google Auth libraries not available'}), 500

    session_data = _get_google_picker_session(session_id)
    if not session_data:
        return jsonify({'error': 'Failed to get session status'}), 500

    return jsonify(session_data)


@app.route('/api/google-photos/fetch-photos/<session_id>', methods=['POST'])
def google_photos_fetch_photos(session_id: str):
    """POST /api/google-photos/fetch-photos/<session_id> - Fetch photos from a completed session."""
    if not HAS_GOOGLE_AUTH:
        return jsonify({'error': 'Google Auth libraries not available'}), 500

    # Get media items from the session
    media_items = _get_google_media_items(session_id)
    if not media_items:
        return jsonify({'error': 'No media items found or failed to fetch'}), 500

    # Convert to our photo format
    photos = []
    for item in media_items:
        photo = _format_google_photo(item)
        if photo:
            photos.append(photo)

    # Save to cache
    _save_google_photos_cache({
        'photos': photos,
        'last_updated': time.time()
    })

    logger.info(f"Saved {len(photos)} photos from Google Photos to cache")
    return jsonify({'success': True, 'count': len(photos), 'photos': photos})


@app.route('/api/google-photos/proxy-image', methods=['GET'])
def google_photos_proxy_image():
    """GET /api/google-photos/proxy-image - Proxy an image from Google Photos."""
    if not HAS_GOOGLE_AUTH:
        return jsonify({'error': 'Google Auth libraries not available'}), 500

    image_url = request.args.get('url')
    if not image_url:
        return jsonify({'error': 'Missing url parameter'}), 400

    creds = _get_google_credentials()
    if not creds:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        response = requests.get(
            image_url,
            headers={
                'Authorization': f'Bearer {creds.token}'
            },
            stream=True
        )
        response.raise_for_status()

        # Return the image
        from flask import Response
        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get('Content-Type', 'image/jpeg'),
            headers={
                'Cache-Control': 'public, max-age=3600'
            }
        )
    except Exception as e:
        logger.error(f"Failed to proxy Google Photos image: {e}")
        return jsonify({'error': str(e)}), 500


# --------------- Standard API endpoints ---------------

@app.route('/api/config', methods=['GET'])
def get_config():
    """GET /api/config - Return current configuration."""
    config = load_config()
    return jsonify(config)


@app.route('/api/photos', methods=['GET'])
def get_photos():
    """GET /api/photos - Return list of photo URLs with EXIF metadata."""
    config = load_config()

    # Check if Google Photos is enabled
    if config.get('photos_source') == 'google_photos' or config.get('google_photos_enabled', False):
        photos = get_google_photos()
    else:
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
