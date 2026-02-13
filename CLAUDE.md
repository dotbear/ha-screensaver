# CLAUDE.md - Home Assistant Screensaver

**AI Assistant Guide for Development**

This document provides comprehensive information about the Home Assistant Screensaver codebase for AI assistants to effectively understand and contribute to the project.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Technologies](#architecture--technologies)
3. [Codebase Structure](#codebase-structure)
4. [Development Workflows](#development-workflows)
5. [Key Conventions](#key-conventions)
6. [API Documentation](#api-documentation)
7. [Configuration System](#configuration-system)
8. [Common Tasks](#common-tasks)
9. [Testing](#testing)
10. [Deployment](#deployment)
11. [Important Notes for AI Assistants](#important-notes-for-ai-assistants)

---

## Project Overview

**Name:** Home Assistant Screensaver
**Version:** 1.1.0
**Type:** Home Assistant Add-on
**Purpose:** Displays Home Assistant UI and automatically switches to a photo slideshow with clock after inactivity

### Key Features
- Full-screen Home Assistant UI display via iframe
- Automatic idle detection with configurable timeout (1-3600 seconds)
- Random photo slideshow from HA media library
- On-screen clock with adaptive color based on image brightness
- EXIF metadata display (location via reverse geocoding, date taken)
- Weather overlay from Home Assistant weather entities
- Configurable slide duration (1-60 seconds)
- Touch/click interaction (tap to exit, tap left edge to go back)
- Support for JPG, PNG, GIF, WebP images
- Optimized for ARM devices (Home Assistant Green)

### Project History
- Originally written in Rust (5-10 min builds, ~500 MB image)
- Rewritten in Python for better HA compatibility (30 sec builds, ~80 MB image)
- Uses Flask web framework for simplicity and maintainability

---

## Architecture & Technologies

### Backend Stack
- **Language:** Python 3
- **Web Framework:** Flask 3.0.0
- **WSGI Server:** Gunicorn 21.2.0 (production)
- **CORS:** flask-cors 4.0.0
- **Image Processing:** Pillow (py3-pillow from Alpine)
- **Container:** Docker (Alpine Linux base)

### Frontend Stack
- **Pure JavaScript** (no frameworks)
- **HTML5/CSS3**
- **Canvas API** for image brightness analysis
- **Fetch API** for backend communication

### Infrastructure
- **Home Assistant Add-on** architecture
- **Ingress:** Port 8080 (proxied through HA)
- **File Access:** Read/write to `/media`, `/share`, `/app/photos`
- **HA API:** Access via SUPERVISOR_TOKEN environment variable

### Build System
- **Dockerfile:** Multi-architecture support (aarch64, amd64, armv7)
- **build.yaml:** Uses HA base images (Alpine 3.19)
- **Run script:** Bash script with bashio helper functions

---

## Codebase Structure

```
ha-screensaver/
├── addon/ha-screensaver/          # Main add-on directory
│   ├── app.py                     # Flask application (338 lines)
│   ├── requirements.txt           # Python dependencies
│   ├── Dockerfile                 # Container build instructions
│   ├── build.yaml                 # HA build configuration
│   ├── config.yaml                # Add-on metadata & schema
│   ├── run.sh                     # Startup script
│   ├── test_local.sh              # Local development test script
│   ├── static/                    # Frontend files
│   │   ├── index.html             # Main UI (includes CSS)
│   │   └── app.js                 # Frontend logic (434 lines)
│   ├── INSTALL.md                 # Installation guide
│   ├── BUG_FIXES.md               # Bug analysis & fixes
│   ├── CHANGELOG.md               # Version history
│   └── README.md                  # Add-on documentation
├── static/                        # Standalone static files (mirror)
│   ├── index.html
│   └── app.js
├── README.md                      # Main project README
├── INSTALL_ADDON.md               # Installation instructions
├── .gitignore                     # Git ignore rules
└── photos/                        # Local test photos (gitignored)
```

### Core Files

#### app.py (Backend)
**Lines:** 338
**Key Components:**
- Configuration management (lines 50-60)
- EXIF extraction with GPS parsing (lines 79-111)
- Reverse geocoding with disk cache (lines 114-172)
- Image file scanning (lines 174-231)
- API endpoints (lines 238-316)
- Flask app initialization (lines 323-337)

**API Routes:**
- `GET /` - Serve index.html
- `GET /api/config` - Return configuration
- `GET /api/photos` - Return photo list with EXIF
- `GET /api/weather` - Proxy HA weather data
- `GET /photos/<filename>` - Serve individual photos

#### app.js (Frontend)
**Lines:** 434
**Key Components:**
- `ScreensaverApp` class (main application)
- Configuration loading (lines 28-48)
- Photo management (lines 50-61)
- Idle detection (lines 87-120)
- Slideshow logic (lines 122-223)
- Clock with adaptive color (lines 224-361)
- Weather display (lines 373-409)
- Touch/click handlers (lines 63-85)

#### config.yaml (Add-on Configuration)
**Schema Validation:**
- `idle_timeout_seconds: int(1,3600)` - Range enforced
- `slide_interval_seconds: int(1,60)` - Range enforced
- `photos_source: list(media|share|addon)?` - Enum
- `clock_position: list(bottom-center|...)` - 6 options
- `weather_entity: str?` - Optional string

#### run.sh (Startup Script)
**Responsibilities:**
1. Read HA add-on options using bashio
2. Determine photos folder based on source
3. Generate `/app/config.json` for Flask
4. Start Gunicorn with 2 workers, 4 threads

---

## Development Workflows

### Local Development

#### Prerequisites
- Python 3 with pip
- Test photos in `~/Pictures/` or similar

#### Quick Start
```bash
cd addon/ha-screensaver
./test_local.sh
```

#### Manual Setup
```bash
# Install dependencies
pip3 install -r requirements.txt

# Create test environment
mkdir test-photos
cp ~/Pictures/*.jpg test-photos/

# Create config
cat > config.json << EOF
{
  "home_assistant_url": "http://homeassistant.local:8123",
  "photos_folder": "./test-photos",
  "idle_timeout_seconds": 60,
  "slide_interval_seconds": 5,
  "clock_position": "bottom-center",
  "weather_entity": ""
}
EOF

# Run server
python3 app.py

# Access at http://localhost:8080
```

### Home Assistant Development

#### Installation to HA
```bash
# Copy add-on to Home Assistant
scp -r addon/ha-screensaver root@homeassistant.local:/addons/

# In HA UI:
# Settings → Add-ons → ⋮ → Check for updates → Install
```

#### Viewing Logs
```bash
# Via HA UI
# Settings → Add-ons → HA Screensaver → Log

# Via SSH
docker logs addon_ha-screensaver
```

#### Rebuilding After Changes
1. Modify code locally
2. `scp -r addon/ha-screensaver root@homeassistant.local:/addons/`
3. In HA: Settings → Add-ons → HA Screensaver → Rebuild
4. Wait ~30 seconds
5. Restart add-on

---

## Key Conventions

### Code Style

#### Python (app.py)
- **Formatting:** PEP 8 style
- **Line Length:** ~80-100 characters
- **Type Hints:** Used for function signatures
- **Docstrings:** Triple-quoted strings for functions
- **Error Handling:** Try/except with specific exceptions
- **Logging:** Using Python logging module (INFO, WARNING, ERROR)

**Example:**
```python
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
```

#### JavaScript (app.js)
- **Style:** ES6+ classes
- **Async/Await:** Preferred over promises
- **Naming:** camelCase for variables/methods
- **Comments:** Inline for complex logic
- **Error Handling:** Try/catch with console logging

**Example:**
```javascript
async loadConfig() {
  try {
    const response = await fetch('api/config');
    this.config = await response.json();
    console.log('Config loaded:', this.config);
  } catch (error) {
    console.error('Error loading config:', error);
    this.config = { /* defaults */ };
  }
}
```

### File Organization
- **Backend:** Single `app.py` file (keep simple)
- **Frontend:** Single `app.js` class-based structure
- **Static assets:** In `static/` directory
- **Documentation:** Separate `.md` files for different purposes

### Configuration Management
- **Source of Truth:** HA add-on `config.yaml` schema
- **Runtime Config:** Generated `/app/config.json` by `run.sh`
- **Frontend Access:** Via `/api/config` endpoint
- **Validation:** Schema-based in `config.yaml`, no backend validation needed

---

## API Documentation

### Endpoints

#### GET /api/config
**Purpose:** Return current configuration
**Authentication:** None (internal)
**Response:**
```json
{
  "home_assistant_url": "http://homeassistant.local:8123",
  "photos_folder": "/media",
  "idle_timeout_seconds": 60,
  "slide_interval_seconds": 5,
  "clock_position": "bottom-center",
  "weather_entity": "weather.home"
}
```

#### GET /api/photos
**Purpose:** Return list of photos with EXIF metadata
**Processing:**
- Scans `photos_folder` for image files
- Extracts EXIF data (date, GPS coordinates)
- Reverse geocodes GPS to city/country (cached)
- Returns sorted list by filename

**Response:**
```json
[
  {
    "url": "/photos/IMG_1234.jpg",
    "exif": {
      "date": "January 15, 2024",
      "location": "San Francisco, United States"
    }
  }
]
```

**Caching:** Geocoding results cached in `/app/geocache.json`
**Rate Limiting:** Nominatim API limited to 1 req/sec

#### GET /api/weather
**Purpose:** Proxy weather data from Home Assistant
**Authentication:** Uses `SUPERVISOR_TOKEN` environment variable
**HA API Endpoint:** `http://supervisor/core/api/states/{entity_id}`

**Response:**
```json
{
  "condition": "sunny",
  "temperature": 22.5,
  "temperature_unit": "°C"
}
```

**Returns null if:**
- No weather_entity configured
- SUPERVISOR_TOKEN not available
- API request fails

#### GET /photos/\<filename\>
**Purpose:** Serve individual photo files
**Security:** `send_from_directory` prevents path traversal
**Error Handling:**
- 404 if file not found
- 403 if permission denied

---

## Configuration System

### Schema Definition (config.yaml)

```yaml
options:
  idle_timeout_seconds: 60           # Default values
  slide_interval_seconds: 5
  photos_source: "media"
  clock_position: "bottom-center"
  weather_entity: ""

schema:
  idle_timeout_seconds: int(1,3600)  # Validation rules
  slide_interval_seconds: int(1,60)
  photos_source: list(media|share|addon)?
  clock_position: list(bottom-center|top-center|top-left|top-right|bottom-left|bottom-right)?
  weather_entity: str?
```

### Photos Source Mapping (run.sh)

```bash
case "${PHOTOS_SOURCE}" in
    "media")  PHOTOS_FOLDER="/media" ;;
    "share")  PHOTOS_FOLDER="/share" ;;
    *)        PHOTOS_FOLDER="/app/photos" ;;
esac
```

### Clock Positions

Available positions (CSS classes):
- `pos-bottom-center` (default)
- `pos-top-center`
- `pos-top-left`
- `pos-top-right`
- `pos-bottom-left`
- `pos-bottom-right`

Applied via JavaScript at runtime (app.js:355-361).

---

## Common Tasks

### Adding a New Configuration Option

1. **Update config.yaml schema:**
```yaml
options:
  new_option: "default_value"
schema:
  new_option: str?
```

2. **Update run.sh to read it:**
```bash
NEW_OPTION=$(bashio::config 'new_option')
bashio::log.info "New option: ${NEW_OPTION}"
```

3. **Add to config.json generation:**
```bash
cat > /app/config.json <<EOF
{
  ...
  "new_option": "${NEW_OPTION}"
}
EOF
```

4. **Use in app.py:**
```python
config = load_config()
new_value = config.get('new_option', 'default')
```

5. **Access in frontend:**
```javascript
await this.loadConfig();
const newValue = this.config.new_option;
```

### Adding Support for New Image Formats

**Update app.py:179:**
```python
image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
```

### Changing Default Idle Timeout

**Edit config.yaml:**
```yaml
options:
  idle_timeout_seconds: 120  # Change from 60 to 120
```

### Adding a New API Endpoint

**In app.py:**
```python
@app.route('/api/new-endpoint', methods=['GET'])
def new_endpoint():
    """GET /api/new-endpoint - Description."""
    try:
        # Your logic here
        return jsonify({"data": "value"})
    except Exception as e:
        logger.error(f"Error in new endpoint: {e}")
        return jsonify({"error": str(e)}), 500
```

### Modifying Clock Display

**CSS in index.html (lines 66-97):**
```css
#clock-time {
  font-size: 72px;  /* Adjust size */
  font-weight: 600;
  letter-spacing: 2px;
}
```

**Logic in app.js (lines 224-254):**
```javascript
updateTime() {
  const now = new Date();
  // Modify time format here
  timeElement.textContent = `${hours}:${minutes}`;
}
```

---

## Testing

### Local Testing Workflow

```bash
cd addon/ha-screensaver

# Run test script
./test_local.sh

# Or manually:
pip3 install -r requirements.txt
mkdir test-photos
cp ~/Pictures/*.jpg test-photos/
python3 app.py
```

### Test Cases (from BUG_FIXES.md)

1. **Empty photos folder** → Should return empty array, not crash
2. **Invalid permissions** → Should log error and continue
3. **Large timeout values** → Should be rejected by schema validation
4. **Negative timeout** → Should be rejected by schema validation
5. **Path traversal attempts** → Should return 404, not serve system files
6. **1000+ photos** → Monitor performance
7. **Missing EXIF data** → Should gracefully handle missing fields
8. **Invalid image files** → Should skip and continue

### Manual Testing Checklist

- [ ] HA iframe loads correctly
- [ ] Idle detection triggers after timeout
- [ ] Photos load and display in random order
- [ ] Clock updates every second
- [ ] Clock color adapts to image brightness
- [ ] Tap to exit slideshow works
- [ ] Tap left edge to go back works
- [ ] Weather displays correctly (if configured)
- [ ] EXIF location/date displays (if available)
- [ ] Configuration changes apply after restart

---

## Deployment

### Build Process

**Triggered by:** Home Assistant when rebuilding add-on
**Build Time:** ~30 seconds on ARM devices
**Image Size:** ~80 MB

**Steps:**
1. Alpine base image selection (based on arch)
2. Install Python 3, pip, Pillow, bash
3. Copy requirements.txt and install dependencies
4. Copy app.py and static/ files
5. Copy and chmod run.sh
6. Set CMD to /run.sh

### Runtime Process

**On add-on start:**
1. `run.sh` executes
2. Reads HA configuration using bashio
3. Determines photos folder
4. Generates `/app/config.json`
5. Starts Gunicorn with app.py
6. Gunicorn spawns 2 worker processes with 4 threads each
7. Listens on 0.0.0.0:8080
8. HA ingress proxies to this port

### File Permissions

**Mapped Volumes:**
- `/media` - Read/write (HA media library)
- `/share` - Read/write (HA share folder)
- `/app/photos` - Read/write (add-on internal)

**Generated Files:**
- `/app/config.json` - Runtime configuration
- `/app/geocache.json` - Geocoding cache

---

## Important Notes for AI Assistants

### When Making Changes

1. **Security First:**
   - Never remove `send_from_directory` - prevents path traversal
   - Always validate user input at boundaries
   - Don't expose internal paths in error messages
   - Keep SUPERVISOR_TOKEN handling secure

2. **Performance Considerations:**
   - Photo scanning happens on every `/api/photos` request
   - For 1000+ photos, consider implementing caching (see BUG_FIXES.md #6)
   - Nominatim geocoding is rate-limited (1 req/sec)
   - Geocoding results are cached to disk

3. **Backwards Compatibility:**
   - Don't change config.yaml schema without migration path
   - Maintain API endpoint contracts
   - Test with existing photo libraries

4. **Home Assistant Integration:**
   - Respect HA add-on conventions
   - Use bashio for configuration reading
   - Use SUPERVISOR_TOKEN for HA API access
   - Follow ingress pattern for web UI

5. **Error Handling:**
   - Always catch specific exceptions
   - Log errors with context
   - Return user-friendly error messages
   - Don't crash on bad data

### Common Pitfalls to Avoid

1. **Don't recursively scan directories** without user option - performance issue with large libraries
2. **Don't cache photos list indefinitely** - users expect new photos to appear
3. **Don't validate configuration in app.py** - HA schema handles it
4. **Don't use debug=True in production** - security risk
5. **Don't store secrets in config.json** - use HA secrets system
6. **Don't assume EXIF data exists** - many photos lack it
7. **Don't exceed Nominatim rate limits** - 1 req/sec max

### Best Practices

1. **Use type hints** for all Python functions
2. **Log at appropriate levels:**
   - INFO: Normal operation (startup, photo count)
   - WARNING: Recoverable issues (no photos, missing EXIF)
   - ERROR: Failures (API errors, file permissions)
3. **Handle missing data gracefully:**
   - Use `.get()` with defaults for dicts
   - Check `if not value:` before using
   - Return empty arrays/null instead of errors
4. **Test locally first** using `test_local.sh`
5. **Document breaking changes** in CHANGELOG.md
6. **Update version** in config.yaml when releasing

### Architecture Decisions

**Why Python over Rust?**
- 6-20x faster builds (30s vs 5-10min)
- 6x smaller images (80 MB vs 500 MB)
- Better HA ecosystem fit
- Easier maintenance
- Negligible performance difference for this use case

**Why single file backend?**
- Simple screensaver doesn't need complex structure
- Easy to understand and modify
- Fast to deploy and test

**Why Gunicorn over Flask dev server?**
- Production-ready WSGI server
- Multi-worker support
- Better performance
- Proper signal handling

**Why disk caching for geocoding?**
- Nominatim rate limits (1 req/sec)
- Same coordinates appear in multiple photos
- Reduces API calls by ~90%
- Survives add-on restarts

### File References

When discussing code, reference specific files and line numbers:
- `app.py:79-111` - EXIF extraction
- `app.js:256-342` - Clock color algorithm
- `config.yaml:23-28` - Schema validation
- `run.sh:19-29` - Photos folder mapping

### Quick Reference

**Most frequently edited files:**
- `config.yaml` - Add configuration options
- `app.py` - Add API endpoints or backend logic
- `app.js` - Modify frontend behavior
- `index.html` - Change UI styling
- `run.sh` - Modify startup logic

**Rarely edited files:**
- `Dockerfile` - Only for dependency changes
- `build.yaml` - Only for architecture support
- `requirements.txt` - Only for new Python packages

---

## Version History

**Current:** 1.1.0
**See:** `addon/ha-screensaver/CHANGELOG.md` for full history

---

## Additional Resources

- **Installation Guide:** `addon/ha-screensaver/INSTALL.md`
- **Bug Analysis:** `addon/ha-screensaver/BUG_FIXES.md`
- **Main README:** `README.md`
- **Home Assistant Add-on Docs:** https://developers.home-assistant.io/docs/add-ons

---

**Last Updated:** 2026-02-13
**Maintainer:** Project maintainers
**AI Assistant Version:** This document is designed for AI assistants working with the codebase
