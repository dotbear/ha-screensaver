class ScreensaverApp {
  constructor() {
    this.config = null;
    this.photos = [];
    this.currentSlideIndex = 0;
    this.slideHistory = [];
    this.photoExif = {};
    this.weather = null;
    this.media = null;
    this.idleTimer = null;
    this.slideInterval = null;
    this.clockInterval = null;
    this.weatherInterval = null;
    this.mediaInterval = null;
    this.lastIframeRefresh = Date.now();
    this.isScreensaverActive = false;
    this.isMediaMode = false;
    this.demoMode = new URLSearchParams(window.location.search).has('demo');

    this.init();
  }

  apiUrl(path) {
    return this.demoMode ? `api/demo/${path}` : `api/${path}`;
  }

  async init() {
    await this.loadConfig();
    await this.loadPhotos();
    this.setupEventListeners();
    this.setupMediaControls();
    this.setupIdleDetection();

    // Set the iframe source to Home Assistant URL
    const iframe = document.getElementById('ha-iframe');
    iframe.src = this.config.home_assistant_url;
  }

  async loadConfig() {
    try {
      const response = await fetch(this.apiUrl('config'));
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
      if (this.demoMode) {
        // In demo mode, use a placeholder image so the screensaver can start
        this.photos = [{
          url: 'https://picsum.photos/seed/demo/1920/1080',
          exif: { date: 'March 10, 2026', location: 'Copenhagen, Denmark' }
        }];
        console.log('Demo mode: using placeholder photo');
        return;
      }
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

  setupMediaControls() {
    document.getElementById('btn-play-pause').addEventListener('click', (e) => {
      e.stopPropagation();
      fetch('api/media/play_pause', { method: 'POST' });
      // Immediately poll for updated state
      setTimeout(() => this.loadMedia(), 500);
    });

    document.getElementById('btn-prev').addEventListener('click', (e) => {
      e.stopPropagation();
      fetch('api/media/previous', { method: 'POST' });
      setTimeout(() => this.loadMedia(), 500);
    });

    document.getElementById('btn-next').addEventListener('click', (e) => {
      e.stopPropagation();
      fetch('api/media/next', { method: 'POST' });
      setTimeout(() => this.loadMedia(), 500);
    });

    const volumeSlider = document.getElementById('volume-slider');
    volumeSlider.addEventListener('change', (e) => {
      e.stopPropagation();
      const volume = parseInt(e.target.value) / 100;
      fetch('api/media/volume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ volume_level: volume })
      });
    });

    // Prevent slideshow touch interactions on controls
    ['media-controls-transport', 'media-controls-volume'].forEach(id => {
      const el = document.getElementById(id);
      ['mousedown', 'touchstart'].forEach(evt => {
        el.addEventListener(evt, (e) => e.stopPropagation());
      });
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
    const preserveIds = [
      'screensaver-clock', 'photo-info', 'now-playing',
      'media-controls-transport', 'media-controls-volume', 'weather-info'
    ];
    const preserved = preserveIds.map(id => document.getElementById(id));
    slideshow.innerHTML = '';
    preserved.forEach(el => { if (el) slideshow.appendChild(el); });

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

    // Load weather data and refresh every 60 seconds
    this.loadWeather();
    clearInterval(this.weatherInterval);
    this.weatherInterval = setInterval(() => {
      this.loadWeather();
    }, 60000);

    // Poll media player state every 10 seconds
    this.isMediaMode = false;
    this.loadMedia();
    clearInterval(this.mediaInterval);
    this.mediaInterval = setInterval(() => {
      this.loadMedia();
    }, 10000);

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

      // Reload HA iframe hourly to prevent browser memory leaks
      if (now.getTime() - this.lastIframeRefresh >= 3600000) {
        const iframe = document.getElementById('ha-iframe');
        if (iframe) {
          console.log('Refreshing HA iframe to free memory');
          iframe.src = iframe.src;
        }
        this.lastIframeRefresh = now.getTime();
      }
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
    const dateEl = document.getElementById('photo-date');
    const locationEl = document.getElementById('photo-location');
    if (!dateEl || !locationEl) return;
    const exif = this.photoExif[slideIndex] || {};
    dateEl.textContent = exif.date ? `\uD83D\uDCC5 ${exif.date}` : '';
    locationEl.textContent = exif.location ? `\uD83D\uDCCD ${exif.location}` : '';
  }

  async loadWeather() {
    if (!this.config.weather_entity) return;
    try {
      const response = await fetch(this.apiUrl('weather'));
      if (!response.ok) return;
      this.weather = await response.json();
      this.updateWeatherDisplay();
    } catch (e) {
      console.error('Error loading weather:', e);
    }
  }

  updateWeatherDisplay() {
    const el = document.getElementById('weather-info');
    if (!el || !this.weather) { if (el) el.innerHTML = ''; return; }

    // SVG weather icons (Heroicons-style)
    const icons = {
      'sunny': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.25a.75.75 0 0 1 .75.75v2.25a.75.75 0 0 1-1.5 0V3a.75.75 0 0 1 .75-.75ZM7.5 12a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0ZM18.894 6.166a.75.75 0 0 0-1.06-1.06l-1.591 1.59a.75.75 0 1 0 1.06 1.061l1.591-1.59ZM21.75 12a.75.75 0 0 1-.75.75h-2.25a.75.75 0 0 1 0-1.5H21a.75.75 0 0 1 .75.75ZM17.834 18.894a.75.75 0 0 0 1.06-1.06l-1.59-1.591a.75.75 0 1 0-1.061 1.06l1.59 1.591ZM12 18a.75.75 0 0 1 .75.75V21a.75.75 0 0 1-1.5 0v-2.25A.75.75 0 0 1 12 18ZM7.758 17.303a.75.75 0 0 0-1.061-1.06l-1.591 1.59a.75.75 0 0 0 1.06 1.061l1.591-1.59ZM6 12a.75.75 0 0 1-.75.75H3a.75.75 0 0 1 0-1.5h2.25A.75.75 0 0 1 6 12ZM6.697 7.757a.75.75 0 0 0 1.06-1.06l-1.59-1.591a.75.75 0 0 0-1.061 1.06l1.59 1.591Z"/></svg>',
      'clear-night': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 0 1 .162.819A8.97 8.97 0 0 0 9 6a9 9 0 0 0 9 9 8.97 8.97 0 0 0 3.463-.69.75.75 0 0 1 .981.98 10.503 10.503 0 0 1-9.694 6.46c-5.799 0-10.5-4.7-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 0 1 .818.162Z" clip-rule="evenodd"/></svg>',
      'cloudy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 9.75a6 6 0 0 1 11.573-2.226 3.75 3.75 0 0 1 4.133 4.303A4.5 4.5 0 0 1 18 20.25H6.75a5.25 5.25 0 0 1-.75-10.449V9.75Z" clip-rule="evenodd"/></svg>',
      'partlycloudy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 9.75a6 6 0 0 1 11.573-2.226 3.75 3.75 0 0 1 4.133 4.303A4.5 4.5 0 0 1 18 20.25H6.75a5.25 5.25 0 0 1-.75-10.449V9.75ZM12 6a3.75 3.75 0 0 0-3.65 4.633.75.75 0 0 1-.583.86A3.75 3.75 0 0 0 6.75 18.75H18a3 3 0 0 0 .566-5.94.75.75 0 0 1-.578-.724 2.25 2.25 0 0 0-2.416-2.237.75.75 0 0 1-.707-.46A3.75 3.75 0 0 0 12 6Z" clip-rule="evenodd"/></svg>',
      'rainy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 9.75a6 6 0 0 1 11.573-2.226 3.75 3.75 0 0 1 4.133 4.303A4.5 4.5 0 0 1 18 20.25H6.75a5.25 5.25 0 0 1-.75-10.449V9.75Z" clip-rule="evenodd"/><path d="M8.25 17.25a.75.75 0 0 1 .75.75v2.25a.75.75 0 0 1-1.5 0V18a.75.75 0 0 1 .75-.75Zm4-1.5a.75.75 0 0 1 .75.75v2.25a.75.75 0 0 1-1.5 0v-2.25a.75.75 0 0 1 .75-.75Zm4 1.5a.75.75 0 0 1 .75.75v2.25a.75.75 0 0 1-1.5 0V18a.75.75 0 0 1 .75-.75Z"/></svg>',
      'pouring': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 9.75a6 6 0 0 1 11.573-2.226 3.75 3.75 0 0 1 4.133 4.303A4.5 4.5 0 0 1 18 20.25H6.75a5.25 5.25 0 0 1-.75-10.449V9.75Z" clip-rule="evenodd"/><path d="M7.5 17.25a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3a.75.75 0 0 1 .75-.75Zm3-1.5a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3a.75.75 0 0 1 .75-.75Zm3 1.5a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3a.75.75 0 0 1 .75-.75Zm3-1.5a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3a.75.75 0 0 1 .75-.75Z"/></svg>',
      'snowy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 9.75a6 6 0 0 1 11.573-2.226 3.75 3.75 0 0 1 4.133 4.303A4.5 4.5 0 0 1 18 20.25H6.75a5.25 5.25 0 0 1-.75-10.449V9.75Z" clip-rule="evenodd"/><circle cx="8.25" cy="18.75" r="1"/><circle cx="12" cy="17.25" r="1"/><circle cx="15.75" cy="18.75" r="1"/></svg>',
      'snowy-rainy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 9.75a6 6 0 0 1 11.573-2.226 3.75 3.75 0 0 1 4.133 4.303A4.5 4.5 0 0 1 18 20.25H6.75a5.25 5.25 0 0 1-.75-10.449V9.75Z" clip-rule="evenodd"/><circle cx="8.25" cy="18.75" r="1"/><circle cx="15.75" cy="18.75" r="1"/><path d="M12 17.25a.75.75 0 0 1 .75.75v2.25a.75.75 0 0 1-1.5 0V18a.75.75 0 0 1 .75-.75Z"/></svg>',
      'windy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>',
      'windy-variant': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>',
      'fog': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4.5 9.75a6 6 0 0 1 11.573-2.226 3.75 3.75 0 0 1 4.133 4.303A4.5 4.5 0 0 1 18 20.25H6.75"/><line x1="3" y1="20" x2="21" y2="20"/><line x1="3" y1="17" x2="21" y2="17"/></svg>',
      'hail': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 9.75a6 6 0 0 1 11.573-2.226 3.75 3.75 0 0 1 4.133 4.303A4.5 4.5 0 0 1 18 20.25H6.75a5.25 5.25 0 0 1-.75-10.449V9.75Z" clip-rule="evenodd"/><circle cx="8.25" cy="18.75" r="1.25"/><circle cx="12" cy="17.25" r="1.25"/><circle cx="15.75" cy="18.75" r="1.25"/></svg>',
      'lightning': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M14.615 1.595a.75.75 0 0 1 .359.852L12.982 9.75h7.268a.75.75 0 0 1 .548 1.262l-10.5 11.25a.75.75 0 0 1-1.272-.71l1.992-7.302H3.75a.75.75 0 0 1-.548-1.262l10.5-11.25a.75.75 0 0 1 .913-.143Z" clip-rule="evenodd"/></svg>',
      'lightning-rainy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M14.615 1.595a.75.75 0 0 1 .359.852L12.982 9.75h7.268a.75.75 0 0 1 .548 1.262l-10.5 11.25a.75.75 0 0 1-1.272-.71l1.992-7.302H3.75a.75.75 0 0 1-.548-1.262l10.5-11.25a.75.75 0 0 1 .913-.143Z" clip-rule="evenodd"/></svg>',
      'exceptional': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.499-2.599 4.499H4.645c-2.309 0-3.752-2.5-2.598-4.499L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clip-rule="evenodd"/></svg>'
    };

    const icon = icons[this.weather.condition] || '';
    let temp = this.weather.temperature;
    if (temp !== null && temp !== undefined) {
      // Always display in Celsius
      if (this.weather.temperature_unit === '\u00b0F' || this.weather.temperature_unit === '°F') {
        temp = (temp - 32) * 5 / 9;
      }
      el.innerHTML = `${icon}<span>${Math.round(temp)}\u00b0C</span>`;
    }
  }

  async loadMedia() {
    if (!this.config.media_player_entity) return;
    try {
      const response = await fetch(this.apiUrl('media'));
      if (!response.ok) return;
      this.media = await response.json();

      const isActive = this.media && (this.media.state === 'playing' || this.media.state === 'paused');
      const sourceAllowed = this.isSourceAllowed(this.media?.source);

      if (isActive && sourceAllowed) {
        this.enterMediaMode();
      } else if (this.isMediaMode) {
        this.exitMediaMode();
      }
    } catch (e) {
      console.error('Error loading media:', e);
    }
  }

  isSourceAllowed(source) {
    const filter = (this.config.media_player_sources || '').trim();
    if (!filter) return true; // empty = all sources allowed
    const allowed = filter.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
    return allowed.includes((source || '').toLowerCase());
  }

  enterMediaMode() {
    const np = document.getElementById('now-playing');
    const photoInfo = document.getElementById('photo-info');
    if (!np || !this.media) return;

    // Pause photo slideshow when entering media mode
    if (!this.isMediaMode) {
      clearInterval(this.slideInterval);
      this.slideInterval = null;
      this.isMediaMode = true;
    }

    // Update album art (only if URL changed)
    const art = document.getElementById('now-playing-art');
    const bg = document.getElementById('now-playing-bg');
    const newUrl = this.media.image_url || '';
    if (art && newUrl && art.src !== new URL(newUrl, window.location.href).href) {
      art.src = newUrl;
      bg.style.backgroundImage = `url(${newUrl})`;
    }

    // Update track info
    document.getElementById('now-playing-title').textContent = this.media.title || '';
    document.getElementById('now-playing-artist').textContent = this.media.artist || '';
    document.getElementById('now-playing-album').textContent = this.media.album || '';

    np.classList.add('active');
    if (photoInfo) photoInfo.style.display = 'none';

    // Push clock up to make room for volume slider
    const clock = document.getElementById('screensaver-clock');
    if (clock) clock.classList.add('media-active');

    // Show media controls
    const transport = document.getElementById('media-controls-transport');
    const volume = document.getElementById('media-controls-volume');
    if (transport) transport.classList.add('active');
    if (volume) volume.classList.add('active');

    // Update play/pause icon
    const iconPause = document.getElementById('icon-pause');
    const iconPlay = document.getElementById('icon-play');
    if (iconPause && iconPlay) {
      iconPause.style.display = this.media.state === 'playing' ? '' : 'none';
      iconPlay.style.display = this.media.state === 'playing' ? 'none' : '';
    }

    // Sync volume slider
    const slider = document.getElementById('volume-slider');
    if (slider && this.media.volume_level != null) {
      slider.value = Math.round(this.media.volume_level * 100);
    }

    // Force white clock text — album art backgrounds are typically dark after blur
    this.setClockColor(true);
  }

  exitMediaMode() {
    if (!this.isMediaMode) return;
    this.isMediaMode = false;

    const np = document.getElementById('now-playing');
    const photoInfo = document.getElementById('photo-info');
    const transport = document.getElementById('media-controls-transport');
    const volume = document.getElementById('media-controls-volume');
    if (np) np.classList.remove('active');
    if (photoInfo) photoInfo.style.display = '';
    if (transport) transport.classList.remove('active');
    if (volume) volume.classList.remove('active');

    // Restore clock position
    const clock = document.getElementById('screensaver-clock');
    if (clock) clock.classList.remove('media-active');

    // Resume photo slideshow
    if (this.isScreensaverActive && !this.slideInterval) {
      this.slideInterval = setInterval(() => {
        this.nextSlide();
      }, this.config.slide_interval_seconds * 1000);

      // Update clock color for current photo slide
      const activeSlide = document.querySelector('.slide.active');
      if (activeSlide) this.updateClockColor(activeSlide);
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

    clearInterval(this.weatherInterval);
    this.weatherInterval = null;

    clearInterval(this.mediaInterval);
    this.mediaInterval = null;
    this.exitMediaMode();

    // Restart idle detection
    this.setupIdleDetection();
  }

}

// Initialize the app when DOM is ready
let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new ScreensaverApp();
});
