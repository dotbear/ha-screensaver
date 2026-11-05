#!/usr/bin/with-contenv bashio

# Get configuration from Home Assistant add-on options
IDLE_TIMEOUT=$(bashio::config 'idle_timeout_seconds')
SLIDE_INTERVAL=$(bashio::config 'slide_interval_seconds')
PHOTOS_SOURCE=$(bashio::config 'photos_source')
CLOCK_POSITION=$(bashio::config 'clock_position')
WEATHER_ENTITY=$(bashio::config 'weather_entity')
MEDIA_PLAYER_ENTITY=$(bashio::config 'media_player_entity')
MEDIA_PLAYER_SOURCES=$(bashio::config 'media_player_sources')
NIGHT_MODE_ENABLED=$(bashio::config 'night_mode_enabled')
NIGHT_MODE_START=$(bashio::config 'night_mode_start')
NIGHT_MODE_END=$(bashio::config 'night_mode_end')
NIGHT_MODE_BRIGHTNESS=$(bashio::config 'night_mode_brightness')
MOTION_PHOTOS_ENABLED=$(bashio::config 'motion_photos_enabled')

# Log startup information
bashio::log.info "Starting Home Assistant Screensaver..."
bashio::log.info "Idle timeout: ${IDLE_TIMEOUT} seconds"
bashio::log.info "Slide interval: ${SLIDE_INTERVAL} seconds"
bashio::log.info "Clock position: ${CLOCK_POSITION}"
bashio::log.info "Weather entity: ${WEATHER_ENTITY}"
bashio::log.info "Media player entity: ${MEDIA_PLAYER_ENTITY}"
bashio::log.info "Media player sources: ${MEDIA_PLAYER_SOURCES}"
bashio::log.info "Photos source: ${PHOTOS_SOURCE}"
bashio::log.info "Night mode: ${NIGHT_MODE_ENABLED} (${NIGHT_MODE_START} - ${NIGHT_MODE_END}, ${NIGHT_MODE_BRIGHTNESS}% brightness)"
bashio::log.info "Motion photos: ${MOTION_PHOTOS_ENABLED}"

# Determine photos folder based on configuration
case "${PHOTOS_SOURCE}" in
    "media")
        PHOTOS_FOLDER="/media"
        ;;
    "share")
        PHOTOS_FOLDER="/share"
        ;;
    *)
        PHOTOS_FOLDER="/app/photos"
        ;;
esac

bashio::log.info "Photos folder: ${PHOTOS_FOLDER}"

# Create the photos folder if it doesn't exist
mkdir -p "${PHOTOS_FOLDER}"

# Serialize the validated options instead of interpolating strings into JSON.
# A source name containing a quote/backslash must not break the whole config.
SCREENSAVER_PHOTOS_FOLDER="${PHOTOS_FOLDER}" python3 - <<'PY'
import json
import os
from pathlib import Path

with open('/data/options.json') as source:
    config = json.load(source)
config.update({
    'home_assistant_url': 'http://homeassistant.local:8123',
    'photos_folder': os.environ['SCREENSAVER_PHOTOS_FOLDER'],
})
scratch = Path('/app/config.json.tmp')
scratch.write_text(json.dumps(config))
scratch.replace('/app/config.json')
PY

bashio::log.info "Configuration file created"
bashio::log.info "Starting Python server..."

# Start the Python application using Gunicorn
exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --worker-class gthread \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app
