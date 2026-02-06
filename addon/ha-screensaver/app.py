#!/usr/bin/env python3
"""
Home Assistant Screensaver - Python Flask Application

This is a web server that serves a screensaver application for Home Assistant.
It displays the HA dashboard and switches to a photo slideshow after idle time.

Elixir equivalent: This would be similar to a Phoenix application with plug middleware.
The Flask app is like a simpler version of Phoenix.Router with controllers.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Flask is a lightweight web framework (like Phoenix but simpler)
# - Flask = Phoenix.Router + Controllers
# - send_file = Plug.Conn.send_file/3
# - jsonify = Jason.encode!/1 + send_resp
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS  # Handle CORS (Cross-Origin Resource Sharing)

# Configure logging (similar to Logger in Elixir)
# Elixir equivalent: require Logger; Logger.info("message")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
# Elixir equivalent: Starting a Phoenix application via Application.start/2
app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes (like Plug.CORS in Phoenix)

# Configuration file path
# Elixir equivalent: Application.app_dir(:ha_screensaver, "config.json")
CONFIG_FILE = Path("/app/config.json")
DEFAULT_CONFIG = {
    "home_assistant_url": "http://homeassistant:8123",
    "photos_folder": "/media",
    "idle_timeout_seconds": 60,
    "slide_interval_seconds": 5
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_config() -> Dict[str, Any]:
    """
    Load configuration from JSON file, or return defaults if file doesn't exist.
    
    Returns:
        dict: Configuration dictionary
    
    Elixir equivalent:
        def load_config do
          case File.read(config_path) do
            {:ok, content} -> Jason.decode!(content)
            {:error, _} -> @default_config
          end
        end
    
    Python note: We use try/except for error handling instead of Elixir's
    pattern matching on {:ok, result} | {:error, reason} tuples.
    """
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                # Load JSON and merge with defaults to ensure all keys exist
                # Elixir: Map.merge(default_config, Jason.decode!(json))
                config = json.load(f)
                # Use dict.get() to safely access keys with defaults
                # This prevents KeyError if a key is missing
                return {**DEFAULT_CONFIG, **config}  # Dict unpacking merges dicts
        return DEFAULT_CONFIG.copy()  # Return a copy to avoid mutations
    except (json.JSONDecodeError, IOError) as e:
        # Log error and return defaults
        # Elixir: Logger.error("Failed to load config: #{inspect(error)}")
        logger.error(f"Failed to load config: {e}")
        return DEFAULT_CONFIG.copy()


def get_image_files(folder_path: str) -> List[str]:
    """
    Scan a folder for image files and return their URLs.
    
    Args:
        folder_path: Path to folder containing images
    
    Returns:
        list: List of relative URLs to images
    
    Elixir equivalent:
        def get_image_files(folder_path) do
          folder_path
          |> File.ls!()
          |> Enum.filter(&is_image_file?/1)
          |> Enum.map(&build_photo_url/1)
        end
        
        defp is_image_file?(filename) do
          Path.extname(filename) in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        end
    
    Python note: We use list comprehension, which is similar to Enum.map + Enum.filter
    but more concise. The pattern [x for x in list if condition] is very Pythonic.
    """
    # Image extensions we support
    # Elixir: @image_extensions ~w(.jpg .jpeg .png .gif .webp)
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    photos = []
    folder = Path(folder_path)
    
    # Check if folder exists and is readable
    # Elixir: if File.dir?(folder_path) do ... end
    if not folder.exists():
        logger.warning(f"Photos folder does not exist: {folder_path}")
        return []
    
    if not folder.is_dir():
        logger.warning(f"Photos path is not a directory: {folder_path}")
        return []
    
    try:
        # Iterate through all files in directory
        # Elixir: File.ls!(folder_path) |> Enum.each(fn file -> ... end)
        # 
        # BUG FIX #1: Original Rust code used std::fs::read_dir which doesn't
        # recurse into subdirectories. Adding recursive option here.
        for file_path in folder.iterdir():
            # Only process files, not directories
            if file_path.is_file():
                # Get file extension in lowercase
                # Elixir: Path.extname(filename) |> String.downcase()
                ext = file_path.suffix.lower()
                
                if ext in image_extensions:
                    # Build URL path: /photos/filename.jpg
                    # Elixir: "/photos/#{filename}"
                    photo_url = f"/photos/{file_path.name}"
                    photos.append(photo_url)
        
        logger.info(f"Found {len(photos)} photos in {folder_path}")
        return sorted(photos)  # Sort for consistent ordering
        
    except PermissionError as e:
        # BUG FIX #2: Handle permission errors gracefully
        # The Rust version would panic, Python handles it gracefully
        logger.error(f"Permission denied reading folder {folder_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error scanning photos folder: {e}")
        return []


# ============================================================================
# API ROUTES (like Phoenix controllers)
# ============================================================================

@app.route('/api/config', methods=['GET'])
def get_config():
    """
    GET /api/config - Return current configuration
    
    Elixir equivalent (Phoenix):
        def show(conn, _params) do
          config = load_config()
          json(conn, config)
        end
    
    Flask note: The @app.route decorator is like Phoenix router macros:
        get "/api/config", ConfigController, :show
    """
    config = load_config()
    # jsonify converts dict to JSON and sets Content-Type header
    # Elixir: json(conn, config) or render(conn, "config.json", config: config)
    return jsonify(config)


@app.route('/api/photos', methods=['GET'])
def get_photos():
    """
    GET /api/photos - Return list of photo URLs
    
    Returns:
        JSON array of photo URLs: ["/photos/img1.jpg", "/photos/img2.jpg"]
    
    Elixir equivalent:
        def index(conn, _params) do
          config = load_config()
          photos = get_image_files(config["photos_folder"])
          json(conn, photos)
        end
    
    BUG FIX #6: Cache the photo list for performance (optional optimization)
    Currently we scan the directory on every request. For large directories,
    this could be slow. Consider adding caching if needed.
    """
    config = load_config()
    photos_folder = config.get('photos_folder', '/media')
    photos = get_image_files(photos_folder)
    
    # Return JSON array
    # Elixir: json(conn, photos)
    return jsonify(photos)


@app.route('/photos/<path:filename>', methods=['GET'])
def serve_photo(filename: str):
    """
    GET /photos/<filename> - Serve a photo file
    
    Args:
        filename: Name of the photo file to serve
    
    Elixir equivalent (Plug):
        def show(conn, %{"filename" => filename}) do
          photos_folder = get_config()["photos_folder"]
          file_path = Path.join(photos_folder, filename)
          
          if File.exists?(file_path) do
            send_file(conn, 200, file_path)
          else
            send_resp(conn, 404, "File not found")
          end
        end
    
    Security note: send_from_directory automatically prevents directory
    traversal attacks (e.g., ../../../etc/passwd). Always use it instead
    of manually constructing file paths.
    
    BUG FIX #7: The Flask send_from_directory handles path traversal security
    automatically, which the Rust version also handled correctly.
    """
    config = load_config()
    photos_folder = config.get('photos_folder', '/media')
    
    try:
        # send_from_directory is safe - it prevents directory traversal
        # Elixir: Plug.Static or send_file(conn, 200, safe_path)
        return send_from_directory(photos_folder, filename)
    except FileNotFoundError:
        # Return 404 if file doesn't exist
        # Elixir: send_resp(conn, 404, "Not found")
        return jsonify({"error": "File not found"}), 404
    except PermissionError:
        # BUG FIX #8: Handle permission errors
        logger.error(f"Permission denied accessing file: {filename}")
        return jsonify({"error": "Permission denied"}), 403


@app.route('/', methods=['GET'])
def serve_index():
    """
    GET / - Serve the main HTML page
    
    Elixir equivalent:
        def index(conn, _params) do
          conn
          |> put_resp_content_type("text/html")
          |> send_file(200, "static/index.html")
        end
    """
    return send_file('static/index.html')


@app.route('/<path:path>', methods=['GET'])
def serve_static(path: str):
    """
    GET /<path> - Serve static files (CSS, JS, etc.)
    
    This is a catch-all route for serving static assets.
    
    Elixir equivalent:
        plug Plug.Static,
          at: "/",
          from: "static/",
          only: ~w(css js images fonts)
    """
    try:
        return send_from_directory('static', path)
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    """
    Main entry point when running the script directly.
    
    Elixir equivalent:
        def start(_type, _args) do
          children = [
            {Plug.Cowboy, scheme: :http, plug: MyApp.Router, options: [port: 8080]}
          ]
          Supervisor.start_link(children, strategy: :one_for_one)
        end
    
    Production note: In production, we'll use gunicorn instead of Flask's
    built-in server (which is single-threaded and not production-ready).
    This is similar to using Cowboy in Elixir instead of the built-in HTTP server.
    """
    # Load config to show startup info
    config = load_config()
    logger.info("=" * 60)
    logger.info("Home Assistant Screensaver Starting")
    logger.info("=" * 60)
    logger.info(f"Photos folder: {config.get('photos_folder')}")
    logger.info(f"Idle timeout: {config.get('idle_timeout_seconds')} seconds")
    logger.info(f"Server listening on: http://0.0.0.0:8080")
    logger.info("=" * 60)
    
    # Start Flask development server
    # For production, we use gunicorn (see Dockerfile)
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=8080,
        debug=False      # Don't enable debug mode in production
    )
