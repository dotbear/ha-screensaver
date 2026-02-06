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

}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ScreensaverApp();
});
