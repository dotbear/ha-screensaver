# Installing Home Assistant Screensaver

## Method 1: Custom Repository (Easiest - Recommended)

### Step 1: Add Repository to Home Assistant

1. In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** menu (three dots) in the top right corner
3. Select **Repositories**
4. Add this URL: `https://github.com/dotbear/ha-screensaver`
5. Click **Add**
6. Click **Close**

### Step 2: Install the Add-on

1. Refresh the Add-on Store page
2. Scroll down or search for **"Home Assistant Screensaver"**
3. Click on the add-on
4. Click **"Install"** (takes ~30 seconds)

### Step 3: Configure and Start

1. Go to the **Configuration** tab
2. Set your preferences:
   - `idle_timeout_seconds`: 60 (time before slideshow starts)
   - `slide_interval_seconds`: 5 (duration each photo displays)
   - `photos_source`: "media" (to use HA media library)
   - `weather_entity`: Optional weather entity ID
3. Click **"Save"**
4. Click **"Start"**
5. Enable **"Start on boot"** if desired
6. Click **"Open Web UI"** or navigate to `http://homeassistant.local:8080`

## Method 2: Manual Installation via SSH

### Step 1: SSH into your Home Assistant

```bash
ssh root@homeassistant.local
```

### Step 2: Navigate to the addons directory

```bash
cd /addons
```

If the directory doesn't exist, create it:
```bash
mkdir -p /addons
```

### Step 3: Copy the add-on files

From your computer, copy the entire `ha-screensaver` directory to your Home Assistant:

```bash
scp -r ha-screensaver root@homeassistant.local:/addons/
```

Or use an SFTP client like FileZilla:
- Host: `homeassistant.local` (or your HA IP)
- Username: `root`
- Password: Your SSH add-on password
- Upload the `ha-screensaver` folder to `/addons/`

### Step 4: Reload Add-ons in Home Assistant

1. In Home Assistant, go to **Settings** → **Add-ons**
2. Click the **⋮** menu (three dots) in the top right
3. Click **"Check for updates"** or refresh the page
4. You should now see **"Home Assistant Screensaver"** in the add-on list under "Local add-ons"

### Step 5: Install and Configure

1. Click on the **Home Assistant Screensaver** add-on
2. Click **"Install"**
3. Wait for installation to complete
4. Configure options:
   - `idle_timeout_seconds`: 60 (or your preference)
   - `photos_source`: "media" (to use HA media library)
5. Click **"Start"**
6. Enable **"Start on boot"** if you want it to auto-start
7. Click **"Open Web UI"** or navigate to `http://homeassistant.local:8080`

## Method 2: Using Samba Share

If you have the Samba add-on installed:

1. Access your Home Assistant via network share
2. Navigate to the `addons` folder
3. Create a new folder called `ha-screensaver`
4. Copy all files from `ha-screensaver` into this folder
5. Follow steps 4-7 from Method 1 above

## Adding Photos

### Using Home Assistant Media Browser

1. In Home Assistant, go to **Media** → **Local Media**
2. Click the **upload** icon
3. Upload your photos
4. The screensaver will automatically find them in `/media`

### Using Samba Share

1. Connect to your Home Assistant via Samba
2. Navigate to the `media` folder
3. Copy your photos there
4. They'll be available to the screensaver

## Troubleshooting

**Add-on doesn't appear after copying files:**
- Make sure the files are in `/addons/ha-screensaver/` (not `/addons/ha-screensaver/`)
- Verify `config.yaml` exists in the directory
- Restart Home Assistant: **Settings** → **System** → **Restart**

**Add-on fails to start:**
- Check the add-on logs: Click on the add-on → **Log** tab
- Make sure the `/media` folder has some images
- Try changing `photos_source` to a different location

**No photos showing in slideshow:**
- Make sure you have images in the configured photos source
- Supported formats: JPG, JPEG, PNG, GIF, WebP
- Check the add-on logs for errors

**Can't access Web UI:**
- Make sure the add-on is started
- Check that port 8080 is not used by another service
- Try accessing via IP: `http://192.168.x.x:8080`

## Building Locally (Advanced)

If you want to build the Docker image locally on your Home Assistant:

```bash
# SSH into Home Assistant
ssh root@homeassistant.local

# Navigate to addon directory
cd /addons/ha-screensaver

# Build using the Home Assistant builder
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.19 -t local/ha-screensaver .
```

Then update `config.yaml` to use `image: local/ha-screensaver` instead of the GitHub image.
