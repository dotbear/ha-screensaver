class ScreensaverApp {
    constructor() {
        this.config = null;
        this.photos = [];
        this.currentSlideIndex = 0;
        this.idleTimer = null;
        this.slideInterval = null;
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
            console.log('Config loaded:', this.config);
        } catch (error) {
            console.error('Error loading config:', error);
            this.config = {
                home_assistant_url: 'http://homeassistant.local:8123',
                photos_folder: './photos',
                idle_timeout_seconds: 60
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
        
        // Clear any existing slides
        slideshow.innerHTML = '';
        
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
        
        // Change slide every 5 seconds
        this.slideInterval = setInterval(() => {
            this.nextSlide();
        }, 5000);
    }

    nextSlide() {
        const slides = document.querySelectorAll('.slide');
        if (slides.length === 0) return;

        slides[this.currentSlideIndex].classList.remove('active');
        this.currentSlideIndex = (this.currentSlideIndex + 1) % slides.length;
        slides[this.currentSlideIndex].classList.add('active');
    }

    stopScreensaver() {
        console.log('Stopping screensaver');
        this.isScreensaverActive = false;
        
        const slideshow = document.getElementById('slideshow');
        slideshow.classList.remove('active');
        
        clearInterval(this.slideInterval);
        this.slideInterval = null;
        
        // Restart idle detection
        this.setupIdleDetection();
    }

    openSettings() {
        const modal = document.getElementById('settings-modal');
        const haUrl = document.getElementById('ha-url');
        const idleTimeout = document.getElementById('idle-timeout');
        const photosFolder = document.getElementById('photos-folder');

        haUrl.value = this.config.home_assistant_url;
        idleTimeout.value = this.config.idle_timeout_seconds;
        photosFolder.value = this.config.photos_folder;

        modal.classList.add('active');
    }

    async saveSettings() {
        const haUrl = document.getElementById('ha-url').value;
        const idleTimeout = parseInt(document.getElementById('idle-timeout').value);
        const photosFolder = document.getElementById('photos-folder').value;

        const newConfig = {
            home_assistant_url: haUrl,
            photos_folder: photosFolder,
            idle_timeout_seconds: idleTimeout
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
