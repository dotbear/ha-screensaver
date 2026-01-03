# Installation Guide - Python Version

## Overview

This guide walks you through installing the **Python version** of the Home Assistant Screensaver add-on. This version is optimized for the Home Assistant Green with much faster builds and smaller image size.

## Prerequisites

- Home Assistant with SSH add-on installed
- SSH access to your Home Assistant
- Photos to display (optional, but recommended)

## Installation Methods

### Method 1: Direct SCP (Recommended)

**Step 1:** Copy the add-on to your Home Assistant

```bash
# From your computer, in the ha-screensaver directory
scp -r addon/ha-screensaver root@homeassistant.local:/addons/
```

Replace `homeassistant.local` with your HA's IP address if needed (e.g., `192.168.1.100`).

**Step 2:** Reload add-ons in Home Assistant

1. Open Home Assistant web interface
2. Go to **Settings** → **Add-ons**
3. Click **⋮** (three dots menu) → **Check for updates**
4. You should now see "Home Assistant Screensaver" under **Local add-ons**

**Step 3:** Install the add-on

1. Click on **"Home Assistant Screensaver"**
2. Click **"Install"**
3. Wait ~30 seconds for the build to complete ⚡
4. Once installed, go to **Configuration** tab

**Step 4:** Configure

```yaml
idle_timeout_seconds: 60
photos_source: media
```

Options:
- `idle_timeout_seconds`: How long (in seconds) to wait before showing slideshow (1-3600)
- `photos_source`: Where to find photos
  - `media` - Use Home Assistant media library (recommended)
  - `share` - Use /share folder
  - `addon` - Use add-on's internal photos folder

**Step 5:** Start the add-on

1. Click **"Start"**
2. Enable **"Start on boot"** if you want it to auto-start
3. Click **"Open Web UI"** or navigate to `http://homeassistant.local:8080`

---

### Method 2: Using File Editor or SSH

If you have the File Editor add-on or prefer using SSH:

**Step 1:** SSH into Home Assistant

```bash
ssh root@homeassistant.local
```

**Step 2:** Create the add-on directory

```bash
mkdir -p /addons/ha-screensaver
cd /addons/ha-screensaver
```

**Step 3:** Copy each file

You'll need to copy these files from your computer:
- `app.py`
- `requirements.txt`
- `Dockerfile`
- `run.sh`
- `config.yaml`
- `build.yaml`
- `README.md`
- `static/` (entire folder)

Then follow steps 2-5 from Method 1.

---

## Adding Photos

### Option 1: Home Assistant Media Library (Easiest)

1. In Home Assistant: **Media** → **Local Media**
2. Click the **upload** button
3. Select and upload your photos
4. The screensaver will automatically find them!

### Option 2: Samba Share

If you have the Samba add-on:

1. Connect to your HA via network share
2. Navigate to `media` folder
3. Copy photos there
4. Photos will appear in the slideshow

### Option 3: Auto-upload from iPhone

Use a file sync app to automatically upload photos:

**PhotoSync:**
1. Install PhotoSync on iPhone
2. Configure destination: SMB/WebDAV to your HA
3. Set destination folder to `/media` or `/share`
4. Enable auto-upload
5. New photos sync automatically!

**Documents by Readdle:**
1. Install Documents app
2. Add your HA as WebDAV/SMB connection
3. Enable photo backup to `/media` folder

**Nextcloud (if installed):**
1. Install Nextcloud add-on on HA
2. Install Nextcloud app on iPhone  
3. Enable auto-upload
4. Point screensaver to Nextcloud photos folder

---

## Testing Locally (Before Installing on HA)

You can test the Python app on your computer first:

```bash
cd addon/ha-screensaver

# Run the test script
./test_local.sh

# Or manually:
pip3 install -r requirements.txt
mkdir test-photos
cp ~/Pictures/*.jpg test-photos/
python3 app.py
```

Then open http://localhost:8080 in your browser!

---

## Troubleshooting

### Add-on doesn't appear after copying

