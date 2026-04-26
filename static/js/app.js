/**
 * ReadSteed RSVP Web Engine — v2
 * Features: Chunk-aware display, adaptive timing, word-skip with hold acceleration, PDF upload
 */

class RSVPReader {
    constructor() {
        this.chunks = [];           // Array of chunk objects from /api/tokenize
        this.currentIndex = 0;      // Current chunk index
        this.isPlaying = false;
        this.wpm = 300;
        this.timer = null;
        this.currentReadingId = null;

        // v2 feature flags
        this.smartPacingEnabled = true;
        this.chunkingEnabled = true;

        // Skip hold-acceleration state
        this._skipRAF = null;
        this._skipDirection = 0;
        this._skipStartTime = 0;
        this._skipLastFire = 0;
        this._keyHeld = null;

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

        this._loadToggles();
        this.init();
    }

    // --- Persist toggle states to localStorage ---
    _loadToggles() {
        const sp = localStorage.getItem('rs_smartPacing');
        const ch = localStorage.getItem('rs_chunking');
        if (sp !== null) this.smartPacingEnabled = sp === 'true';
        if (ch !== null) this.chunkingEnabled = ch === 'true';

        const spEl = document.getElementById('smart-pacing-toggle');
        const chEl = document.getElementById('chunking-toggle');
        if (spEl) spEl.checked = this.smartPacingEnabled;
        if (chEl) chEl.checked = this.chunkingEnabled;
    }

    _saveToggles() {
        localStorage.setItem('rs_smartPacing', this.smartPacingEnabled);
        localStorage.setItem('rs_chunking', this.chunkingEnabled);
    }

    init() {
        // --- Extension Integration ---
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('extension') === 'true') {
            document.body.classList.add('extension-mode');
        }

        window.addEventListener("message", (event) => {
            if (event.data && event.data.type === "RSVP_START_READER") {
                this.textInput.value = event.data.text;
                this.updateStats();
                this.startReader();
            }
        });

        this.wpmSlider.addEventListener('input', (e) => {
            this.wpm = parseInt(e.target.value);
            this.wpmValue.textContent = this.wpm;
        });

        this.playPauseBtn.addEventListener('click', () => this.togglePlay());
        document.getElementById('start-btn').addEventListener('click', () => this.startReader());
        document.getElementById('reset-btn').addEventListener('click', () => this.reset());
        document.getElementById('exit-reader-btn').addEventListener('click', () => this.exitReader());
        document.getElementById('new-reading-btn').addEventListener('click', () => this.newReading());

        // Skip buttons — single click + hold acceleration
        this._initSkipButton('skip-back-btn', -1);
        this._initSkipButton('skip-fwd-btn', 1);

        this.initFeatures();

        // Auth
        const showLoginBtn = document.getElementById('show-login-btn');
        if (showLoginBtn) showLoginBtn.addEventListener('click', () => this.showAuthModal(true));
        const closeBtn = document.getElementById('close-modal');
        if (closeBtn) closeBtn.addEventListener('click', () => this.showAuthModal(false));

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
        if (logoutBtn) logoutBtn.addEventListener('click', () => this.handleLogout());

        // Sidebar toggle & Overlay
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        if (window.innerWidth <= 768) sidebar.classList.add('closed');

