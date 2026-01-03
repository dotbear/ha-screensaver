# Home Assistant Screensaver

A Rust-based web application that displays your Home Assistant UI and automatically switches to a photo slideshow after a period of inactivity.

## Features

- Displays Home Assistant UI in an iframe
- Automatic idle detection with configurable timeout
- Slideshow of photos from a local folder
- Touch/click to exit slideshow and return to Home Assistant
- Persistent configuration via JSON file
- Settings UI for easy configuration
- Supports JPG, PNG, GIF, and WebP images

## Prerequisites

- Rust and Cargo (install from [rustup.rs](https://rustup.rs/))
- A Home Assistant instance
- A browser that allows iframe embedding (Chrome, Edge, Safari - Firefox may block due to X-Frame-Options)

## Installation

1. Build the project:
```bash
cargo build --release
```

2. Create a photos folder and add your photos:
```bash
mkdir -p photos
cp /path/to/your/photos/*.jpg photos/
```

3. Run the server:
```bash
cargo run --release
```

The server will start on `http://0.0.0.0:8080`

## Configuration

### Via Settings UI

1. Open the application in your browser
2. Click the "⚙️ Settings" button in the top-right corner
3. Configure:
   - **Home Assistant URL**: Your Home Assistant instance URL (e.g., `http://homeassistant.local:8123`)
   - **Idle Timeout**: Number of seconds before slideshow starts (default: 60)
   - **Photos Folder**: Path to your photos folder (default: `./photos`)

### Via config.json

The configuration is stored in `config.json` in the project root. You can also edit this file directly:

```json
{
  "home_assistant_url": "http://homeassistant.local:8123",
  "photos_folder": "./photos",
  "idle_timeout_seconds": 60
}
```

## Usage

1. Start the server
2. Open the application on your tablet browser (navigate to `http://<server-ip>:8080`)
3. Configure your Home Assistant URL in settings
4. The Home Assistant UI will be displayed
5. After the configured idle period, the slideshow will automatically start
6. Touch the screen to exit the slideshow and return to Home Assistant

## Adding Photos

### From Local Storage

Simply copy image files to the `photos` folder:

```bash
cp ~/Pictures/*.jpg photos/
```

### From Home Assistant Media Folder

If you want to use photos from your Home Assistant's media folder:

1. Find your Home Assistant media folder location (usually `/config/media` or similar)
2. Either:
   - Copy photos to the screensaver's photos folder, OR
   - Update the `photos_folder` setting to point to your HA media folder

### Auto-upload from iPhone

**Note:** Google Photos API no longer supports automatic album access as of March 31, 2025. Here are alternative solutions:

1. **File Sync Apps** (Recommended):
   - Install **PhotoSync**, **Documents by Readdle**, or similar on iPhone
   - Configure auto-upload to your computer/server via SMB, WebDAV, or FTP
   - Point the screensaver to the sync destination folder

2. **iCloud Photos**:
   - Enable iCloud Photos on your iPhone
   - Use iCloud for Windows/Mac to sync photos locally
   - Point the screensaver to the iCloud Photos folder

3. **Manual Transfer**:
   - Periodically copy photos from iPhone via AirDrop, USB, or file transfer
   - Add them to the photos folder

## API Endpoints

- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration
- `GET /api/photos` - Get list of photo URLs for slideshow
- `GET /photos/*` - Serve photos from the photos folder

## Development

Run in development mode with hot reload:
```bash
cargo watch -x run
```

## Deployment

For deployment on your tablet:

1. Build the release binary:
```bash
cargo build --release
```

2. Copy the binary and static files to your server
3. Run the binary (consider using systemd or similar for auto-start)

## License

MIT