**Problem:** Local add-ons section is empty

**Solutions:**
1. Verify files are in `/addons/ha-screensaver/` (not `/addons/addon/ha-screensaver/`)
2. Check that `config.yaml` exists: `ls -la /addons/ha-screensaver/config.yaml`
3. Restart Home Assistant: **Settings** → **System** → **Restart**
4. Check file permissions: `chmod -R 755 /addons/ha-screensaver`

---

### Build fails

**Problem:** Installation fails with error message

**Solutions:**
1. Check the build logs in the add-on page
2. Common issues:
   - Python not available: Update HA to latest version
   - Network issues: Check internet connection
   - Disk space: Free up space on HA Green
3. Try rebuilding: Remove add-on and install again

---

### No photos in slideshow

**Problem:** Slideshow shows no photos or is empty

**Solutions:**
1. Verify photos are in the correct location:
   - If `photos_source: media`, check HA Media browser
   - If `photos_source: share`, check `/share` folder via SSH
2. Check supported formats: JPG, JPEG, PNG, GIF, WebP
3. Check add-on logs: **Add-ons** → **HA Screensaver** → **Log**
4. Verify permissions: `ls -la /media` (via SSH)

---

### Slideshow doesn't start

**Problem:** Dashboard stays visible, never switches to slideshow

**Solutions:**
1. Check `idle_timeout_seconds` is set correctly (not 0 or negative)
2. Move your mouse/touch away and wait for timeout period
3. Check browser console for errors (F12 → Console)
4. Verify at least one photo exists
5. Try refreshing the page (F5)

---

### Can't access Web UI

**Problem:** Opening Web UI shows connection error

**Solutions:**
1. Verify add-on is running (green "Running" status)
2. Check logs for errors
3. Verify port 8080 is not used by another add-on:
   - SSH: `netstat -ln | grep 8080`
4. Try accessing via IP: `http://192.168.x.x:8080`
5. Check firewall settings

---

### Performance issues

**Problem:** Slideshow is slow or laggy

**Solutions:**
1. Reduce number of photos (if >1000)
2. Resize photos to reasonable size (1920x1080 max)
3. Check HA Green's resource usage:
   - **Settings** → **System** → **Hardware**
4. Consider enabling photo caching (see BUG_FIXES.md)

---

## Verification Checklist

After installation, verify:

- [ ] Add-on appears in **Settings** → **Add-ons**
- [ ] Add-on installs successfully (~30 seconds)
- [ ] Configuration options are available
- [ ] Add-on starts without errors
- [ ] Web UI is accessible on port 8080
- [ ] Home Assistant dashboard loads in the iframe
- [ ] At least one photo is uploaded
- [ ] `/api/photos` endpoint returns photo list
- [ ] Slideshow activates after idle timeout
- [ ] Touching screen returns to dashboard
- [ ] Add-on logs show no errors

---

## Configuration Reference

### Full config.yaml options

```yaml
# How long to wait before starting slideshow (seconds)
idle_timeout_seconds: 60

# Where to find photos
# Options: "media", "share", "addon"
photos_source: "media"
```

### Valid ranges

- `idle_timeout_seconds`: 1 to 3600 (1 second to 1 hour)
- `photos_source`: Must be one of: "media", "share", "addon"

### Default values

If not specified, defaults are:
- `idle_timeout_seconds`: 60
- `photos_source`: "media"

---

## Next Steps

1. **Upload photos** to HA media library
2. **Configure auto-upload** from your phone (PhotoSync, etc.)
3. **Set idle timeout** to your preference
4. **Mount tablet** on wall and enjoy!

---

## Support

- **Logs:** Settings → Add-ons → HA Screensaver → Log
- **Code:** Check `app.py` (heavily commented with Elixir comparisons!)
- **Bugs:** See `BUG_FIXES.md` for known issues and fixes
- **Migration:** See `PYTHON_MIGRATION.md` for Rust → Python changes

The Python version is production-ready and well-documented! 🎉
