#!/usr/bin/with-contenv bashio

# This script runs when the Home Assistant add-on starts
# bashio is a helper library for HA add-ons (provides bashio::config, bashio::log, etc.)

# Get configuration from Home Assistant add-on options
# Elixir equivalent: Application.get_env(:ha_screensaver, :idle_timeout_seconds)
IDLE_TIMEOUT=$(bashio::config 'idle_timeout_seconds')
SLIDE_INTERVAL=$(bashio::config 'slide_interval_seconds')
PHOTOS_SOURCE=$(bashio::config 'photos_source')

# Log startup information
# Elixir: Logger.info("Starting Home Assistant Screensaver...")
bashio::log.info "Starting Home Assistant Screensaver..."
bashio::log.info "Idle timeout: ${IDLE_TIMEOUT} seconds"
bashio::log.info "Slide interval: ${SLIDE_INTERVAL} seconds"
bashio::log.info "Photos source: ${PHOTOS_SOURCE}"

# Determine photos folder based on configuration
# This is like a case statement in Elixir:
#   case photos_source do
#     "media" -> "/media"
#     "share" -> "/share"
#     _ -> "/app/photos"
#   end
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
# Elixir: File.mkdir_p!(photos_folder)
mkdir -p "${PHOTOS_FOLDER}"

# Create config.json for the Python application
# This writes configuration that app.py will read
# Elixir equivalent: File.write!(config_path, Jason.encode!(config))
cat > /app/config.json <<EOF
{
  "home_assistant_url": "http://homeassistant.local:8123",
  "photos_folder": "${PHOTOS_FOLDER}",
  "idle_timeout_seconds": ${IDLE_TIMEOUT},
  "slide_interval_seconds": ${SLIDE_INTERVAL}
}
EOF

bashio::log.info "Configuration file created"
bashio::log.info "Starting Python server..."

# Start the Python application using Gunicorn
# Gunicorn is a production-ready WSGI server (like Cowboy in Elixir)
#
# Options explained:
#   --bind 0.0.0.0:8080     - Listen on all interfaces, port 8080
#   --workers 2             - Use 2 worker processes (similar to BEAM schedulers)
#   --worker-class gthread  - Use threaded workers for better concurrency
#   --threads 4             - 4 threads per worker = 8 total concurrent handlers
#   --timeout 120           - Request timeout in seconds
#   --access-logfile -      - Log access to stdout (for HA logs)
#   --error-logfile -       - Log errors to stdout
#   app:app                 - Module:callable (app.py file, app variable)
#
# Elixir equivalent:
#   Supervisor.start_link([
#     {Plug.Cowboy, scheme: :http, plug: Router, options: [
#       port: 8080,
#       protocol_options: [max_connections: 8]
#     ]}
#   ], strategy: :one_for_one)
#
exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --worker-class gthread \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app
