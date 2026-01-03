# Home Assistant Screensaver

A Python-based Home Assistant add-on that displays your Home Assistant UI and automatically switches to a photo slideshow after a period of inactivity.

Perfect for wall-mounted tablets running Home Assistant!

## Features

- 🖼️ Displays Home Assistant UI in fullscreen
- ⏱️ Automatic idle detection with configurable timeout
- 📸 Photo slideshow from Home Assistant media library with random selection
- 🕐 On-screen clock with adaptive color (auto-adjusts to image brightness)
- ⚡ Configurable slide duration (1-60 seconds)
- 👆 Touch/click to exit slideshow and return to Home Assistant
- ⚙️ Easy configuration via Home Assistant UI
- 🎨 Supports JPG, PNG, GIF, and WebP images
- 🚀 Optimized for Home Assistant Green (ARM devices)
- 🐍 Lightweight Python implementation

## Installation

This is a **Home Assistant add-on**. Install it directly from your Home Assistant instance.

### Quick Install

1. **Copy add-on to Home Assistant:**
   ```bash
   scp -r addon/ha-screensaver root@homeassistant.local:/addons/
   ```

2. **In Home Assistant:**
   - Go to **Settings** → **Add-ons**
   - Click **⋮** menu → **Check for updates**
   - Find **"Home Assistant Screensaver"** under Local add-ons
   - Click **Install** (~30 seconds)

3. **Configure:**
   - `idle_timeout_seconds`: 60 (or your preference)
   - `slide_interval_seconds`: 5 (or your preference)
   - `photos_source`: "media" (to use HA media library)

4. **Start the add-on:**
   - Click **Start**
   - Enable **"Start on boot"** (optional)
   - Click **"Open Web UI"** or navigate to `http://homeassistant.local:8080`

For detailed installation instructions, see [INSTALL.md](addon/ha-screensaver/INSTALL.md)

## Adding Photos

### Option 1: Home Assistant Media Library (Easiest)

1. In Home Assistant: **Media** → **Local Media**
2. Click **Upload** button
3. Select your photos
4. Done! The screensaver will automatically find them

### Option 2: Auto-upload from iPhone

Use a file sync app to automatically upload photos from your iPhone:

- **PhotoSync** - Auto-upload to HA via SMB/WebDAV
- **Documents by Readdle** - File sync to HA
- **Nextcloud** (if installed) - Native sync support

Point the app to upload to your Home Assistant's media folder.

## Configuration

Configure via the Home Assistant add-on configuration UI:

```yaml
idle_timeout_seconds: 60      # Time before slideshow starts (1-3600)
slide_interval_seconds: 5     # Duration each photo displays (1-60)
photos_source: media          # Where to find photos: "media", "share", or "addon"
```

## Usage

1. Access the screensaver at `http://homeassistant.local:8080`
2. Your Home Assistant dashboard will be displayed
3. After the configured idle time, photos will start with an on-screen clock
4. Photos display in random order with adaptive text color for the clock
5. Touch the screen to return to the dashboard

## Why Python?

This add-on was originally written in Rust but rewritten in Python for better Home Assistant compatibility:

| Metric | Rust | Python |
|--------|------|--------|
| Build time | 5-10 minutes | 30 seconds ⚡ |
| Image size | ~500 MB | ~80 MB 💾 |
| HA ecosystem | Uncommon | Standard 🏠 |
| Maintenance | Complex | Simple ✅ |

For more details, see [PYTHON_MIGRATION.md](PYTHON_MIGRATION.md)

## Documentation

- **[INSTALL.md](addon/ha-screensaver/INSTALL.md)** - Detailed installation guide
- **[BUG_FIXES.md](addon/ha-screensaver/BUG_FIXES.md)** - Bug analysis and fixes
- **[PYTHON_MIGRATION.md](PYTHON_MIGRATION.md)** - Rust to Python migration info
- **[app.py](addon/ha-screensaver/app.py)** - Source code (heavily commented!)

## Development

### Local Testing

Test the Python app on your computer before deploying:

```bash
cd addon/ha-screensaver
./test_local.sh
```

Or manually:

```bash
pip3 install -r requirements.txt
mkdir test-photos
cp ~/Pictures/*.jpg test-photos/
python3 app.py
```

Then open http://localhost:8080

### For Elixir Developers

The source code (`app.py`) includes detailed comments explaining Python concepts in terms of Elixir equivalents:

- `try/except` explained as `case` pattern matching
- List comprehensions compared to `Enum.map |> Enum.filter`
- Flask decorators compared to Phoenix route macros
- Dictionary operations compared to `Map` functions

## Troubleshooting

### No photos showing
- Check that photos are in the configured folder
- Verify supported formats: JPG, JPEG, PNG, GIF, WebP
- Check add-on logs: **Settings** → **Add-ons** → **HA Screensaver** → **Log**

### Slideshow doesn't start
- Ensure `idle_timeout_seconds` is set correctly
- Verify at least one photo exists
- Check browser console (F12) for errors

### Add-on won't install
- Check that files are in `/addons/ha-screensaver/`
- Verify `config.yaml` exists
- Restart Home Assistant if needed

For more troubleshooting, see [INSTALL.md](addon/ha-screensaver/INSTALL.md)

## Project Structure

```
ha-screensaver/
├── addon/ha-screensaver/      # Home Assistant add-on
│   ├── app.py                 # Main Python Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Container build instructions
│   ├── run.sh                # Startup script
│   ├── config.yaml           # Add-on configuration
│   ├── static/               # Frontend files
│   │   ├── index.html
│   │   └── app.js
│   └── *.md                  # Documentation
├── static/                    # Standalone static files
├── photos/                    # Local photos folder (gitignored)
└── README.md                  # This file
```

## API Endpoints

- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration (with validation)
- `GET /api/photos` - Get list of photo URLs
- `GET /photos/<filename>` - Serve individual photo

## Contributing

Found a bug or have a feature request? Please check the documentation first:

1. **Installation issues:** See [INSTALL.md](addon/ha-screensaver/INSTALL.md)
2. **Known bugs:** See [BUG_FIXES.md](addon/ha-screensaver/BUG_FIXES.md)
3. **Code questions:** See inline comments in [app.py](addon/ha-screensaver/app.py)

## License

MIT

## Acknowledgments

- Originally inspired by the need for a simple Home Assistant screensaver
- Migrated from Rust to Python for better HA Green compatibility
- Designed with Elixir developers in mind (extensive Elixir equivalents in comments)
