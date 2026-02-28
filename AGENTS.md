# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Cursor, Copilot, etc.) when working with code in this repository.

## Project Overview

Home Assistant add-on that displays the HA dashboard in an iframe and switches to a photo slideshow with clock overlay after user inactivity. When a configured media player is playing music, the screensaver switches to a "now playing" view with album art, track info, and playback/volume controls. Backend is a single-file Flask app (`ha-screensaver/app.py`), frontend is a single ES6 class (`ha-screensaver/static/app.js`). No build step, no bundler, no framework.

## Development Commands

```bash
# Local development (from ha-screensaver/ directory)
cd ha-screensaver
./test_local.sh                          # Sets up config, installs deps, runs server
# Or manually:
pip3 install -r requirements.txt
python3 app.py                           # Serves on http://localhost:8080

# Deploy to HA for testing
scp -r ha-screensaver root@homeassistant.local:/addons/
# Then in HA UI: Settings → Add-ons → HA Screensaver → Rebuild
```

There are no automated tests, linter, or formatter configured.

## Architecture

### Data flow: Config

1. HA add-on UI writes options per `config.yaml` schema
2. `run.sh` reads them via `bashio::config`, writes `/app/config.json`
3. `app.py` reads `/app/config.json` on each API request (falls back to `./config.json` for local dev)
4. Frontend fetches `/api/config` on page load

### Data flow: Photos

1. `run.sh` maps `photos_source` option → filesystem path (`/media`, `/share`, or `/app/photos`)
2. `/api/photos` scans that directory (non-recursive, single level only), extracts EXIF via Pillow
3. GPS coordinates are reverse-geocoded via Nominatim (rate-limited 1 req/sec, cached to `/app/geocache.json`)
4. Frontend receives `[{url, exif: {date, location}}]`, creates DOM slides, picks random order

### Data flow: Weather

`/api/weather` proxies to HA Supervisor API using `SUPERVISOR_TOKEN` env var. Polled every 60 seconds while screensaver is active. Only available when running as an HA add-on.

### Data flow: Media Player

`/api/media` proxies the configured `media_player` entity state from HA. Returns track title, artist, album, album art URL, volume level, and playback state. Polled every 10 seconds while screensaver is active. Album art from HA's internal proxy is served through `/api/media/image` which handles Supervisor auth. Control endpoints (`/api/media/play_pause`, `/api/media/next`, `/api/media/previous`, `/api/media/volume`) call HA's `media_player` service API.

### Frontend state machine

`ScreensaverApp` has three modes:
- **Dashboard mode**: HA iframe visible, idle timer counting down
- **Photo slideshow mode**: Random photo slides with clock, photo info (top-left), and weather (top-right) overlays. Tap anywhere to exit, tap left 10% to go back one photo.
- **Now playing mode**: Activated when the configured media player is playing/paused. Shows album art (blurred background + centered sharp art), track info, transport controls (top center: ⏮ ⏯ ⏭), and volume slider (bottom, 90% width). Photo slideshow pauses; resumes when playback stops.

Clock text color adapts to image brightness by sampling the bottom-center region via canvas. In media mode, clock is forced to white (blurred background is always dark).

### Iframe memory management

The HA frontend leaks memory when left open for extended periods (a known community issue). The screensaver reloads the iframe hourly while active, using a timestamp-based check in the clock tick. The timer is not reset when exiting/re-entering the screensaver — it tracks wall-clock time since the last refresh.

## Key Constraints

- **Single-file architecture is intentional** — don't split `app.py` or `app.js` into modules
- **No recursive directory scanning** — photos are only read from the top level of the configured folder
- **Don't validate config in app.py** — HA's `config.yaml` schema handles validation
- **Nominatim rate limit** — 1 request/sec max; the geocode cache (`geocache.json`) is critical
- **`send_from_directory` for photo serving** — never replace this, it prevents path traversal
- **Photo list is not cached** — `/api/photos` rescans on every request so new photos appear immediately
- **Gunicorn in production** — `run.sh` starts Gunicorn (2 workers, 4 threads); `app.py` `__main__` is for local dev only
- **`/api/media/image` only proxies `/api/` paths** — this prevents it being used as an open proxy

## Adding a Configuration Option

Must be updated in 4 places:
1. `config.yaml` — add to both `options` (default) and `schema` (validation)
2. `run.sh` — read with `bashio::config`, add to the generated `config.json`
3. `app.py` — add to `DEFAULT_CONFIG` dict, use via `load_config()`
4. `app.js` — access from `this.config`
