class ScreensaverApp {
  constructor() {
    this.config = null;
    this.photos = [];
    this.currentSlideIndex = 0;
    this.slideHistory = [];
    this.photoExif = {};
    this.weather = null;
    this.idleTimer = null;
    this.slideInterval = null;
    this.clockInterval = null;
    this.isScreensaverActive = false;

    this.init();
  }

  async init() {
    await this.loadConfig();
    await this.loadPhotos();
    this.setupEventListeners();
    this.setupIdleDetection();
    this.setupGooglePhotos();

    // Set the iframe source to Home Assistant URL
    const iframe = document.getElementById('ha-iframe');
    iframe.src = this.config.home_assistant_url;
  }

  async loadConfig() {
    try {
      const response = await fetch('api/config');
      this.config = await response.json();

      // Set default slide interval if not present
      if (!this.config.slide_interval_seconds) {
        this.config.slide_interval_seconds = 5;
      }

      console.log('Config loaded:', this.config);
    } catch (error) {
      console.error('Error loading config:', error);
      this.config = {
        home_assistant_url: 'http://homeassistant.local:8123',
        photos_folder: './photos',
        idle_timeout_seconds: 60,
        slide_interval_seconds: 5
      };
    }
  }

  async loadPhotos() {
    try {
      const response = await fetch('api/photos');
      const data = await response.json();
      // API returns [{url, exif}, ...] -- store full objects
      this.photos = data;
      console.log('Photos loaded:', this.photos.length);
    } catch (error) {
      console.error('Error loading photos:', error);
      this.photos = [];
    }
  }

  setupEventListeners() {
    const slideshow = document.getElementById('slideshow');

    const handleSlideshowInteraction = (e) => {
      if (!this.isScreensaverActive) return;
      e.preventDefault();
      e.stopPropagation();

      const x = e.touches ? e.touches[0].clientX : e.clientX;

      if (x < window.innerWidth * 0.1) {
        // Left 10% of screen - go back one image
        this.previousSlide();
        this.resetSlideTimer();
      } else {
        this.stopScreensaver();
      }
    };

    ['mousedown', 'touchstart'].forEach(event => {
      slideshow.addEventListener(event, handleSlideshowInteraction);
    });
  }

