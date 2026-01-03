# Home Assistant Screensaver Add-on

A photo slideshow screensaver for Home Assistant that displays your HA dashboard and automatically switches to a photo slideshow after idle time.

## About

This add-on provides a fullscreen web interface that shows your Home Assistant dashboard. After a configurable period of inactivity, it automatically switches to a beautiful photo slideshow using images from your Home Assistant media library or shared folders.

Perfect for wall-mounted tablets or kiosk displays!

## Features

- Displays Home Assistant dashboard in fullscreen
- Automatic idle detection with configurable timeout
- Photo slideshow from your media library
- Touch/click to exit slideshow
- Supports JPG, PNG, GIF, and WebP images
- Lightweight and efficient

## Installation

1. Click the "Add Repository" button below or manually add this repository to your Home Assistant add-on store
2. Install the "Home Assistant Screensaver" add-on
3. Start the add-on
4. Open the Web UI or navigate to `http://homeassistant.local:8080`

## Configuration

```yaml
idle_timeout_seconds: 60
photos_source: "media"
```

### Option: `idle_timeout_seconds`

Number of seconds of inactivity before the slideshow starts.

Default: `60`

### Option: `photos_source`

Where to find photos for the slideshow:
- `media`: Use photos from `/media` folder (Home Assistant media library)
- `share`: Use photos from `/share` folder
- `addon`: Use photos from the add-on's own photos folder

Default: `media`

## How to Add Photos

### Using Home Assistant Media Library (Recommended)

1. In Home Assistant, go to **Media** → **Local Media**
2. Click the upload button
3. Upload your photos
4. The screensaver will automatically find and display them

### Using the Share Folder

1. Copy photos to your Home Assistant's `/share` directory
2. Set `photos_source: "share"` in the add-on configuration
3. Restart the add-on

### Auto-upload from iPhone

Use a file sync app like:
- **PhotoSync** - Auto-upload to Home Assistant via SMB/WebDAV
- **Documents by Readdle** - File transfer and sync
- **Nextcloud** (if installed) - Native sync support

Point the sync destination to your Home Assistant media or share folder.

## Usage

1. Access the screensaver at `http://homeassistant.local:8080`
2. Your Home Assistant dashboard will be displayed
3. After the configured idle time, the photo slideshow will start
4. Touch the screen to return to the dashboard

## Support

For issues and feature requests, please visit the GitHub repository.
