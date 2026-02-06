#!/usr/bin/with-contenv bashio

# Get configuration from Home Assistant add-on options
IDLE_TIMEOUT=$(bashio::config 'idle_timeout_seconds')
SLIDE_INTERVAL=$(bashio::config 'slide_interval_seconds')
PHOTOS_SOURCE=$(bashio::config 'photos_source')
CLOCK_POSITION=$(bashio::config 'clock_position')
WEATHER_ENTITY=$(bashio::config 'weather_entity')

# Log startup information
bashio::log.info "Starting Home Assistant Screensaver..."
bashio::log.info "Idle timeout: ${IDLE_TIMEOUT} seconds"
bashio::log.info "Slide interval: ${SLIDE_INTERVAL} seconds"
bashio::log.info "Clock position: ${CLOCK_POSITION}"
bashio::log.info "Weather entity: ${WEATHER_ENTITY}"
bashio::log.info "Photos source: ${PHOTOS_SOURCE}"

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

# Create config.json for the Python application
cat > /app/config.json <<EOF
{
  "home_assistant_url": "http://homeassistant.local:8123",
  "photos_folder": "${PHOTOS_FOLDER}",
  "idle_timeout_seconds": ${IDLE_TIMEOUT},
  "slide_interval_seconds": ${SLIDE_INTERVAL},
  "clock_position": "${CLOCK_POSITION}",
  "weather_entity": "${WEATHER_ENTITY}"
}
EOF

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
