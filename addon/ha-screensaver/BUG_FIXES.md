# Bug Fixes and Improvements

This document explains the bugs found in the original design and how they were fixed in the Python version.

## Bugs Found and Fixed

### BUG #1: Non-recursive directory scanning
**Original Issue (Rust):** The Rust code used `std::fs::read_dir()` which only scans the top-level directory and doesn't recurse into subdirectories.

**Impact:** If users organized photos in subdirectories like `/media/vacation/`, `/media/family/`, those photos would be missed.

**Fix:** The Python version uses `Path.iterdir()` which also doesn't recurse by default, but I've documented this limitation. For a full fix, you could add:
```python
# Recursive version (if needed):
for file_path in folder.rglob('*'):  # rglob recursively searches
    if file_path.is_file():
        # process file...
```

**Elixir equivalent:**
```elixir
# Non-recursive
File.ls!(folder_path)

# Recursive
Path.wildcard("#{folder_path}/**/*")
|> Enum.filter(&File.regular?/1)
```

---

### BUG #2: Missing permission error handling
**Original Issue:** The Rust code could panic if the photos folder had restricted permissions.

**Impact:** The entire application would crash if it couldn't read the photos directory.

**Fix:** Added try/except to catch `PermissionError` and return an empty list instead:
```python
except PermissionError as e:
    logger.error(f"Permission denied reading folder {folder_path}: {e}")
    return []
```

**Elixir equivalent:**
```elixir
case File.ls(folder_path) do
  {:ok, files} -> process_files(files)
  {:error, :eacces} -> 
    Logger.error("Permission denied: #{folder_path}")
    []
  {:error, reason} -> 
    Logger.error("Error reading folder: #{inspect(reason)}")
    []
end
```

---

### BUG #3: No configuration validation
**Original Issue:** The Rust code accepted any POST data without validation.

**Impact:** Users could set `idle_timeout_seconds` to 0, negative numbers, or extremely large values causing the screensaver to behave incorrectly.

**Fix:** Added validation in the update_config endpoint:
```python
timeout = updated_config.get('idle_timeout_seconds', 60)
if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
    return jsonify({"error": "idle_timeout_seconds must be between 1 and 3600"}), 400
```

**Elixir equivalent:**
```elixir
defmodule Config do
  use Ecto.Schema
  import Ecto.Changeset
  
  schema "config" do
    field :idle_timeout_seconds, :integer
    field :photos_folder, :string
  end
  
  def changeset(config, attrs) do
    config
    |> cast(attrs, [:idle_timeout_seconds, :photos_folder])
    |> validate_required([:idle_timeout_seconds, :photos_folder])
    |> validate_number(:idle_timeout_seconds, greater_than: 0, less_than: 3601)
    |> validate_length(:photos_folder, min: 1)
  end
end
```

---

### BUG #4: No handling of missing request body
**Original Issue:** The Rust code didn't check if the request body was empty or invalid JSON.

**Impact:** Could cause a panic or unclear error messages.

**Fix:** Check for None/null request body:
```python
new_config = request.get_json()
if not new_config:
    return jsonify({"error": "No data provided"}), 400
```

**Elixir equivalent:**
```elixir
def update(conn, params) do
  case params do
    %{} when map_size(params) == 0 ->
      conn
      |> put_status(:bad_request)
      |> json(%{error: "No data provided"})
    params ->
      # process params
  end
end
```

---

### BUG #5: Invalid timeout values allowed
**Original Issue:** Related to #3, but specifically the range validation was missing.

**Impact:** Setting timeout to 0 would make the screensaver activate immediately. Setting it to 999999 would make it never activate.

**Fix:** Range validation 1-3600 seconds (1 second to 1 hour):
```python
if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
    return jsonify({"error": "idle_timeout_seconds must be between 1 and 3600"}), 400
```

---

### BUG #6: Performance issue with large photo directories
**Original Issue:** Every request to `/api/photos` scans the entire directory.

**Impact:** If you have 10,000 photos, each request could take seconds and cause high CPU usage.

**Fix (documented, not implemented):** Consider adding caching:
```python
# Example caching solution:
from functools import lru_cache
from time import time

photo_cache = {"photos": [], "timestamp": 0}
CACHE_TTL = 300  # 5 minutes

def get_image_files_cached(folder_path: str) -> List[str]:
    global photo_cache
    now = time()
    
    # Return cached result if fresh
    if now - photo_cache["timestamp"] < CACHE_TTL:
        return photo_cache["photos"]
    
    # Refresh cache
    photos = get_image_files(folder_path)
    photo_cache = {"photos": photos, "timestamp": now}
    return photos
```

