class ScreensaverApp {
    constructor() {
        this.config = null;
        this.photos = [];
        this.currentSlideIndex = 0;
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
        
        // Set the iframe source to Home Assistant URL
        const iframe = document.getElementById('ha-iframe');
        iframe.src = this.config.home_assistant_url;
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
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
            const response = await fetch('/api/photos');
            this.photos = await response.json();
            console.log('Photos loaded:', this.photos.length);
        } catch (error) {
            console.error('Error loading photos:', error);
            this.photos = [];
        }
    }

    setupEventListeners() {
        const settingsButton = document.getElementById('settings-button');
        const settingsModal = document.getElementById('settings-modal');
        const saveButton = document.getElementById('save-settings');
        const cancelButton = document.getElementById('cancel-settings');

        settingsButton.addEventListener('click', () => {
            this.openSettings();
        });

        saveButton.addEventListener('click', () => {
            this.saveSettings();
        });

        cancelButton.addEventListener('click', () => {
            settingsModal.classList.remove('active');
        });

        // Click on modal background to close
        settingsModal.addEventListener('click', (e) => {
            if (e.target === settingsModal) {
                settingsModal.classList.remove('active');
            }
        });

        // Activity detection to exit slideshow
        const activityEvents = ['mousedown', 'touchstart', 'click'];
        activityEvents.forEach(event => {
            document.getElementById('slideshow').addEventListener(event, (e) => {
                if (this.isScreensaverActive) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.stopScreensaver();
                }
            });
        });
    }

    setupIdleDetection() {
        const resetIdleTimer = () => {
            // Don't reset timer if screensaver is active
            if (this.isScreensaverActive) return;
            
            clearTimeout(this.idleTimer);
            this.idleTimer = setTimeout(() => {
                this.startScreensaver();
            }, this.config.idle_timeout_seconds * 1000);
        };

        // Events that indicate user activity
        const activityEvents = [
            'mousedown', 'mousemove', 'keypress', 
            'scroll', 'touchstart', 'click'
        ];

        activityEvents.forEach(event => {
            document.addEventListener(event, resetIdleTimer, true);
        });

        // Start the initial timer
        resetIdleTimer();
    }

    startScreensaver() {
        if (this.photos.length === 0) {
            console.log('No photos available for slideshow');
            return;
        }

        console.log('Starting screensaver');
        this.isScreensaverActive = true;
        const slideshow = document.getElementById('slideshow');
        slideshow.classList.add('active');
        
        // Hide settings button when slideshow is active
        const settingsButton = document.getElementById('settings-button');
        settingsButton.style.display = 'none';
        
        // Clear any existing slides but preserve the clock
        const clockElement = document.getElementById('screensaver-clock');
        slideshow.innerHTML = '';
        if (clockElement) {
            slideshow.appendChild(clockElement);
        }
        
        // Create slides
        this.photos.forEach((photo, index) => {
            const slide = document.createElement('div');
            slide.className = 'slide';
            if (index === 0) slide.classList.add('active');
            
            const img = document.createElement('img');
            img.src = photo;
            img.alt = `Photo ${index + 1}`;
            
            slide.appendChild(img);
            slideshow.appendChild(slide);
        });

        this.currentSlideIndex = 0;
        
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
        
        // Update clock color based on new image
        this.updateClockColor(slides[this.currentSlideIndex]);
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
        if (!img || !img.complete) {
            // Default to white if image not loaded
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

    stopScreensaver() {
        console.log('Stopping screensaver');
        this.isScreensaverActive = false;
        
        const slideshow = document.getElementById('slideshow');
        slideshow.classList.remove('active');
        
        // Show settings button when slideshow stops
        const settingsButton = document.getElementById('settings-button');
        settingsButton.style.display = 'block';
        
        clearInterval(this.slideInterval);
        this.slideInterval = null;
        
        clearInterval(this.clockInterval);
        this.clockInterval = null;
        
        // Restart idle detection
        this.setupIdleDetection();
    }

    openSettings() {
        const modal = document.getElementById('settings-modal');
        const haUrl = document.getElementById('ha-url');
        const idleTimeout = document.getElementById('idle-timeout');
        const slideInterval = document.getElementById('slide-interval');
        const photosFolder = document.getElementById('photos-folder');

        haUrl.value = this.config.home_assistant_url;
        idleTimeout.value = this.config.idle_timeout_seconds;
        slideInterval.value = this.config.slide_interval_seconds;
        photosFolder.value = this.config.photos_folder;

        modal.classList.add('active');
    }

    async saveSettings() {
        const haUrl = document.getElementById('ha-url').value;
        const idleTimeout = parseInt(document.getElementById('idle-timeout').value);
        const slideInterval = parseInt(document.getElementById('slide-interval').value);
        const photosFolder = document.getElementById('photos-folder').value;

        const newConfig = {
            home_assistant_url: haUrl,
            photos_folder: photosFolder,
            idle_timeout_seconds: idleTimeout,
            slide_interval_seconds: slideInterval
        };

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newConfig)
            });

            if (response.ok) {
                this.config = await response.json();
                
                // Ensure slide interval is present
                if (!this.config.slide_interval_seconds) {
                    this.config.slide_interval_seconds = slideInterval;
                }
                
                // Reload iframe to apply new config
                const iframe = document.getElementById('ha-iframe');
                iframe.src = this.config.home_assistant_url;
                
                // Reload photos
                await this.loadPhotos();
                
                // Close modal
                document.getElementById('settings-modal').classList.remove('active');
                
                // Restart idle detection with new timeout
                this.setupIdleDetection();
                
                console.log('Settings saved successfully');
            } else {
                console.error('Error saving settings');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
        }
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ScreensaverApp();
});
