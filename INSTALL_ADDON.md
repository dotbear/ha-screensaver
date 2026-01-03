# Installing as a Home Assistant Local Add-on

## Method 1: Using SSH and File Transfer (Easiest)

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

From your computer, copy the entire `addon/ha-screensaver` directory to your Home Assistant:

```bash
scp -r addon/ha-screensaver root@homeassistant.local:/addons/
```

Or use an SFTP client like FileZilla:
- Host: `homeassistant.local` (or your HA IP)
- Username: `root`
- Password: Your SSH add-on password
- Upload the `addon/ha-screensaver` folder to `/addons/`

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
4. Copy all files from `addon/ha-screensaver` into this folder
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
- Make sure the files are in `/addons/ha-screensaver/` (not `/addons/addon/ha-screensaver/`)
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