  setupIdleDetection() {
    // Only attach listeners once to avoid duplicates on repeated calls
    if (!this._idleListenersAttached) {
      this._idleListenersAttached = true;

      const resetIdleTimer = () => {
        if (this.isScreensaverActive) return;
        clearTimeout(this.idleTimer);
        this.idleTimer = setTimeout(() => {
          this.startScreensaver();
        }, this.config.idle_timeout_seconds * 1000);
      };

      const activityEvents = [
        'mousedown', 'mousemove', 'keypress',
        'scroll', 'touchstart', 'click'
      ];

      activityEvents.forEach(event => {
        document.addEventListener(event, resetIdleTimer, true);
      });

      // Detect interaction within the HA iframe -- clicking inside the
      // iframe causes the parent window to lose focus
      window.addEventListener('blur', resetIdleTimer);
      window.addEventListener('focus', resetIdleTimer);
    }

    // Start/restart the idle timer
    clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => {
      this.startScreensaver();
    }, this.config.idle_timeout_seconds * 1000);
  }

  startScreensaver() {
    if (this.photos.length === 0) {
      console.log('No photos available for slideshow');
      return;
    }

    console.log('Starting screensaver');
    this.isScreensaverActive = true;
    clearInterval(this.slideInterval);
    clearInterval(this.clockInterval);
    const slideshow = document.getElementById('slideshow');
    slideshow.classList.add('active');

    // Clear any existing slides but preserve overlay elements
    const clockElement = document.getElementById('screensaver-clock');
    const weatherElement = document.getElementById('weather-info');
    slideshow.innerHTML = '';
    if (clockElement) slideshow.appendChild(clockElement);
    if (weatherElement) slideshow.appendChild(weatherElement);

    // Pick a random starting slide
    const startIndex = Math.floor(Math.random() * this.photos.length);

    // Create slides and store EXIF data per index
    this.photoExif = {};
    this.photos.forEach((photo, index) => {
      const slide = document.createElement('div');
      slide.className = 'slide';
      if (index === startIndex) slide.classList.add('active');

      const img = document.createElement('img');
      img.src = photo.url;
      img.alt = `Photo ${index + 1}`;

      slide.appendChild(img);
      slideshow.appendChild(slide);
      this.photoExif[index] = photo.exif || {};
    });

    this.currentSlideIndex = startIndex;
    this.slideHistory = [];

    // Apply clock position and show initial photo info
    this.applyClockPosition();
    this.updatePhotoInfo(startIndex);

    // Load weather data
    this.loadWeather();

    // Start the clock
    this.startClock();

    // Change slide based on configured interval
    this.slideInterval = setInterval(() => {
      this.nextSlide();
    }, this.config.slide_interval_seconds * 1000);
  }

  nextSlide() {
    const slides = document.querySelectorAll('.slide');
    if (slides.length === 0) return;

    if (this.slideHistory.length >= 100) this.slideHistory.shift();
    this.slideHistory.push(this.currentSlideIndex);
    slides[this.currentSlideIndex].classList.remove('active');

    // Pick a random slide that's different from the current one
    let nextIndex;
    if (slides.length > 1) {
      do {
        nextIndex = Math.floor(Math.random() * slides.length);
      } while (nextIndex === this.currentSlideIndex);
    } else {
      nextIndex = 0;
    }

    this.currentSlideIndex = nextIndex;
    slides[this.currentSlideIndex].classList.add('active');

    this.updateClockColor(slides[this.currentSlideIndex]);
    this.updatePhotoInfo(this.currentSlideIndex);
  }

  previousSlide() {
    const slides = document.querySelectorAll('.slide');
    if (slides.length === 0 || this.slideHistory.length === 0) return;

    slides[this.currentSlideIndex].classList.remove('active');
    this.currentSlideIndex = this.slideHistory.pop();
    slides[this.currentSlideIndex].classList.add('active');

    this.updateClockColor(slides[this.currentSlideIndex]);
    this.updatePhotoInfo(this.currentSlideIndex);
  }

  resetSlideTimer() {
    clearInterval(this.slideInterval);
    this.slideInterval = setInterval(() => {
      this.nextSlide();
    }, this.config.slide_interval_seconds * 1000);
  }

  startClock() {
    const clockElement = document.getElementById('screensaver-clock');
    const timeElement = document.getElementById('clock-time');
    const dateElement = document.getElementById('clock-date');

    const updateTime = () => {
      const now = new Date();

      // Update time
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      timeElement.textContent = `${hours}:${minutes}`;

      // Update date - format: "Monday, January 1"
      const weekday = now.toLocaleDateString('en-US', { weekday: 'long' });
      const month = now.toLocaleDateString('en-US', { month: 'long' });
      const day = now.getDate();
      dateElement.textContent = `${weekday}, ${month} ${day}`;
    };

    updateTime();
    this.clockInterval = setInterval(updateTime, 1000);

    // Set initial clock color
    setTimeout(() => {
      const activeSlide = document.querySelector('.slide.active');
      if (activeSlide) {
        this.updateClockColor(activeSlide);
      }
    }, 100);
  }

  updateClockColor(slideElement) {
    const img = slideElement.querySelector('img');
    if (!img || !img.complete || img.naturalHeight === 0) {
      // Default to white if image not loaded or failed to load
      this.setClockColor(true);
      return;
    }

    // Create a canvas to sample the image
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    // Sample area at the bottom center where clock is positioned
    const sampleWidth = 400;
    const sampleHeight = 150;
    canvas.width = sampleWidth;
    canvas.height = sampleHeight;

    try {
      // Calculate the position to sample from the image
      const imgAspect = img.naturalWidth / img.naturalHeight;
      const containerAspect = window.innerWidth / window.innerHeight;

      let sourceX, sourceY, sourceWidth, sourceHeight;

      if (imgAspect > containerAspect) {
        // Image is wider - it will be letterboxed vertically
        sourceHeight = img.naturalHeight;
        sourceWidth = img.naturalHeight * containerAspect;
        sourceX = (img.naturalWidth - sourceWidth) / 2;
        sourceY = 0;
      } else {
        // Image is taller - it will be pillarboxed horizontally
        sourceWidth = img.naturalWidth;
        sourceHeight = img.naturalWidth / containerAspect;
        sourceX = 0;
        sourceY = (img.naturalHeight - sourceHeight) / 2;
      }

      // Sample from bottom center of the visible area
      const bottomCenterX = sourceX + sourceWidth / 2 - (sourceWidth * 0.2);
      const bottomCenterY = sourceY + sourceHeight - (sourceHeight * 0.15);
      const sampleSourceWidth = sourceWidth * 0.4;
      const sampleSourceHeight = sourceHeight * 0.15;

      ctx.drawImage(
        img,
        bottomCenterX,
        bottomCenterY,
        sampleSourceWidth,
        sampleSourceHeight,
        0,
        0,
        sampleWidth,
        sampleHeight
      );

      // Get image data
      const imageData = ctx.getImageData(0, 0, sampleWidth, sampleHeight);
      const data = imageData.data;

      // Calculate average brightness
      let totalBrightness = 0;
      const pixelCount = data.length / 4;

      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];

        // Calculate relative luminance
        const brightness = (0.299 * r + 0.587 * g + 0.114 * b);
        totalBrightness += brightness;
      }

      const avgBrightness = totalBrightness / pixelCount;

      // Use white text for dark backgrounds, black text for light backgrounds
      const useWhite = avgBrightness < 128;
      this.setClockColor(useWhite);

    } catch (error) {
      console.error('Error analyzing image:', error);
      // Default to white on error
      this.setClockColor(true);
    }
  }

  setClockColor(useWhite) {
    const clockElement = document.getElementById('screensaver-clock');
    if (useWhite) {
      clockElement.classList.remove('black');
      clockElement.classList.add('white');
    } else {
      clockElement.classList.remove('white');
      clockElement.classList.add('black');
    }
  }

  applyClockPosition() {
    const clock = document.getElementById('screensaver-clock');
    const pos = this.config.clock_position || 'bottom-center';
    // Remove any existing position class and apply new one
    clock.className = clock.className.replace(/\bpos-\S+/g, '').trim();
    clock.classList.add(`pos-${pos}`);
  }

  updatePhotoInfo(slideIndex) {
    const el = document.getElementById('photo-info');
    if (!el) return;
    const exif = this.photoExif[slideIndex] || {};
    const parts = [];
    if (exif.location) parts.push(`\uD83D\uDCCD ${exif.location}`);
    if (exif.date) parts.push(`\uD83D\uDCC5 ${exif.date}`);
    el.textContent = parts.join('   ');
  }

  async loadWeather() {
    if (!this.config.weather_entity) return;
    try {
      const response = await fetch('api/weather');
      if (!response.ok) return;
      this.weather = await response.json();
      this.updateWeatherDisplay();
    } catch (e) {
      console.error('Error loading weather:', e);
    }
  }

  updateWeatherDisplay() {
    const el = document.getElementById('weather-info');
    if (!el || !this.weather) { if (el) el.textContent = ''; return; }

    const icons = {
      'sunny': '\u2600\uFE0F', 'clear-night': '\uD83C\uDF19',
      'cloudy': '\u2601\uFE0F', 'partlycloudy': '\u26C5',
      'rainy': '\uD83C\uDF27\uFE0F', 'pouring': '\uD83C\uDF27\uFE0F',
      'snowy': '\uD83C\uDF28\uFE0F', 'snowy-rainy': '\uD83C\uDF28\uFE0F',
      'windy': '\uD83D\uDCA8', 'windy-variant': '\uD83D\uDCA8',
      'fog': '\uD83C\uDF2B\uFE0F', 'hail': '\uD83C\uDF28\uFE0F',
      'lightning': '\u26C8\uFE0F', 'lightning-rainy': '\u26C8\uFE0F',
      'exceptional': '\u26A0\uFE0F'
    };

    const icon = icons[this.weather.condition] || '';
    let temp = this.weather.temperature;
    if (temp !== null && temp !== undefined) {
      // Always display in Celsius
      if (this.weather.temperature_unit === '\u00b0F' || this.weather.temperature_unit === '°F') {
        temp = (temp - 32) * 5 / 9;
      }
      el.textContent = `${icon} ${Math.round(temp)}\u00b0C`;
    }
  }

  stopScreensaver() {
    console.log('Stopping screensaver');
    this.isScreensaverActive = false;

    const slideshow = document.getElementById('slideshow');
    slideshow.classList.remove('active');

    clearInterval(this.slideInterval);
    this.slideInterval = null;

    clearInterval(this.clockInterval);
    this.clockInterval = null;

    // Restart idle detection
    this.setupIdleDetection();
  }

  // ========== Google Photos Integration ==========

  async setupGooglePhotos() {
    // Check if Google Photos is enabled
    if (!this.config.google_photos_enabled && this.config.photos_source !== 'google_photos') {
      return;
    }

    // Show the Google Photos button
    const button = document.getElementById('google-photos-button');
    button.classList.add('visible');

    // Setup button click handler
    button.addEventListener('click', () => {
      this.showGooglePhotosModal();
    });

    // Check authentication status
    await this.checkGooglePhotosStatus();
  }

  async checkGooglePhotosStatus() {
    try {
      const response = await fetch('api/google-photos/status');
      const status = await response.json();

      if (status.authenticated && status.photos_count > 0) {
        // Update button to show photo count
        const button = document.getElementById('google-photos-button');
        button.textContent = `Google Photos (${status.photos_count})`;
      }
    } catch (error) {
      console.error('Error checking Google Photos status:', error);
    }
  }

  showGooglePhotosModal() {
    const modal = document.getElementById('google-photos-modal');
    modal.classList.add('active');

    // Load current status
    this.updateGooglePhotosModalContent();

    // Setup close on background click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        this.closeGooglePhotosModal();
      }
    });
  }

  closeGooglePhotosModal() {
    const modal = document.getElementById('google-photos-modal');
    modal.classList.remove('active');
  }

  async updateGooglePhotosModalContent() {
    const statusEl = document.getElementById('modal-status');
    const actionsEl = document.getElementById('modal-actions');

    // Show loading
    statusEl.innerHTML = '<div class="spinner"></div>';
    actionsEl.innerHTML = '';

    try {
      const response = await fetch('api/google-photos/status');
      const status = await response.json();

      if (status.error) {
        statusEl.innerHTML = `<div class="status-message error">${status.error}</div>`;
        actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
        return;
      }

      if (!status.authenticated) {
        // Not authenticated - show auth button
        statusEl.innerHTML = '<div class="status-message info">Connect your Google Photos account to use photos from your library.</div>';
        actionsEl.innerHTML = `
          <button class="modal-button primary" onclick="app.startGoogleAuth()">Connect Google Photos</button>
          <button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Cancel</button>
        `;
      } else if (status.photos_count === 0) {
        // Authenticated but no photos selected
        statusEl.innerHTML = '<div class="status-message info">Connected! Now select photos from your Google Photos library.</div>';
        actionsEl.innerHTML = `
          <button class="modal-button primary" onclick="app.openGooglePhotosPicker()">Select Photos</button>
          <button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Cancel</button>
        `;
      } else {
        // Has photos - show count and refresh option
        const lastUpdated = status.last_updated ? new Date(status.last_updated * 1000).toLocaleString() : 'Unknown';
        statusEl.innerHTML = `
          <div class="status-message success">
            ${status.photos_count} photos selected<br>
            <small>Last updated: ${lastUpdated}</small>
          </div>
        `;
        actionsEl.innerHTML = `
          <button class="modal-button primary" onclick="app.openGooglePhotosPicker()">Update Selection</button>
          <button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>
        `;
      }
    } catch (error) {
      statusEl.innerHTML = `<div class="status-message error">Error: ${error.message}</div>`;
      actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
    }
  }

  async startGoogleAuth() {
    const statusEl = document.getElementById('modal-status');
    const actionsEl = document.getElementById('modal-actions');

    statusEl.innerHTML = '<div class="spinner"></div><p style="text-align: center;">Opening Google authentication...</p>';
    actionsEl.innerHTML = '';

    try {
      const response = await fetch('api/google-photos/auth-url');
      const data = await response.json();

      if (data.error) {
        statusEl.innerHTML = `<div class="status-message error">${data.error}</div>`;
        actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
        return;
      }

      // Open auth URL in new window
      const authWindow = window.open(data.authorization_url, 'Google Photos Auth', 'width=600,height=700');

      statusEl.innerHTML = '<div class="status-message info">Please complete authentication in the popup window.</div>';
      actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Cancel</button>';

      // Poll for auth completion
      const checkAuth = setInterval(async () => {
        if (authWindow.closed) {
          clearInterval(checkAuth);
          // Recheck status
          await this.updateGooglePhotosModalContent();
          await this.checkGooglePhotosStatus();
        }
      }, 1000);
    } catch (error) {
      statusEl.innerHTML = `<div class="status-message error">Error: ${error.message}</div>`;
      actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
    }
  }

  async openGooglePhotosPicker() {
    const statusEl = document.getElementById('modal-status');
    const actionsEl = document.getElementById('modal-actions');

    statusEl.innerHTML = '<div class="spinner"></div><p style="text-align: center;">Creating picker session...</p>';
    actionsEl.innerHTML = '';

    try {
      // Create picker session
      const response = await fetch('api/google-photos/create-session', { method: 'POST' });
      const sessionData = await response.json();

      if (sessionData.error) {
        statusEl.innerHTML = `<div class="status-message error">${sessionData.error}</div>`;
        actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
        return;
      }

      const sessionId = sessionData.id;
      const pickerUri = sessionData.pickerUri;

      // Open picker in new window
      const pickerWindow = window.open(pickerUri, 'Google Photos Picker', 'width=800,height=900');

      statusEl.innerHTML = '<div class="status-message info">Select photos in the Google Photos picker window, then click Done.</div>';
      actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Cancel</button>';

      // Poll for session completion
      this.pollPickerSession(sessionId, pickerWindow);
    } catch (error) {
      statusEl.innerHTML = `<div class="status-message error">Error: ${error.message}</div>`;
      actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
    }
  }

  async pollPickerSession(sessionId, pickerWindow) {
    const statusEl = document.getElementById('modal-status');
    const actionsEl = document.getElementById('modal-actions');

    const pollInterval = setInterval(async () => {
      try {
        // Check if window is closed
        if (pickerWindow.closed) {
          statusEl.innerHTML = '<div class="status-message info">Checking for selected photos...</div>';
        }

        // Poll session status
        const response = await fetch(`api/google-photos/poll-session/${sessionId}`);
        const sessionData = await response.json();

        if (sessionData.error) {
          clearInterval(pollInterval);
          statusEl.innerHTML = `<div class="status-message error">${sessionData.error}</div>`;
          actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
          return;
        }

        // Check if photos have been selected
        if (sessionData.mediaItemsSet) {
          clearInterval(pollInterval);
          if (pickerWindow && !pickerWindow.closed) {
            pickerWindow.close();
          }

          // Fetch the selected photos
          statusEl.innerHTML = '<div class="spinner"></div><p style="text-align: center;">Fetching selected photos...</p>';

          const fetchResponse = await fetch(`api/google-photos/fetch-photos/${sessionId}`, { method: 'POST' });
          const fetchData = await fetchResponse.json();

          if (fetchData.error) {
            statusEl.innerHTML = `<div class="status-message error">${fetchData.error}</div>`;
            actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
            return;
          }

          // Success!
          statusEl.innerHTML = `<div class="status-message success">Successfully selected ${fetchData.count} photos!</div>`;
          actionsEl.innerHTML = '<button class="modal-button primary" onclick="app.closeGooglePhotosModal()">Done</button>';

          // Reload photos
          await this.loadPhotos();
          await this.checkGooglePhotosStatus();
        }
      } catch (error) {
        clearInterval(pollInterval);
        statusEl.innerHTML = `<div class="status-message error">Error: ${error.message}</div>`;
        actionsEl.innerHTML = '<button class="modal-button secondary" onclick="app.closeGooglePhotosModal()">Close</button>';
      }
    }, 2000); // Poll every 2 seconds
  }

}

// Initialize the app when DOM is ready
let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new ScreensaverApp();
});
