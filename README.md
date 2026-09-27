# Home Assistant Screensaver

A Python-based Home Assistant app (formerly "add-on") that displays your Home Assistant UI and automatically switches to a photo slideshow after a period of inactivity.

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
- 🌙 Night mode: only a faint greyscale clock during set hours
- ⚡ Configurable slide duration (1-60 seconds)
- 👆 Touch/click to exit slideshow and return to Home Assistant
- ⏪ Tap left edge of screen to go back to previous photo
- ♻️ Automatic iframe refresh to prevent browser memory leaks
- ⚙️ Easy configuration via Home Assistant UI
- 🎨 Supports JPG, PNG, GIF, WebP, and HEIC/HEIF (iPhone) images
- 🎞️ Live Photos and Motion Photos play their motion once, then hold on the still
- 🚀 Optimized for Home Assistant Green (ARM devices)

## Installation

This is a **Home Assistant app** (Home Assistant OS / Supervised only). Install it from your Home Assistant instance.

### Method 1: App repository (recommended)

1. **Add this repository:** **Settings** → **Apps** → **App store** → **⋮** (top right) → **Repositories** → add `https://github.com/dotbear/ha-screensaver` → **Add** → **Close**.
2. **Install:** refresh the store, open **Home Assistant Screensaver**, click **Install** (~30 seconds).
3. **Configure:** on the **Configuration** tab, set the options you need (see [Configuration](#configuration)) and click **Save**. The defaults work out of the box with photos in the HA media library.
4. **Start:** click **Start**, optionally enable **Start on boot**, then **Open Web UI** or browse to `http://homeassistant.local:8080`.

Updates arrive through the app store whenever `version` in `ha-screensaver/config.yaml` is bumped.

### Method 2: Local app (for testing changes)

1. From the root of this repository, copy the app folder into the local apps folder. In current versions of the Terminal & SSH app that folder is `/local_apps` (older versions call it `/addons`):
   ```bash
   scp -r ha-screensaver root@homeassistant.local:/local_apps/
   ```
   It must end up as `/local_apps/ha-screensaver/config.yaml`, not nested one level deeper. You can also copy it over the Samba app's share for local apps.
2. **Settings** → **Apps** → **App store** → **⋮** → **Check for updates**. The app appears under **Local apps**.
3. Continue with steps 2-4 of Method 1. After changing files, use **Rebuild** on the app page.

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

### Option 3: Samba share

With the Samba share app installed, copy photos into its `media` share. Use
`photos_source: share` and the `share` folder instead if you prefer to keep them
out of the media library.

## Configuration

Configure on the app's **Configuration** tab:

```yaml
idle_timeout_seconds: 60         # Time before slideshow starts (1-3600)
slide_interval_seconds: 5        # Duration each photo displays (1-60)
photos_source: media             # Where to find photos: "media", "share", or "addon"
clock_position: bottom-center    # Clock position: bottom-center, top-center, top-left, top-right, bottom-left, bottom-right
weather_entity: ""               # HA weather entity ID (e.g., "weather.home")
media_player_entity: ""          # HA media player entity ID (e.g., "media_player.spotify")
media_player_sources: ""         # Comma-separated sources that trigger Now Playing (empty = all)
night_mode_enabled: true         # Dim greyscale clock only during the night window
night_mode_start: "21:00"        # HH:MM, 24-hour
night_mode_end: "05:00"          # HH:MM; windows crossing midnight are fine
night_mode_brightness: 15        # Night clock brightness, percent (1-100)
motion_photos_enabled: true      # Play the motion in Live Photos / Motion Photos
```

### iPhone photos (HEIC) and Live Photos

HEIC files are decoded to JPEG by the app, so you can copy them across
straight from your phone - no converting first. The decoded copy is cached, so
each photo is only converted once; dates and locations read from it appear from
the next time the page loads.

A Live Photo is two files, `IMG_0001.HEIC` and `IMG_0001.MOV`. Copy both into
the same folder and the screensaver plays the motion once each time the photo
comes up, then fades back to the still. Android Motion Photos, which keep the
clip inside the image file itself, work the same way. Only the still is shown
if the clip is missing or your browser can't decode it.

## Usage

1. Access the screensaver at `http://homeassistant.local:8080`
2. Your Home Assistant dashboard will be displayed
3. After the configured idle time, photos will start with an on-screen clock
4. Photos display in random order with adaptive text color for the clock
5. If a media player is configured and playing, the screensaver shows album art with track info and playback controls
6. Touch the screen to return to the dashboard (tap left edge to go back a photo)

## Why Python?

This app was originally written in Rust but rewritten in Python for better Home Assistant compatibility:

| Metric | Rust | Python |
|--------|------|--------|
| Build time | 5-10 minutes | 30 seconds ⚡ |
| Image size | ~500 MB | ~80 MB 💾 |
| HA ecosystem | Uncommon | Standard 🏠 |
| Maintenance | Complex | Simple ✅ |

## Documentation

- **[ha-screensaver/README.md](ha-screensaver/README.md)** - App documentation: every option, photo formats, Live Photos
- **[ha-screensaver/CHANGELOG.md](ha-screensaver/CHANGELOG.md)** - Release history
- **[AGENTS.md](AGENTS.md)** - Architecture notes for contributors and coding agents

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

### App doesn't appear after copying (local install)
- Check that `config.yaml` is at `/local_apps/ha-screensaver/config.yaml` (not nested one level deeper)
- Fix permissions if needed: `chmod -R 755 /local_apps/ha-screensaver`
- Run **Check for updates** in the app store again, or restart Home Assistant

### App won't build or start
- Read the app's **Log** tab (**Settings** → **Apps** → **Home Assistant Screensaver** → **Log**)
- Check free disk space and network access (the build downloads Python packages)
- Remove and reinstall the app to force a clean build

### No photos showing
- Check that photos are in the top level of the configured folder (subfolders are not scanned)
- Verify supported formats: JPG, JPEG, PNG, GIF, WebP, HEIC, HEIF
- Check the app's **Log** tab for errors

### Slideshow doesn't start
- Ensure `idle_timeout_seconds` is what you expect, and stop touching the screen for that long
- Verify at least one photo exists (night mode works without photos)
- Check the browser console (F12) for errors

### Can't open the web UI
- Confirm the app is running
- Make sure nothing else uses port 8080, or use **Open Web UI** (ingress) instead
- Try the IP directly: `http://<ha-ip>:8080`

### Slow or laggy slideshow
- Resize very large photos (around 1920x1080 is plenty) and keep folders to a sensible size
- The first scan of GPS-tagged photos is slow because locations are looked up at 1 per second; results are cached

## Project Structure

```
ha-screensaver/
├── ha-screensaver/            # Home Assistant app
│   ├── app.py                 # Main Python Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Container build instructions
│   ├── run.sh                # Startup script
│   ├── config.yaml           # App configuration (options, schema, version)
│   ├── static/               # Frontend files
│   │   ├── index.html
│   │   └── app.js
│   ├── README.md             # App documentation
│   └── CHANGELOG.md
├── repository.yaml            # App repository configuration
├── AGENTS.md                  # Contributor/agent notes (CLAUDE.md symlinks here)
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
- `GET /photos/<filename>` - Serve individual photo (HEIC/HEIF decoded to JPEG)
- `GET /api/motion/<filename>` - Serve a photo's Live/Motion clip as MP4

## Contributing

Found a bug or have a feature request? Open an issue or pull request on GitHub. Architecture notes are in [AGENTS.md](AGENTS.md).

## License

MIT

## Acknowledgments

- Originally inspired by the need for a simple Home Assistant screensaver
- Migrated from Rust to Python for better HA Green compatibility