        const toggleSidebar = () => {
            const isClosed = sidebar.classList.toggle('closed');
            if (overlay) overlay.classList.toggle('active', !isClosed);
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

    // ===================== SKIP HOLD-ACCELERATION =====================

    _initSkipButton(btnId, direction) {
        const btn = document.getElementById(btnId);
        if (!btn) return;

        const startHold = (e) => {
            e.preventDefault();
            btn.classList.add('pressing');
            this._startSkipRepeat(direction);
        };
        const stopHold = (e) => {
            e.preventDefault();
            btn.classList.remove('pressing');
            this._stopSkipRepeat();
        };

        btn.addEventListener('pointerdown', startHold);
        btn.addEventListener('pointerup', stopHold);
        btn.addEventListener('pointerleave', stopHold);
        btn.addEventListener('pointercancel', stopHold);
        // Prevent context menu on long press (mobile)
        btn.addEventListener('contextmenu', (e) => e.preventDefault());
    }

    _startSkipRepeat(direction) {
        this._stopSkipRepeat();
        this._skipDirection = direction;
        this._skipStartTime = performance.now();
        this._skipLastFire = this._skipStartTime;
        // Fire immediately on first press
        this._doSingleSkip(direction);
        this._skipRAF = requestAnimationFrame((t) => this._skipLoop(t));
    }

    _skipLoop(timestamp) {
        const elapsed = timestamp - this._skipStartTime;
        // Acceleration curve: start at ~150ms interval (≈7/sec), ramp to ~35ms (≈28/sec)
        const maxInterval = 150;
        const minInterval = 35;
        const rampDuration = 1200; // ms to reach full speed
        const progress = Math.min(elapsed / rampDuration, 1);
        const interval = maxInterval - (maxInterval - minInterval) * (progress * progress); // ease-in
        const sinceLast = timestamp - this._skipLastFire;

        if (sinceLast >= interval) {
            this._doSingleSkip(this._skipDirection);
            this._skipLastFire = timestamp;
        }

        this._skipRAF = requestAnimationFrame((t) => this._skipLoop(t));
    }

    _stopSkipRepeat() {
        if (this._skipRAF) {
            cancelAnimationFrame(this._skipRAF);
            this._skipRAF = null;
        }
        this._skipDirection = 0;
    }

    _doSingleSkip(direction) {
        if (!this.chunks.length) return;
        const newIndex = this.currentIndex + direction;
        // Clamp to valid range
        if (newIndex < 0 || newIndex >= this.chunks.length) return;
        this.currentIndex = newIndex;
        this.displayWord();
        this.updateProgress();
    }

    // ===================== FEATURES INIT =====================

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
        this.wpmSlider.addEventListener('input', (e) => {
            this.wpm = parseInt(e.target.value);
            this.wpmValue.textContent = this.wpm;
            this.updateStats();
        });

        // File Upload (txt + pdf)
        const fileUpload = document.getElementById('file-upload');
        if (fileUpload) {
            fileUpload.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (!file) return;

                if (file.name.toLowerCase().endsWith('.pdf')) {
                    this._handlePDFUpload(file);
                } else {
                    const reader = new FileReader();
                    reader.onload = (evt) => {
                        this.textInput.value = evt.target.result;
                        this.updateStats();
                    };
                    reader.readAsText(file);
                }
                e.target.value = '';
            });
        }

        // Toggle: Smart Pacing
        const spToggle = document.getElementById('smart-pacing-toggle');
        if (spToggle) {
            spToggle.addEventListener('change', (e) => {
                this.smartPacingEnabled = e.target.checked;
                this._saveToggles();
            });
        }

        // Toggle: Chunking — requires re-tokenization
        const chToggle = document.getElementById('chunking-toggle');
        if (chToggle) {
            chToggle.addEventListener('change', async (e) => {
                this.chunkingEnabled = e.target.checked;
                this._saveToggles();
                // Re-tokenize if we have text loaded
                if (this.textInput.value.trim() && !this.displayContainer.classList.contains('hidden')) {
                    const wasPlaying = this.isPlaying;
                    this.togglePlay(false);
                    await this._tokenize(this.textInput.value.trim());
                    this.currentIndex = Math.min(this.currentIndex, this.chunks.length - 1);
                    this.updateProgress();
                    this.displayWord();
                    if (wasPlaying) this.togglePlay(true);
                }
            });
        }

        // Settings (Color, Theme, Font)
        const bgColorInput = document.getElementById('bg-color-input');
        const textColorInput = document.getElementById('text-color-input');
        const themePreset = document.getElementById('theme-preset');
        const fontPreset = document.getElementById('font-preset');

        if (bgColorInput) bgColorInput.addEventListener('change', (e) => { 
            const val = e.target.value.trim();
            if (val) {
                document.documentElement.style.setProperty('--bg-dark', val);
                document.documentElement.style.setProperty('--bg-sidebar', val); // Apply to sidebar as well
            } else {
                document.documentElement.style.removeProperty('--bg-dark');
                document.documentElement.style.removeProperty('--bg-sidebar');
            }
        });
        
        if (textColorInput) textColorInput.addEventListener('change', (e) => { 
            const val = e.target.value.trim();
            if (val) {
                document.documentElement.style.setProperty('--text-primary', val);
                document.documentElement.style.setProperty('--text-secondary', val);
            } else {
                document.documentElement.style.removeProperty('--text-primary');
                document.documentElement.style.removeProperty('--text-secondary');
            }
        });
        
        if (themePreset) themePreset.addEventListener('change', (e) => {
            document.body.classList.remove('theme-dark', 'theme-light', 'theme-sepia');
            document.body.classList.add(`theme-${e.target.value}`);
            // Reset custom colors when preset changes
            if (bgColorInput) bgColorInput.value = '';
            if (textColorInput) textColorInput.value = '';
            document.documentElement.style.removeProperty('--bg-dark');
            document.documentElement.style.removeProperty('--bg-sidebar');
            document.documentElement.style.removeProperty('--text-primary');
            document.documentElement.style.removeProperty('--text-secondary');
        });
        
        if (fontPreset) fontPreset.addEventListener('change', (e) => { 
            document.body.style.fontFamily = e.target.value; 
            document.documentElement.style.setProperty('--font-custom', e.target.value);
        });

        // Focus Mode
        const focusToggleBtn = document.getElementById('focus-mode-toggle');
        if (focusToggleBtn) focusToggleBtn.addEventListener('click', () => this.toggleFocusMode());

        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement) {
                document.body.classList.remove('focus-mode-active');
                document.body.style.overflow = '';
            }
        });
        document.addEventListener('webkitfullscreenchange', () => {
            if (!document.webkitFullscreenElement) {
                document.body.classList.remove('focus-mode-active');
                document.body.style.overflow = '';
            }
        });

        // Tap-to-pause overlay
        const tapOverlay = document.getElementById('focus-tap-overlay');
        if (tapOverlay) tapOverlay.addEventListener('click', () => this.togglePlay());

        // Global Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {
            if (this.displayContainer.classList.contains('hidden')) return;
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
                    this.showHUD(`${this.wpm} WPM`);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.wpm = Math.max(100, this.wpm - 10);
                    this.wpmSlider.value = this.wpm;
                    this.wpmValue.textContent = this.wpm;
                    if (this.updateStats) this.updateStats();
                    this.showHUD(`${this.wpm} WPM`);
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    if (!this._keyHeld) {
                        this._keyHeld = 'ArrowLeft';
                        this._startSkipRepeat(-1);
                    }
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    if (!this._keyHeld) {
                        this._keyHeld = 'ArrowRight';
                        this._startSkipRepeat(1);
                    }
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

        document.addEventListener('keyup', (e) => {
            if (e.code === this._keyHeld) {
                this._stopSkipRepeat();
                this._keyHeld = null;
            }
        });
    }

    // ===================== PDF UPLOAD =====================

    async _handlePDFUpload(file) {
        this.showHUD('Parsing PDF…', 2000);
        try {
            const formData = new FormData();
            formData.append('file', file);
            const resp = await fetch('/api/parse-pdf', { method: 'POST', body: formData });
            const data = await resp.json();
            if (data.success) {
                this.textInput.value = data.text;
                this.updateStats();
                this.showHUD('PDF loaded ✓');
            } else {
                this.showHUD(data.message || 'PDF parsing failed', 2500);
            }
        } catch (e) {
            console.error('PDF upload error', e);
            this.showHUD('Failed to upload PDF', 2500);
        }
    }

    // ===================== TOKENIZATION =====================

    async _tokenize(text) {
        const resp = await fetch('/api/tokenize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text, chunking: this.chunkingEnabled })
        });
        this.chunks = await resp.json();
    }

    // ===================== READER LIFECYCLE =====================

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
            this.loadReadings();
            this.startReader(true);
        } catch (e) {
            console.error("Failed to load reading", e);
        }
    }

    async startReader(justShow = false) {
        const text = this.textInput.value.trim();
        if (!text) return;

        await this._tokenize(text);

        this.inputContainer.classList.add('hidden');
        this.displayContainer.classList.remove('hidden');

        if (this.currentIndex >= this.chunks.length) this.currentIndex = 0;
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
        
        // Notify extension to close overlay
        if (window.parent !== window) {
            window.parent.postMessage({ type: "RSVP_CLOSE_OVERLAY" }, "*");
        }
    }

    newReading() {
        this.exitReader();
        this.currentReadingId = null;
        this.textInput.value = '';
        this.currentIndex = 0;
        this.chunks = [];
    }

    togglePlay(forceValue) {
        this.isPlaying = forceValue !== undefined ? forceValue : !this.isPlaying;

        if (this.isPlaying && this.currentIndex >= this.chunks.length) {
            this.currentIndex = 0;
            this.updateProgress();
        }

        this.playPauseBtn.textContent = this.isPlaying ? 'Pause' : 'Play';
        if (forceValue === undefined) {
            this.showHUD(this.isPlaying ? '▶  Play' : '⏸  Pause');
        }

        if (this.isPlaying) {
            this.run();
        } else {
            clearTimeout(this.timer);
            this.autoSave();
        }
    }

    // ===================== RUN LOOP — ADAPTIVE TIMING =====================

    run() {
        if (!this.isPlaying || this.currentIndex >= this.chunks.length) {
            this.togglePlay(false);
            return;
        }

        const chunk = this.chunks[this.currentIndex];
        this.displayWord();

        this.currentIndex++;
        this.updateProgress();

        if (this.currentIndex % 25 === 0) this.autoSave();

        let delay;
        if (this.smartPacingEnabled) {
            // Adaptive: use pre-computed ms, scaled by WPM ratio (300 = baseline)
            delay = chunk.display_time_ms * (300 / this.wpm);
        } else {
            // Legacy constant timing with delay multiplier
            const baseDelay = (60 / this.wpm) * 1000;
            delay = baseDelay * (chunk.delay_multiplier || 1.0);
        }

        this.timer = setTimeout(() => this.run(), delay);
    }

    // ===================== DISPLAY =====================

    displayWord() {
        if (this.currentIndex >= this.chunks.length) {
            this.showPlaceholder("Finished");
            this.togglePlay(false);
            return;
        }

        const chunk = this.chunks[this.currentIndex];
        const display = chunk.display;

        // For multi-word chunks, find the longest word for ORP
        // For single words, use as-is
        let orpWord = display;
        if (chunk.words && chunk.words.length > 1) {
            orpWord = chunk.words.reduce((a, b) => a.length >= b.length ? a : b);
        }

        const orp = this.getORPIndex(orpWord);

        if (chunk.words && chunk.words.length > 1) {
            // Multi-word chunk: show entire text, highlight ORP of longest word
            // Find where the longest word starts in the display string
            const wordStart = display.indexOf(orpWord);
            const orpPos = wordStart + orp;
            this.prefixEl.textContent = display.substring(0, orpPos);
            this.focusEl.textContent = display[orpPos] || '';
            this.suffixEl.textContent = display.substring(orpPos + 1);
        } else {
            // Single word — standard ORP split
            this.prefixEl.textContent = display.substring(0, orp);
            this.focusEl.textContent = display[orp] || '';
            this.suffixEl.textContent = display.substring(orp + 1);
        }
    }

    showPlaceholder(text) {
        this.prefixEl.textContent = "";
        this.focusEl.textContent = text;
        this.suffixEl.textContent = "";
        this.focusEl.style.color = "var(--text-secondary)";
        setTimeout(() => { this.focusEl.style.color = "var(--focus-color)"; }, 1000);
    }

    // ===================== FOCUS MODE =====================

    toggleFocusMode() {
        const isActive = document.body.classList.contains('focus-mode-active');
        if (!isActive) {
            const elem = document.documentElement;
            if (elem.requestFullscreen) elem.requestFullscreen().catch(err => console.warn(err));
            else if (elem.webkitRequestFullscreen) elem.webkitRequestFullscreen();
            document.body.classList.add('focus-mode-active');
            document.body.style.overflow = 'hidden';
        } else {
            this.exitFocusMode();
        }
    }

    exitFocusMode() {
        if (document.exitFullscreen && document.fullscreenElement) document.exitFullscreen();
        else if (document.webkitExitFullscreen && document.webkitFullscreenElement) document.webkitExitFullscreen();
        document.body.classList.remove('focus-mode-active');
        document.body.style.overflow = '';
    }

    // ===================== HUD =====================

    showHUD(text, duration = 750) {
        const hud = document.getElementById('hud-toast');
        if (!hud) return;
        hud.textContent = text;
        hud.classList.add('visible');
        clearTimeout(this._hudTimer);
        this._hudTimer = setTimeout(() => hud.classList.remove('visible'), duration);
    }

    // ===================== HELPERS =====================

    getORPIndex(word) {
        const length = word.length;
        if (length <= 1) return 0;
        if (length <= 5) return 1;
        if (length <= 9) return 2;
        if (length <= 13) return 3;
        return 4;
    }

    _getTotalWords() {
        return this.chunks.reduce((sum, c) => sum + (c.word_count || 1), 0);
    }

    _getWordsUpTo(index) {
        let count = 0;
        for (let i = 0; i < index && i < this.chunks.length; i++) {
            count += (this.chunks[i].word_count || 1);
        }
        return count;
    }

    updateProgress() {
        const totalWords = this._getTotalWords();
        const wordsRead = this._getWordsUpTo(this.currentIndex);
        const percent = totalWords > 0 ? (wordsRead / totalWords) * 100 : 0;
        this.progressFill.style.width = `${percent}%`;
        this.progressText.textContent = `${wordsRead} / ${totalWords} words`;
    }

    async autoSave() {
        if (!this.chunks.length) return;
        const text = this.textInput.value;
        const title = this.chunks.slice(0, 4).map(c => c.display).join(' ') + '...';
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

    // ===================== AUTH =====================

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
        if (data.success) window.location.reload();
        else alert(data.message);
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
