class ScreensaverApp {
    constructor() {
        this.config = null;
        this.photos = [];
        this.currentSlideIndex = 0;
        this.slideHistory = [];
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
        const slideshow = document.getElementById('slideshow');
        slideshow.classList.add('active');
        
        // Clear any existing slides
        slideshow.innerHTML = '';
        
        // Pick a random starting slide
        const startIndex = Math.floor(Math.random() * this.photos.length);

        // Create slides
        this.photos.forEach((photo, index) => {
            const slide = document.createElement('div');
            slide.className = 'slide';
            if (index === startIndex) slide.classList.add('active');

            const img = document.createElement('img');
            img.src = photo;
            img.alt = `Photo ${index + 1}`;

            slide.appendChild(img);
            slideshow.appendChild(slide);
        });

        this.currentSlideIndex = startIndex;
        this.slideHistory = [];

        // Change slide every 5 seconds
        this.slideInterval = setInterval(() => {
            this.nextSlide();
        }, 5000);
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
    }

    previousSlide() {
        const slides = document.querySelectorAll('.slide');
        if (slides.length === 0 || this.slideHistory.length === 0) return;

        slides[this.currentSlideIndex].classList.remove('active');
        this.currentSlideIndex = this.slideHistory.pop();
        slides[this.currentSlideIndex].classList.add('active');
    }

    resetSlideTimer() {
        clearInterval(this.slideInterval);
        this.slideInterval = setInterval(() => {
            this.nextSlide();
        }, 5000);
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