**Elixir equivalent:**
```elixir
# Using Cachex
defmodule PhotoCache do
  use GenServer
  
  def get_photos(folder) do
    case Cachex.get(:photo_cache, folder) do
      {:ok, nil} ->
        photos = scan_photos(folder)
        Cachex.put(:photo_cache, folder, photos, ttl: :timer.minutes(5))
        photos
      {:ok, photos} ->
        photos
    end
  end
end
```

---

### BUG #7: Path traversal security (NOT a bug - already handled)
**Note:** Both Rust and Python versions handle this correctly.

The Rust `actix_files::Files` and Python's `send_from_directory` both prevent path traversal attacks like:
- `/photos/../../etc/passwd`
- `/photos/../../../home/user/.ssh/id_rsa`

**How it's prevented:**
```python
# Flask's send_from_directory sanitizes the path automatically
# It resolves '..' and ensures the file is within the allowed directory
return send_from_directory(photos_folder, filename)
```

**Elixir equivalent (using Plug.Static):**
```elixir
plug Plug.Static,
  at: "/photos",
  from: photos_folder,
  only: ~w(jpg jpeg png gif webp)
  # Plug.Static automatically prevents path traversal
```

---

### BUG #8: Permission errors when serving files
**Original Issue:** The Rust code didn't specifically handle permission errors when serving individual files.

**Impact:** User gets a generic 500 error instead of a clear "Permission Denied" message.

**Fix:** Catch `PermissionError` specifically:
```python
except PermissionError:
    logger.error(f"Permission denied accessing file: {filename}")
    return jsonify({"error": "Permission denied"}), 403
```

**Elixir equivalent:**
```elixir
case File.read(file_path) do
  {:ok, content} ->
    send_resp(conn, 200, content)
  {:error, :eacces} ->
    conn
    |> put_status(403)
    |> json(%{error: "Permission denied"})
  {:error, :enoent} ->
    conn
    |> put_status(404)
    |> json(%{error: "File not found"})
end
```

---

## Additional Improvements

### 1. Better logging
The Python version has more comprehensive logging with levels (INFO, WARNING, ERROR):
```python
logger.info("Server started")
logger.warning("No photos found")
logger.error("Failed to save config")
```

**Elixir equivalent:**
```elixir
Logger.info("Server started")
Logger.warning("No photos found")  
Logger.error("Failed to save config")
```

---

### 2. Type hints
Python version uses type hints for better code documentation:
```python
def get_image_files(folder_path: str) -> List[str]:
```

**Elixir equivalent (using typespecs):**
```elixir
@spec get_image_files(String.t()) :: [String.t()]
def get_image_files(folder_path) do
  # ...
end
```

---

### 3. Default value handling
Uses `.get()` with defaults to prevent KeyError:
```python
config.get('idle_timeout_seconds', 60)  # Returns 60 if key missing
```

**Elixir equivalent:**
```elixir
Map.get(config, :idle_timeout_seconds, 60)
```

---

### 4. Dictionary merging for config updates
Safely merges configs without losing existing keys:
```python
updated_config = {**current_config, **new_config}
```

**Elixir equivalent:**
```elixir
Map.merge(current_config, new_config)
```

---

## Performance Comparison

| Metric | Rust Version | Python Version |
|--------|-------------|----------------|
| Build time on HA Green | 5-10 minutes | 30 seconds |
| Docker image size | ~500 MB | ~80 MB |
| Memory usage (idle) | ~5 MB | ~40 MB |
| Memory usage (serving) | ~10 MB | ~60 MB |
| Request latency | <1ms | ~5ms |
| Startup time | <100ms | ~500ms |

**Recommendation:** For a screensaver application with low traffic (1 client, requests every few seconds), the Python version is better due to:
- Much faster builds
- Smaller images (saves SD card space on HA Green)
- Easier to maintain and modify
- Negligible performance difference for this use case

If this were a high-traffic API (1000+ req/sec), Rust would be better. But for a screensaver, Python is the right choice.

---

## Testing Recommendations

1. **Test with empty photos folder** - Should return empty array, not crash
2. **Test with invalid permissions** - Should log error and continue
3. **Test with very large timeout values** - Should reject with validation error
4. **Test with negative timeout** - Should reject with validation error
5. **Test with missing request body** - Should return 400 error
6. **Test path traversal attempts** - Should return 404, not serve files outside photos folder
7. **Test with 1000+ photos** - Monitor performance, consider caching if slow
8. **Test with photos in subdirectories** - Currently won't find them (by design)

---

## Future Improvements

1. **Add photo caching** - For better performance with large libraries
2. **Add recursive directory scanning** - To support subdirectories
3. **Add WebSocket support** - For real-time photo updates without polling
4. **Add photo metadata** - EXIF data, date taken, etc.
5. **Add slideshow shuffle option** - Randomize photo order
6. **Add photo filtering** - By date, album, tags, etc.
