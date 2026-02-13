# Home Assistant Screensaver Add-on

A photo slideshow screensaver for Home Assistant that displays your HA dashboard and automatically switches to a photo slideshow after idle time.

## About

This add-on provides a fullscreen web interface that shows your Home Assistant dashboard. After a configurable period of inactivity, it automatically switches to a beautiful photo slideshow using images from your Home Assistant media library or shared folders.

Perfect for wall-mounted tablets or kiosk displays!

## Features

- Displays Home Assistant dashboard in fullscreen
- Automatic idle detection with configurable timeout
- Photo slideshow from your media library **or Google Photos**
- Touch/click to exit slideshow
- Supports JPG, PNG, GIF, and WebP images
- EXIF metadata display (date and location)
- Weather overlay integration
- Lightweight and efficient

## Installation

1. Click the "Add Repository" button below or manually add this repository to your Home Assistant add-on store
2. Install the "Home Assistant Screensaver" add-on
3. Start the add-on
4. Open the Web UI or navigate to `http://homeassistant.local:8080`

## Configuration

```yaml
idle_timeout_seconds: 60
slide_interval_seconds: 5
photos_source: "media"
clock_position: "bottom-center"
weather_entity: ""
google_photos_enabled: false
google_photos_client_id: ""
google_photos_client_secret: ""
google_photos_refresh_interval: 3600
```

### Option: `idle_timeout_seconds`

Number of seconds of inactivity before the slideshow starts.

Default: `60` (Range: 1-3600)

### Option: `slide_interval_seconds`

Number of seconds each photo is displayed before transitioning to the next.

Default: `5` (Range: 1-60)

### Option: `photos_source`

Where to find photos for the slideshow:
- `media`: Use photos from `/media` folder (Home Assistant media library)
- `share`: Use photos from `/share` folder
- `addon`: Use photos from the add-on's own photos folder
- `google_photos`: Use photos from Google Photos

Default: `media`

### Option: `clock_position`

Position of the clock overlay on the slideshow:
- `bottom-center` (default)
- `top-center`
- `top-left`
- `top-right`
- `bottom-left`
- `bottom-right`

Default: `bottom-center`

### Option: `weather_entity`

The Home Assistant weather entity to display on the slideshow (e.g., `weather.home`). Leave empty to disable.

Default: `""` (disabled)

### Option: `google_photos_enabled`

Enable Google Photos integration.

Default: `false`

### Option: `google_photos_client_id`

Your Google OAuth 2.0 Client ID. Required for Google Photos integration.

See "Google Photos Setup" section below for instructions.

Default: `""` (empty)

### Option: `google_photos_client_secret`

Your Google OAuth 2.0 Client Secret. Required for Google Photos integration.

See "Google Photos Setup" section below for instructions.

Default: `""` (empty)

### Option: `google_photos_refresh_interval`

How often to refresh the photo list from Google Photos, in seconds.

Default: `3600` (1 hour, Range: 60-86400)

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

## Google Photos Setup

To use photos from your Google Photos library:

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing one)
3. Enable the **Google Photos Picker API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Photos Picker API"
   - Click "Enable"

### 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External
   - App name: "Home Assistant Screensaver"
   - Add your email as developer contact
   - Scopes: Add `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`
4. Application type: "Web application"
5. Authorized redirect URIs: Add `http://YOUR_HA_URL:8080/api/google-photos/callback`
   - Example: `http://homeassistant.local:8080/api/google-photos/callback`
6. Click "Create" and save your Client ID and Client Secret

### 3. Configure the Add-on

1. In the add-on configuration, set:
   ```yaml
   photos_source: "google_photos"
   google_photos_enabled: true
   google_photos_client_id: "YOUR_CLIENT_ID"
   google_photos_client_secret: "YOUR_CLIENT_SECRET"
   ```
2. Restart the add-on

### 4. Authenticate and Select Photos

1. Access the screensaver web UI
2. Click the "Google Photos" button in the bottom-right corner
3. Click "Connect Google Photos" and sign in
4. Click "Select Photos" to open the Google Photos picker
5. Select the photos you want to use in the slideshow
6. Click "Done" in the picker

Your selected photos will now be used in the slideshow!

**Note:** Google Photos doesn't provide location metadata for privacy reasons, so only the date taken will be displayed in the EXIF overlay.

## Usage

1. Access the screensaver at `http://homeassistant.local:8080`
2. Your Home Assistant dashboard will be displayed
3. After the configured idle time, the photo slideshow will start
4. Touch the screen to return to the dashboard

## Support

For issues and feature requests, please visit the GitHub repository.
