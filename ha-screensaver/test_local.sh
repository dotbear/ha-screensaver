#!/bin/bash
# Quick local test script for the Python screensaver
# This lets you test the app before deploying to Home Assistant

echo "========================================"
echo "  Testing Python Screensaver Locally"
echo "========================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi
echo "✓ Python 3 found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip."
    exit 1
fi
echo "✓ pip3 found"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install -q -r requirements.txt

# Create test config
echo ""
echo "Creating test configuration..."
cat > config.json << EOFCONFIG
{
  "home_assistant_url": "http://homeassistant.local:8123",
  "photos_folder": "./test-photos",
  "idle_timeout_seconds": 60
}
EOFCONFIG
echo "✓ Config created: config.json"

# Create test photos directory
mkdir -p test-photos
echo "✓ Test photos directory created: ./test-photos"

# Check if there are any test photos
photo_count=$(find test-photos -type f \( -iname "*.jpg" -o -iname "*.png" -o -iname "*.gif" \) | wc -l)
if [ "$photo_count" -eq 0 ]; then
    echo ""
    echo "⚠️  No photos in test-photos folder."
    echo "   Add some photos to test-photos/ before running."
    echo ""
    echo "   Example:"
    echo "   cp ~/Pictures/*.jpg test-photos/"
else
    echo "✓ Found $photo_count test photos"
fi

echo ""
echo "========================================"
echo "  Starting server on http://localhost:8080"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the app
python3 app.py
