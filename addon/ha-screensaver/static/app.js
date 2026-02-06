class ScreensaverApp {
    constructor() {
        this.config = null;
        this.photos = [];
        this.currentSlideIndex = 0;
        this.slideHistory = [];
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
        const slideshow = document.getElementById('slideshow');
        slideshow.classList.add('active');
        
        // Clear any existing slides but preserve the clock
        const clockElement = document.getElementById('screensaver-clock');
        slideshow.innerHTML = '';
        if (clockElement) {
            slideshow.appendChild(clockElement);
        }
        
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
        
        // Update clock color based on new image
        this.updateClockColor(slides[this.currentSlideIndex]);
    }

    previousSlide() {
        const slides = document.querySelectorAll('.slide');
        if (slides.length === 0 || this.slideHistory.length === 0) return;

        slides[this.currentSlideIndex].classList.remove('active');
        this.currentSlideIndex = this.slideHistory.pop();
        slides[this.currentSlideIndex].classList.add('active');

        this.updateClockColor(slides[this.currentSlideIndex]);
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
        
        clearInterval(this.slideInterval);
        this.slideInterval = null;
        
        clearInterval(this.clockInterval);
        this.clockInterval = null;
        
        // Restart idle detection
        this.setupIdleDetection();
    }

}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ScreensaverApp();
});
