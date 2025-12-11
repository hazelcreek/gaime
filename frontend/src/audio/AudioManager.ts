import { Howl } from 'howler';
import { gameAPI } from '../api/client';

// Extend Window to store AudioManager instance (survives HMR)
declare global {
  interface Window {
    __audioManager?: AudioManager;
  }
}

/**
 * Singleton class managing audio playback for GAIME.
 * Currently handles menu music only; will be extended for world music and SFX.
 * Instance is stored on window to survive Hot Module Reload.
 */
class AudioManager {
  private menuMusic: Howl | null = null;
  private menuTracks: string[] = [];
  private isMuted: boolean = true;
  private initialized: boolean = false;
  private initPromise: Promise<void> | null = null;
  private isStopping: boolean = false;

  private constructor() {
    // Private constructor for singleton
  }

  static getInstance(): AudioManager {
    // Use window to persist across HMR
    if (!window.__audioManager) {
      window.__audioManager = new AudioManager();
    }
    return window.__audioManager;
  }

  /**
   * Initialize audio manager and load preferences from localStorage.
   * Fetches available menu tracks from the backend.
   * Safe to call multiple times - will return same promise if already initializing.
   */
  async init(): Promise<void> {
    // If already initialized, return immediately
    if (this.initialized) return;
    
    // If currently initializing, return the existing promise
    if (this.initPromise) return this.initPromise;

    // Start initialization
    this.initPromise = this.doInit();
    return this.initPromise;
  }

  private async doInit(): Promise<void> {
    // Fetch available menu tracks from backend
    try {
      const response = await gameAPI.getMenuTracks();
      this.menuTracks = response.tracks;
    } catch (error) {
      console.warn('[Audio] Failed to fetch menu tracks:', error);
      this.menuTracks = [];
    }

    this.initialized = true;
  }

  /**
   * Create a new Howl instance with a random track from the menu tracks list.
   */
  private createMenuMusic(): void {
    if (this.menuTracks.length === 0) return;
    
    // Unload previous track if exists
    if (this.menuMusic) {
      this.menuMusic.unload();
    }
    
    const randomTrack = this.menuTracks[Math.floor(Math.random() * this.menuTracks.length)];
    this.menuMusic = new Howl({
      src: [randomTrack],
      loop: true,
      volume: this.isMuted ? 0 : 0.5,
      preload: true,
      onloaderror: (_id, error) => {
        console.error('[Audio] Failed to load track:', error);
      },
      onplayerror: (_id, error) => {
        console.error('[Audio] Failed to play track:', error);
      },
    });
  }

  /**
   * Start playing menu music with a random track.
   * Selects a new random track each time (unless already playing).
   */
  playMenuMusic(): void {
    if (this.menuTracks.length === 0) return;
    
    // If we're in the middle of a fade-out, cancel it and restore music
    if (this.isStopping && this.menuMusic) {
      this.isStopping = false;
      
      if (!this.isMuted) {
        // Fade back up to normal volume
        this.fadeVolume(0.5, 200);
      } else {
        // If muted, keep playing at volume 0, ready for unmute
        this.menuMusic.volume(0);
      }
      return;
    }
    
    // Reset stopping flag if we're starting to play
    this.isStopping = false;
    
    // If currently muted, defer playback until user unmutes to avoid clicks
    if (this.isMuted) {
      return;
    }

    // If already playing, don't interrupt
    if (this.menuMusic?.playing()) return;
    
    // Create a new track (random selection)
    this.createMenuMusic();
    
    if (this.menuMusic) {
      // Start from 0 and fade up to target for smooth start
      this.menuMusic.volume(0);
      this.menuMusic.play();
      this.fadeVolume(0.5, 200);
    }
  }

  /**
   * Stop menu music with a fade out for smooth transition.
   */
  stopMenuMusic(): void {
    if (!this.menuMusic) return;
    
    // Prevent multiple stop calls from interrupting the fade
    if (this.isStopping) return;
    this.isStopping = true;
    
    // Get current volume for fade
    const currentVolume = this.menuMusic.volume();
    
    // If volume is already 0 or very low, just stop immediately
    if (currentVolume < 0.01) {
      this.menuMusic.stop();
      this.isStopping = false;
      return;
    }
    
    // Fade out over 5 seconds
    this.menuMusic.fade(currentVolume, 0, 5000);
    
    // Use Howler's onfade event to stop cleanly after fade completes
    this.menuMusic.once('fade', () => {
      // Only stop if we're still in stopping mode
      // (playMenuMusic may have been called during the fade, cancelling the stop)
      if (!this.isStopping) return;
      
      if (this.menuMusic) {
        this.menuMusic.stop();
        // Restore volume for next play (if not muted)
        if (!this.isMuted) {
          this.menuMusic.volume(0.5);
        }
      }
      this.isStopping = false;
    });
  }

  /**
   * Toggle mute state and persist to localStorage.
   * @returns The new mute state
   */
  toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    
    // Apply to menu music
    if (!this.isMuted) {
      // Unmuting: ensure music is playing, even if previously deferred
      if (!this.menuMusic) {
        this.createMenuMusic();
      }

      if (this.menuMusic) {
        this.menuMusic.volume(0);
        this.menuMusic.play();
        this.fadeVolume(0.5, 200);
      }
    } else if (this.menuMusic) {
      // Muting: fade down smoothly
      this.fadeVolume(0, 150);
    }

    return this.isMuted;
  }

  /**
   * Smoothly adjust the current menu music volume. Falls back to an
   * immediate set if fade is not applicable (e.g., not playing).
   */
  private fadeVolume(targetVolume: number, durationMs: number): void {
    if (!this.menuMusic) return;

    const howl = this.menuMusic;
    const currentVolume = howl.volume();

    // If already at target, ensure it is set exactly and exit
    if (Math.abs(currentVolume - targetVolume) < 0.001) {
      howl.volume(targetVolume);
      return;
    }

    // If the track isn't playing, fade won't run—set immediately
    if (!howl.playing()) {
      howl.volume(targetVolume);
      return;
    }

    try {
      howl.fade(currentVolume, targetVolume, durationMs);
    } catch (error) {
      // If fade throws for any reason, fall back to direct set
      howl.volume(targetVolume);
    }
  }

  /**
   * Get current mute state.
   */
  getMuted(): boolean {
    return this.isMuted;
  }

  /**
   * Check if audio manager is ready to play.
   */
  isReady(): boolean {
    return this.initialized && this.menuTracks.length > 0;
  }
}

export const audioManager = AudioManager.getInstance();
