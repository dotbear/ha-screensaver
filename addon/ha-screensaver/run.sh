#!/usr/bin/with-contenv bashio

# Get configuration
IDLE_TIMEOUT=$(bashio::config 'idle_timeout_seconds')
PHOTOS_SOURCE=$(bashio::config 'photos_source')

bashio::log.info "Starting Home Assistant Screensaver..."
bashio::log.info "Idle timeout: ${IDLE_TIMEOUT} seconds"
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

# Create config.json
cat > /app/config.json <<EOF
{
  "home_assistant_url": "http://supervisor/core",
  "photos_folder": "${PHOTOS_FOLDER}",
  "idle_timeout_seconds": ${IDLE_TIMEOUT}
}
EOF

# Start the screensaver
bashio::log.info "Starting screensaver server on port 8080..."
exec /usr/local/bin/ha-screensaver
