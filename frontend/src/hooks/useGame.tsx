/**
 * Game state management hook and context provider
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { gameAPI, GameState, ActionResponse, LLMDebugInfo } from '../api/client';

interface NarrativeEntry {
  id: string;
  type: 'narrative' | 'player' | 'system' | 'error';
  content: string;
  timestamp: Date;
}

interface GameContextValue {
  // State
  sessionId: string | null;
  worldId: string | null;
  gameState: GameState | null;
  narrative: NarrativeEntry[];
  isLoading: boolean;
  error: string | null;
  debugMode: boolean;
  lastDebugInfo: LLMDebugInfo | null;
  
  // Actions
  startNewGame: (worldId?: string, playerName?: string) => Promise<void>;
  sendAction: (action: string) => Promise<void>;
  clearError: () => void;
  resetGame: () => void;
  setDebugMode: (enabled: boolean) => void;
}

const GameContext = createContext<GameContextValue | null>(null);

const STORAGE_KEY = 'gaime_session';
const DEBUG_MODE_KEY = 'gaime_debug_mode';

export function GameProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [worldId, setWorldId] = useState<string | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [narrative, setNarrative] = useState<NarrativeEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [debugMode, setDebugModeState] = useState<boolean>(() => {
    const stored = localStorage.getItem(DEBUG_MODE_KEY);
    return stored === 'true';
  });
  const [lastDebugInfo, setLastDebugInfo] = useState<LLMDebugInfo | null>(null);

  // Generate unique ID for narrative entries
  const generateId = () => Math.random().toString(36).substring(2, 9);

  // Add a narrative entry
  const addNarrative = useCallback((type: NarrativeEntry['type'], content: string) => {
    setNarrative(prev => [...prev, {
      id: generateId(),
      type,
      content,
      timestamp: new Date(),
    }]);
  }, []);

  // Load session from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const { sessionId: storedId } = JSON.parse(stored);
        // TODO: Validate session still exists on backend
        setSessionId(storedId);
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  // Save session to localStorage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessionId }));
    }
  }, [sessionId]);

  // Save debug mode preference
  const setDebugMode = useCallback((enabled: boolean) => {
    setDebugModeState(enabled);
    localStorage.setItem(DEBUG_MODE_KEY, enabled ? 'true' : 'false');
  }, []);

  // Start a new game
  const startNewGame = useCallback(async (selectedWorldId?: string, playerName?: string) => {
    // Use provided worldId, or fall back to current world, or default to 'cursed-manor'
    const effectiveWorldId = selectedWorldId ?? worldId ?? 'cursed-manor';
    const effectivePlayerName = playerName ?? gameState?.player_name ?? 'Traveler';
    
    setIsLoading(true);
    setError(null);
    setNarrative([]);
    setLastDebugInfo(null);
    
    try {
      const response = await gameAPI.newGame(effectiveWorldId, effectivePlayerName, debugMode);
      setSessionId(response.session_id);
      setWorldId(effectiveWorldId);
      setGameState(response.state);
      addNarrative('narrative', response.narrative);
      addNarrative('system', 'Type your commands below. Try "look around" or "help" to get started.');
      
      // Store debug info if present
      if (response.llm_debug) {
        setLastDebugInfo(response.llm_debug);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start game';
      setError(message);
      addNarrative('error', message);
    } finally {
      setIsLoading(false);
    }
  }, [addNarrative, worldId, gameState?.player_name, debugMode]);

  // Send a player action
  const sendAction = useCallback(async (action: string) => {
    if (!sessionId) {
      setError('No active game session');
      return;
    }

    // Add player input to narrative
    addNarrative('player', action);
    setIsLoading(true);
    setError(null);

    try {
      const response: ActionResponse = await gameAPI.sendAction(sessionId, action, debugMode);
      setGameState(response.state);
      addNarrative('narrative', response.narrative);
      
      // Store debug info if present
      if (response.llm_debug) {
        setLastDebugInfo(response.llm_debug);
      }
      
      // Show hints if any
      if (response.hints && response.hints.length > 0) {
        response.hints.forEach(hint => {
          addNarrative('system', `💡 ${hint}`);
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process action';
      setError(message);
      addNarrative('error', message);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, addNarrative, debugMode]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Reset game and return to start screen
  const resetGame = useCallback(() => {
    setSessionId(null);
    setWorldId(null);
    setGameState(null);
    setNarrative([]);
    setError(null);
    setLastDebugInfo(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <GameContext.Provider value={{
      sessionId,
      worldId,
      gameState,
      narrative,
      isLoading,
      error,
      debugMode,
      lastDebugInfo,
      startNewGame,
      sendAction,
      clearError,
      resetGame,
      setDebugMode,
    }}>
      {children}
    </GameContext.Provider>
  );
}

export function useGame() {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
}
