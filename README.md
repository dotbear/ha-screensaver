# Home Assistant Screensaver

A Python-based Home Assistant add-on that displays your Home Assistant UI and automatically switches to a photo slideshow after a period of inactivity.

Perfect for wall-mounted tablets running Home Assistant!

## Features

- 🖼️ Displays Home Assistant UI in fullscreen
- ⏱️ Automatic idle detection with configurable timeout
- 📸 Photo slideshow from Home Assistant media library with random selection
- 🕐 On-screen clock with adaptive color (auto-adjusts to image brightness)
- 📍 EXIF photo info display (location and date)
- 🌤️ Weather overlay from Home Assistant weather entities
- 🎵 Now Playing mode with album art, track info, and playback controls
- 🔊 Volume slider and transport controls (previous, play/pause, next)
- ⚡ Configurable slide duration (1-60 seconds)
- 👆 Touch/click to exit slideshow and return to Home Assistant
- ⏪ Tap left edge of screen to go back to previous photo
- ♻️ Automatic iframe refresh to prevent browser memory leaks
- ⚙️ Easy configuration via Home Assistant UI
- 🎨 Supports JPG, PNG, GIF, and WebP images
- 🚀 Optimized for Home Assistant Green (ARM devices)

## Installation

This is a **Home Assistant add-on**. Install it directly from your Home Assistant instance.

### Method 1: Add Custom Repository (Recommended)

1. **Add this repository to Home Assistant:**
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click **⋮** (three dots menu) in the top right
   - Select **Repositories**
   - Add this URL: `https://github.com/dotbear/ha-screensaver`
   - Click **Add** → **Close**

2. **Install the add-on:**
   - Refresh the Add-on Store page
   - Find **"Home Assistant Screensaver"** in the list
   - Click on it and then click **Install** (~30 seconds)

3. **Configure:**
   - Go to the **Configuration** tab
   - Set your preferences:
     - `idle_timeout_seconds`: 60 (time before slideshow starts)
     - `slide_interval_seconds`: 5 (duration each photo displays)
     - `photos_source`: "media" (to use HA media library)
     - `weather_entity`: Optional weather entity ID
     - `media_player_entity`: Optional media player entity ID

4. **Start the add-on:**
   - Click **Start**
   - Enable **"Start on boot"** (optional)
   - Click **"Open Web UI"** or navigate to `http://homeassistant.local:8080`

### Method 2: Manual Installation

If you prefer to install manually:

1. **Copy add-on to Home Assistant:**
   ```bash
   scp -r ha-screensaver root@homeassistant.local:/addons/
   ```

2. **Follow steps 2-4 from Method 1 above**

For detailed installation instructions, see [INSTALL.md](ha-screensaver/INSTALL.md)

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
idle_timeout_seconds: 60         # Time before slideshow starts (1-3600)
slide_interval_seconds: 5        # Duration each photo displays (1-60)
photos_source: media             # Where to find photos: "media", "share", or "addon"
clock_position: bottom-center    # Clock position: bottom-center, top-center, top-left, top-right, bottom-left, bottom-right
weather_entity: ""               # HA weather entity ID (e.g., "weather.home")
media_player_entity: ""          # HA media player entity ID (e.g., "media_player.spotify")
```

## Usage

1. Access the screensaver at `http://homeassistant.local:8080`
2. Your Home Assistant dashboard will be displayed
3. After the configured idle time, photos will start with an on-screen clock
4. Photos display in random order with adaptive text color for the clock
5. If a media player is configured and playing, the screensaver shows album art with track info and playback controls
6. Touch the screen to return to the dashboard (tap left edge to go back a photo)

## Why Python?

This add-on was originally written in Rust but rewritten in Python for better Home Assistant compatibility:

| Metric | Rust | Python |
|--------|------|--------|
| Build time | 5-10 minutes | 30 seconds ⚡ |
| Image size | ~500 MB | ~80 MB 💾 |
| HA ecosystem | Uncommon | Standard 🏠 |
| Maintenance | Complex | Simple ✅ |

## Documentation

- **[INSTALL.md](ha-screensaver/INSTALL.md)** - Detailed installation guide
- **[BUG_FIXES.md](ha-screensaver/BUG_FIXES.md)** - Bug analysis and fixes
- **[app.py](ha-screensaver/app.py)** - Source code

## Development

### Local Testing

Test the Python app on your computer before deploying:

```bash
cd ha-screensaver
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

For more troubleshooting, see [INSTALL.md](ha-screensaver/INSTALL.md)

## Project Structure

```
ha-screensaver/
├── ha-screensaver/            # Home Assistant add-on
│   ├── app.py                 # Main Python Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Container build instructions
│   ├── run.sh                # Startup script
│   ├── config.yaml           # Add-on configuration
│   ├── static/               # Frontend files
│   │   ├── index.html
│   │   └── app.js
│   └── *.md                  # Documentation
├── repository.yaml            # Add-on repository configuration
└── README.md                  # This file
```

## API Endpoints

- `GET /api/config` - Get current configuration
- `GET /api/photos` - Get list of photo URLs with EXIF metadata
- `GET /api/weather` - Get weather data from Home Assistant
- `GET /api/media` - Get current media player state (track info, album art, volume)
- `GET /api/media/image` - Proxy album art image from Home Assistant
- `POST /api/media/play_pause` - Toggle media playback
- `POST /api/media/next` - Skip to next track
- `POST /api/media/previous` - Skip to previous track
- `POST /api/media/volume` - Set volume level
- `GET /photos/<filename>` - Serve individual photo

## Contributing

Found a bug or have a feature request? Please check the documentation first:

1. **Installation issues:** See [INSTALL.md](ha-screensaver/INSTALL.md)
2. **Known bugs:** See [BUG_FIXES.md](ha-screensaver/BUG_FIXES.md)
3. **Code questions:** See [app.py](ha-screensaver/app.py)

## License

MIT

## Acknowledgments

- Originally inspired by the need for a simple Home Assistant screensaver
- Migrated from Rust to Python for better HA Green compatibility
