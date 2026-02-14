# Changelog

## 1.2.2 (2026-02-14)

### Bug Fixes
- **Google Photos OAuth Fix** - Added direct port access (8080) to enable Google OAuth authentication
  - Google OAuth requires direct URL access and doesn't work through Home Assistant's ingress (iframe)
  - Add-on now exposes port 8080 for direct access from local network
  - Updated documentation with clear instructions for OAuth setup and troubleshooting
  - Users can now access the app at `http://HA_IP:8080` for OAuth authentication

## 1.2.1 (2026-02-14)

### Bug Fixes
- Fixed startup crash when Google Photos is enabled - the add-on no longer tries to create an empty photos directory when `photos_source` is set to `google_photos`

## 1.2.0 (2026-02-13)

### Major Features
- **Google Photos Integration** - Added support for using photos from Google Photos as an alternative to local storage
  - OAuth 2.0 authentication with Google Photos Picker API
  - Interactive photo picker UI for selecting photos from your Google Photos library
  - Automatic photo caching and refresh functionality
  - Metadata display showing date taken from Google Photos (location not available due to privacy)
  - New configuration options: `google_photos_enabled`, `google_photos_client_id`, `google_photos_client_secret`, `google_photos_refresh_interval`
  - New `photos_source` option: `google_photos`

### Improvements
- Enhanced photo source configuration with `google_photos` option
- Added visual Google Photos management button in web UI
- Modal interface for Google Photos authentication and photo selection
- Automatic session polling and photo fetching
- Image proxy endpoint for secure Google Photos image delivery

### Technical Changes
- Added dependencies: `google-auth`, `google-auth-oauthlib`, `requests`
- New API endpoints for Google Photos integration:
  - `/api/google-photos/status` - Check authentication status
  - `/api/google-photos/auth-url` - Get OAuth authorization URL
  - `/api/google-photos/callback` - Handle OAuth callback
  - `/api/google-photos/create-session` - Create picker session
  - `/api/google-photos/poll-session/<id>` - Poll session status
  - `/api/google-photos/fetch-photos/<id>` - Fetch selected photos
  - `/api/google-photos/proxy-image` - Proxy Google Photos images
- Enhanced configuration system to support both local and Google Photos sources

## 1.1.0 (2026-01-03)

### Features
- Added on-screen clock display during slideshow with time and date
- Adaptive clock color - automatically switches between white and black text based on image brightness for optimal readability
- Random slide selection - photos now appear in random order instead of sequential
- Configurable slide interval - set custom duration (1-60 seconds) for how long each photo displays
- Settings button auto-hides during slideshow for cleaner display

### Improvements
- Removed redundant clock font configuration options (now uses clean default styling)
- Enhanced slideshow experience with smart color adaptation

## 1.0.0 (2026-01-03)

### Features
- Initial release
- Photo slideshow from Home Assistant media library
- Configurable idle timeout
- Support for multiple photo sources (media, share, addon folders)
- Fullscreen Home Assistant dashboard display
- Touch/click to exit slideshow
- Support for JPG, PNG, GIF, and WebP images
- Optimized for ARM devices (Home Assistant Green)

### Notes
- Migrated from Google Photos API (deprecated March 31, 2025) to local photo management
- Designed specifically for Home Assistant integration
