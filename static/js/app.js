/**
 * ReadSteed RSVP Web Engine
 */

class RSVPReader {
    constructor() {
        this.words = [];
        this.currentIndex = 0;
        this.isPlaying = false;
        this.wpm = 300;
        this.timer = null;
        this.currentReadingId = null;

        // DOM Elements
        this.prefixEl = document.getElementById('prefix');
        this.focusEl = document.getElementById('focus');
        this.suffixEl = document.getElementById('suffix');
        this.progressFill = document.getElementById('progress-fill');
        this.progressText = document.getElementById('progress-text');
        this.wpmSlider = document.getElementById('wpm-slider');
        this.wpmValue = document.getElementById('wpm-value');
        this.playPauseBtn = document.getElementById('play-pause-btn');
        this.textInput = document.getElementById('text-input');
        this.inputContainer = document.getElementById('input-container');
        this.displayContainer = document.getElementById('display-container');

        this.init();
    }

    init() {
        this.wpmSlider.addEventListener('input', (e) => {
            this.wpm = parseInt(e.target.value);
            this.wpmValue.textContent = this.wpm;
        });

        this.playPauseBtn.addEventListener('click', () => this.togglePlay());
        document.getElementById('start-btn').addEventListener('click', () => this.startReader());
        document.getElementById('reset-btn').addEventListener('click', () => this.reset());
        document.getElementById('exit-reader-btn').addEventListener('click', () => this.exitReader());
        document.getElementById('new-reading-btn').addEventListener('click', () => this.newReading());
        
        this.initFeatures();

        // Auth
        const showLoginBtn = document.getElementById('show-login-btn');
        if (showLoginBtn) {
            showLoginBtn.addEventListener('click', () => this.showAuthModal(true));
        }
        
        const closeBtn = document.getElementById('close-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.showAuthModal(false));
        }

        document.getElementById('show-signup').addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('login-form').classList.add('hidden');
            document.getElementById('signup-form').classList.remove('hidden');
            document.getElementById('modal-title').textContent = 'Create Account';
        });

        document.getElementById('show-login').addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('signup-form').classList.add('hidden');
            document.getElementById('login-form').classList.remove('hidden');
            document.getElementById('modal-title').textContent = 'Welcome Back';
        });

        document.getElementById('do-login-btn').addEventListener('click', () => this.handleLogin());
        document.getElementById('do-signup-btn').addEventListener('click', () => this.handleSignup());
        
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // Sidebar toggle & Overlay
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        
        // Auto-close on mobile load
        if (window.innerWidth <= 768) {
            sidebar.classList.add('closed');
        }
        
        const toggleSidebar = () => {
            const isClosed = sidebar.classList.toggle('closed');
            if (overlay) {
                if (isClosed) {
                    overlay.classList.remove('active');
                } else {
                    overlay.classList.add('active');
                }
            }
        };

        document.getElementById('sidebar-toggle').addEventListener('click', toggleSidebar);
        if (overlay) {
            overlay.addEventListener('click', () => {
                sidebar.classList.add('closed');
                overlay.classList.remove('active');
            });
        }

        this.loadReadings();
    }

    initFeatures() {
        // Stats
        const textStats = document.getElementById('text-stats');
        this.updateStats = () => {
            const text = this.textInput.value.trim();
            const words = text ? text.split(/\s+/).length : 0;
            const mins = Math.ceil(words / this.wpm);
            if (textStats) textStats.textContent = `${words} words | ~${mins} min read`;
        };
        this.textInput.addEventListener('input', this.updateStats);
        
        // Ensure WPM slider update syncs stats
        this.wpmSlider.addEventListener('input', (e) => {
            this.wpm = parseInt(e.target.value);
            this.wpmValue.textContent = this.wpm;
            this.updateStats();
        });

        // File Upload
        const fileUpload = document.getElementById('file-upload');
        if (fileUpload) {
            fileUpload.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (evt) => {
                        this.textInput.value = evt.target.result;
                        this.updateStats();
                    };
                    reader.readAsText(file);
                }
                // Reset file input in case same file selected again
                e.target.value = '';
            });
        }

        // Settings (Color, Theme, Font)
        const bgColorInput = document.getElementById('bg-color-input');
        const textColorInput = document.getElementById('text-color-input');
        const themePreset = document.getElementById('theme-preset');
        const fontPreset = document.getElementById('font-preset');

        const validateColorName = (val) => /^[a-zA-Z]+$/.test(val);

        if (bgColorInput) {
            bgColorInput.addEventListener('change', (e) => {
                const val = e.target.value.trim();
                document.body.style.backgroundColor = val || '';
            });
        }

        if (textColorInput) {
            textColorInput.addEventListener('change', (e) => {
                const val = e.target.value.trim();
                document.body.style.color = val || '';
            });
        }

        if (themePreset) {
            themePreset.addEventListener('change', (e) => {
                document.body.classList.remove('theme-dark', 'theme-light', 'theme-sepia');
                document.body.classList.add(`theme-${e.target.value}`);
            });
        }

        if (fontPreset) {
            fontPreset.addEventListener('change', (e) => {
                document.body.style.fontFamily = e.target.value;
            });
        }

        // Focus Mode (Native Fullscreen API)
        const focusToggleBtn = document.getElementById('focus-mode-toggle');
        if (focusToggleBtn) {
            focusToggleBtn.addEventListener('click', () => {
                this.toggleFocusMode();
            });
        }
        
        // Handle native fullscreen exiting (e.g. user presses ESC or back gesture)
        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement) {
                document.body.classList.remove('focus-mode-active');
                document.body.style.overflow = ''; // Restore scroll
            }
        });
        document.addEventListener('webkitfullscreenchange', () => {
            if (!document.webkitFullscreenElement) {
                document.body.classList.remove('focus-mode-active');
                document.body.style.overflow = '';
            }
        });

        // Global Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {
            // Only trigger if we are actively in the reader display
            if (this.displayContainer.classList.contains('hidden')) return;
            
            // Ignore if user is typing in a text input (e.g. settings)
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

            switch(e.code) {
                case 'Space':
                    e.preventDefault();
                    this.togglePlay();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.wpm = Math.min(1000, this.wpm + 10);
                    this.wpmSlider.value = this.wpm;
                    this.wpmValue.textContent = this.wpm;
                    if (this.updateStats) this.updateStats();
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.wpm = Math.max(100, this.wpm - 10);
                    this.wpmSlider.value = this.wpm;
                    this.wpmValue.textContent = this.wpm;
                    if (this.updateStats) this.updateStats();
                    break;
                case 'Escape':
                    e.preventDefault();
                    if (document.fullscreenElement || document.webkitFullscreenElement) {
                        this.exitFocusMode();
                    } else {
                        this.exitReader();
                    }
                    break;
            }
        });
    }

    async loadReadings() {
        try {
            const resp = await fetch('/api/readings');
            const readings = await resp.json();
            const list = document.getElementById('readings-list');
            
            if (readings.length === 0) {
                list.innerHTML = '<p class="sidebar-info">No readings saved yet.</p>';
                return;
            }

            list.innerHTML = readings.map(r => `
                <div class="reading-item ${this.currentReadingId === r.id ? 'active' : ''}" onclick="app.loadReading(${r.id})">
                    <h3>${r.title}</h3>
                    <p>${new Date(r.date).toLocaleDateString()}</p>
                </div>
            `).join('');
        } catch (e) {
            console.error("Failed to load readings", e);
        }
    }

    async loadReading(id) {
        try {
            const resp = await fetch(`/api/readings/${id}`);
            const data = await resp.json();
            this.currentReadingId = id;
            this.textInput.value = data.text;
            this.currentIndex = data.index || 0;
            this.loadReadings(); // Update active state
            this.startReader(true); // Switch to display mode but don't play
        } catch (e) {
            console.error("Failed to load reading", e);
        }
    }

    async startReader(justShow = false) {
        const text = this.textInput.value.trim();
        if (!text) return;

        // Tokenize 
        const resp = await fetch('/api/tokenize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text})
        });
        this.words = await resp.json();

        this.inputContainer.classList.add('hidden');
        this.displayContainer.classList.remove('hidden');

        if (this.currentIndex >= this.words.length) this.currentIndex = 0;
        this.updateProgress();
        this.displayWord();

        if (!justShow) {
            this.currentIndex = 0;
            this.showPlaceholder("Ready");
            setTimeout(() => this.togglePlay(true), 1000);
        }

    }

    exitReader() {
        this.togglePlay(false);
        this.displayContainer.classList.add('hidden');
        this.inputContainer.classList.remove('hidden');
        this.autoSave();
    }

    newReading() {
        this.exitReader();
        this.currentReadingId = null;
        this.textInput.value = '';
        this.currentIndex = 0;
        this.words = [];
    }

    togglePlay(forceValue) {
        this.isPlaying = forceValue !== undefined ? forceValue : !this.isPlaying;

        // Auto-reset if playing but already at the end
        if (this.isPlaying && this.currentIndex >= this.words.length) {
            this.currentIndex = 0;
            this.updateProgress();
        }

        this.playPauseBtn.textContent = this.isPlaying ? 'Pause' : 'Play';
        
        if (this.isPlaying) {
            this.run();
        } else {
            clearTimeout(this.timer);
            this.autoSave();
        }
    }

    run() {
        if (!this.isPlaying || this.currentIndex >= this.words.length) {
            this.togglePlay(false);
            return;
        }

        const wordData = this.words[this.currentIndex];
        this.displayWord();
        
        this.currentIndex++;
        this.updateProgress();

        if (this.currentIndex % 25 === 0) this.autoSave();

        const baseDelay = (60 / this.wpm) * 1000;
        const delay = baseDelay * (wordData.delay_multiplier || 1.0);

        this.timer = setTimeout(() => this.run(), delay);
    }

    displayWord() {
        if (this.currentIndex >= this.words.length) {
            this.showPlaceholder("Finished");
            this.togglePlay(false);
            return;
        }

        const wordData = this.words[this.currentIndex];
        const word = wordData.word;
        const orp = this.getORPIndex(word);
        
        this.prefixEl.textContent = word.substring(0, orp);
        this.focusEl.textContent = word[orp];
        this.suffixEl.textContent = word.substring(orp + 1);
    }

    showPlaceholder(text) {
        this.prefixEl.textContent = "";
        this.focusEl.textContent = text;
        this.suffixEl.textContent = "";
        this.focusEl.style.color = "var(--text-secondary)";
        setTimeout(() => {
            this.focusEl.style.color = "var(--focus-color)";
        }, 1000);
    }

    // --- Focus Mode Logic ---
    toggleFocusMode() {
        const isActive = document.body.classList.contains('focus-mode-active');
        if (!isActive) {
            // Enter Fullscreen
            const elem = document.documentElement;
            if (elem.requestFullscreen) {
                elem.requestFullscreen().catch(err => console.warn(err));
            } else if (elem.webkitRequestFullscreen) { /* Safari */
                elem.webkitRequestFullscreen();
            }
            document.body.classList.add('focus-mode-active');
            document.body.style.overflow = 'hidden'; // Lock scroll completely
        } else {
            this.exitFocusMode();
        }
    }

    exitFocusMode() {
        if (document.exitFullscreen && document.fullscreenElement) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen && document.webkitFullscreenElement) {
            document.webkitExitFullscreen();
        }
        document.body.classList.remove('focus-mode-active');
        document.body.style.overflow = '';
    }


    getORPIndex(word) {
        const length = word.length;
        if (length <= 1) return 0;
        if (length <= 5) return 1;
        if (length <= 9) return 2;
        if (length <= 13) return 3;
        return 4;
    }

    updateProgress() {
        const total = this.words.length;
        const percent = total > 0 ? (this.currentIndex / total) * 100 : 0;
        this.progressFill.style.width = `${percent}%`;
        this.progressText.textContent = `${this.currentIndex} / ${total} words`;
    }

    async autoSave() {
        if (!this.words.length) return;
        
        const text = this.textInput.value;
        const title = this.words.slice(0, 4).map(w => w.word).join(' ') + '...';
        
        try {
            const resp = await fetch('/api/readings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id: this.currentReadingId,
                    text: text,
                    index: this.currentIndex,
                    title: title
                })
            });
            const data = await resp.json();
            if (data.success) {
                this.currentReadingId = data.id;
                this.loadReadings();
            }
        } catch (e) {
            console.error("Auto-save failed", e);
        }
    }

    // Modal & Auth
    showAuthModal(show) {
        const modal = document.getElementById('auth-modal');
        if (show) modal.classList.remove('hidden');
        else modal.classList.add('hidden');
    }

    async handleLogin() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password})
        });
        const data = await resp.json();
        if (data.success) {
            window.location.reload();
        } else {
            alert(data.message);
        }
    }

    async handleSignup() {
        const username = document.getElementById('signup-username').value;
        const email = document.getElementById('signup-email').value;
        const password = document.getElementById('signup-password').value;
        
        const resp = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, email, password})
        });
        const data = await resp.json();
        if (data.success) {
            alert("Account created! Please login.");
            document.getElementById('show-login').click();
        } else {
            alert(data.message);
        }
    }

    async handleLogout() {
        await fetch('/api/auth/logout', {method: 'POST'});
        window.location.reload();
    }

    reset() {
        this.togglePlay(false);
        this.currentIndex = 0;
        this.updateProgress();
        this.displayWord();
    }
}

// Global instance
const app = new RSVPReader();
window.app = app;
