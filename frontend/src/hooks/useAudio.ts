import { useState, useEffect, useCallback } from 'react';
import { audioManager } from '../audio/AudioManager';

/**
 * React hook for audio control.
 * Provides mute toggle and menu music controls.
 */
export function useAudio() {
  const [isMuted, setIsMuted] = useState(audioManager.getMuted());
  const [isReady, setIsReady] = useState(false);

  // Initialize audio manager on mount (async)
  useEffect(() => {
    let mounted = true;

    audioManager.init().then(() => {
      if (mounted) {
        // Sync state in case init loaded from localStorage
        setIsMuted(audioManager.getMuted());
        setIsReady(audioManager.isReady());
      }
    });

    return () => {
      mounted = false;
    };
  }, []);

  const toggleMute = useCallback(() => {
    const newMuted = audioManager.toggleMute();
    setIsMuted(newMuted);
  }, []);

  const playMenuMusic = useCallback(() => {
    audioManager.playMenuMusic();
  }, []);

  const stopMenuMusic = useCallback(() => {
    audioManager.stopMenuMusic();
  }, []);

  return {
    isMuted,
    isReady,
    toggleMute,
    playMenuMusic,
    stopMenuMusic,
  };
}
