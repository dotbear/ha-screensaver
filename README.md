# Home Assistant Screensaver

A Rust-based web application that displays your Home Assistant UI and automatically switches to a Google Photos slideshow after a period of inactivity.

## Features

- Displays Home Assistant UI in an iframe
- Automatic idle detection with configurable timeout
- Slideshow of photos from Google Photos albums
- Touch/click to exit slideshow and return to Home Assistant
- Persistent configuration via JSON file
- Settings UI for easy configuration

## Prerequisites

- Rust and Cargo (install from [rustup.rs](https://rustup.rs/))
- A Home Assistant instance
- A browser that allows iframe embedding (Chrome, Edge, Safari - Firefox may block due to X-Frame-Options)
- (Optional) Google Photos API credentials for actual photo fetching

## Installation

1. Build the project:
```bash
cargo build --release
```

2. Run the server:
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
   - **Google Photos Album IDs**: Comma-separated list of album IDs (currently using placeholder images)

### Via config.json

The configuration is stored in `config.json` in the project root. You can also edit this file directly:

```json
{
  "home_assistant_url": "http://homeassistant.local:8123",
  "google_photos_album_ids": [],
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

## Google Photos Integration

Currently, the application uses placeholder images from Lorem Picsum. To integrate with actual Google Photos:

1. Set up Google Photos API credentials
2. Implement OAuth2 flow in the Rust backend
3. Update the `/api/photos` endpoint to fetch from Google Photos API

See the Google Photos API documentation: https://developers.google.com/photos

## API Endpoints

- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration
- `GET /api/photos` - Get list of photo URLs for slideshow

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
