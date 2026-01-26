class AudioManager {
    constructor() {
        this.bgm = new Audio();
        this.bgm.loop = true;
        this.se = new Audio();

        // Default volumes
        this.bgmVolume = 0.3;
        this.seVolume = 0.5;
        this.isMuted = false;

        // Load settings from localStorage
        this.loadSettings();

        // Bind volume to audio objects
        this.updateVolume();
    }

    loadSettings() {
        const savedBgmVol = localStorage.getItem('moon_bgm_volume');
        const savedSeVol = localStorage.getItem('moon_se_volume');
        const savedMute = localStorage.getItem('moon_is_muted');

        if (savedBgmVol !== null) this.bgmVolume = parseFloat(savedBgmVol);
        if (savedSeVol !== null) this.seVolume = parseFloat(savedSeVol);
        if (savedMute !== null) this.isMuted = (savedMute === 'true');
    }

    saveSettings() {
        localStorage.setItem('moon_bgm_volume', this.bgmVolume);
        localStorage.setItem('moon_se_volume', this.seVolume);
        localStorage.setItem('moon_is_muted', this.isMuted);
    }

    updateVolume() {
        this.bgm.volume = this.isMuted ? 0 : this.bgmVolume;
        this.se.volume = this.isMuted ? 0 : this.seVolume;
    }

    playBGM(filename) {
        // Don't restart if already playing the same file
        if (this.bgm.src.includes(filename) && !this.bgm.paused) return;

        // Add timestamp to prevent caching old empty files
        const timestamp = new Date().getTime();
        this.bgm.src = `/static/audio/bgm/${filename}?t=${timestamp}`;
        this.bgm.play().catch(e => console.log('BGM Play blocked (user interaction needed first):', e));
    }

    stopBGM() {
        this.bgm.pause();
    }

    playSE(filename) {
        // Create a new Audio instance for overlapping SE
        // Add timestamp to prevent caching old empty files
        const timestamp = new Date().getTime();
        const tempSe = new Audio(`/static/audio/se/${filename}?t=${timestamp}`);
        tempSe.volume = this.isMuted ? 0 : this.seVolume;
        tempSe.play().catch(e => console.log('SE Play blocked:', e));
    }

    setBGMVolume(val) {
        this.bgmVolume = Math.max(0, Math.min(1, val));
        this.updateVolume();
        this.saveSettings();
    }

    setSEVolume(val) {
        this.seVolume = Math.max(0, Math.min(1, val));
        this.updateVolume();
        this.saveSettings();
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        this.updateVolume();
        this.saveSettings();
        return this.isMuted;
    }
}

// Global instance
window.audioManager = new AudioManager();
