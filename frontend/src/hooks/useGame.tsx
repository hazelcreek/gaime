/**
 * Game state management hook and context provider
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import {
  gameAPI,
  AnyGameState,
  DebugInfo,
  isTwoPhaseActionResponse,
  isTwoPhaseNewGameResponse,
} from '../api/client';

export interface NarrativeEntry {
  id: string;
  type: 'narrative' | 'player' | 'system' | 'error';
  content: string;
  timestamp: Date;
  debugInfo?: DebugInfo;
}

interface GameContextValue {
  // State
  sessionId: string | null;
  worldId: string | null;
  worldName: string | null;
  engineVersion: string | null;
  gameState: AnyGameState | null;
  narrative: NarrativeEntry[];
  isLoading: boolean;
  error: string | null;

  // Actions
  startNewGame: (worldId?: string, worldName?: string, engine?: string) => Promise<void>;
  sendAction: (action: string) => Promise<void>;
  clearError: () => void;
  resetGame: () => void;
}

const GameContext = createContext<GameContextValue | null>(null);

const STORAGE_KEY = 'gaime_session';

export function GameProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [worldId, setWorldId] = useState<string | null>(null);
  const [worldName, setWorldName] = useState<string | null>(null);
  const [engineVersion, setEngineVersion] = useState<string | null>(null);
  const [gameState, setGameState] = useState<AnyGameState | null>(null);
  const [narrative, setNarrative] = useState<NarrativeEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generate unique ID for narrative entries
  const generateId = () => Math.random().toString(36).substring(2, 9);

  // Add a narrative entry with optional debug info
  const addNarrative = useCallback((type: NarrativeEntry['type'], content: string, debugInfo?: DebugInfo) => {
    setNarrative(prev => [...prev, {
      id: generateId(),
      type,
      content,
      timestamp: new Date(),
      debugInfo,
    }]);
  }, []);

  // Load session from localStorage on mount and restore game state
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const {
          sessionId: storedId,
          worldId: storedWorldId,
          worldName: storedWorldName,
          engineVersion: storedEngineVersion,
        } = JSON.parse(stored);
        if (storedId) {
          // Try to restore game state from backend
          setIsLoading(true);
          gameAPI.getState(storedId)
            .then(({ state, engine }) => {
              // Session exists, restore state
              setSessionId(storedId);
              if (storedWorldId) {
                setWorldId(storedWorldId);
              }
              if (storedWorldName) {
                setWorldName(storedWorldName);
              }
              // Use engine from backend response, or fall back to stored version
              setEngineVersion(engine ?? storedEngineVersion ?? null);
              setGameState(state);
              addNarrative('system', 'Game restored. Continue your adventure!');
            })
            .catch(() => {
              // Session doesn't exist on backend, clear localStorage
              localStorage.removeItem(STORAGE_KEY);
            })
            .finally(() => {
              setIsLoading(false);
            });
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, [addNarrative]);

  // Save session to localStorage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        sessionId,
        worldId,
        worldName,
        engineVersion,
      }));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [sessionId, worldId, worldName, engineVersion]);

  // Start a new game - always request debug info
  const startNewGame = useCallback(async (
    selectedWorldId?: string,
    selectedWorldName?: string,
    engine?: string
  ) => {
    // Use provided worldId, or fall back to current world, or default to 'cursed-manor'
    const effectiveWorldId = selectedWorldId ?? worldId ?? 'cursed-manor';

    setIsLoading(true);
    setError(null);
    setNarrative([]);

    try {
      // Always request debug info (debug: true)
      const response = await gameAPI.newGame(effectiveWorldId, true, engine);
      setSessionId(response.session_id);
      setWorldId(effectiveWorldId);
      setWorldName(selectedWorldName ?? null);
      setEngineVersion(response.engine_version);
      setGameState(response.state);

      // Extract debug info based on engine type
      let debugInfo: DebugInfo | undefined;
      if (isTwoPhaseNewGameResponse(response)) {
        // Two-phase engine: use pipeline_debug
        debugInfo = response.pipeline_debug ?? undefined;
      } else {
        // Classic engine: use llm_debug
        debugInfo = response.llm_debug;
      }

      addNarrative('narrative', response.narrative, debugInfo);
      addNarrative('system', 'Type your commands below. Try "look around" or "help" to get started.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start game';
      setError(message);
      addNarrative('error', message);
    } finally {
      setIsLoading(false);
    }
  }, [addNarrative, worldId]);

  // Send a player action - always request debug info
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
      // Always request debug info (debug: true)
      const response = await gameAPI.sendAction(sessionId, action, true);
      setGameState(response.state);

      // Extract debug info based on engine type
      let debugInfo: DebugInfo | undefined;
      if (isTwoPhaseActionResponse(response)) {
        // Two-phase engine: use pipeline_debug
        debugInfo = response.pipeline_debug ?? undefined;
      } else {
        // Classic engine: use llm_debug
        debugInfo = response.llm_debug;
      }

      // Attach debug info to the narrative entry
      addNarrative('narrative', response.narrative, debugInfo);

      // Show hints if any (classic engine only)
      if (!isTwoPhaseActionResponse(response) && response.hints && response.hints.length > 0) {
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
  }, [sessionId, addNarrative]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Reset game and return to start screen
  const resetGame = useCallback(() => {
    setSessionId(null);
    setWorldId(null);
    setWorldName(null);
    setEngineVersion(null);
    setGameState(null);
    setNarrative([]);
    setError(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <GameContext.Provider value={{
      sessionId,
      worldId,
      worldName,
      engineVersion,
      gameState,
      narrative,
      isLoading,
      error,
      startNewGame,
      sendAction,
      clearError,
      resetGame,
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
