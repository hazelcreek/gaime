/**
 * Game state management hook and context provider
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { gameAPI, GameState, ActionResponse } from '../api/client';

interface NarrativeEntry {
  id: string;
  type: 'narrative' | 'player' | 'system' | 'error';
  content: string;
  timestamp: Date;
}

interface GameContextValue {
  // State
  sessionId: string | null;
  gameState: GameState | null;
  narrative: NarrativeEntry[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  startNewGame: (worldId?: string, playerName?: string) => Promise<void>;
  sendAction: (action: string) => Promise<void>;
  clearError: () => void;
}

const GameContext = createContext<GameContextValue | null>(null);

const STORAGE_KEY = 'gaime_session';

export function GameProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [narrative, setNarrative] = useState<NarrativeEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  // Start a new game
  const startNewGame = useCallback(async (worldId = 'cursed-manor', playerName = 'Traveler') => {
    setIsLoading(true);
    setError(null);
    setNarrative([]);
    
    try {
      const response = await gameAPI.newGame(worldId, playerName);
      setSessionId(response.session_id);
      setGameState(response.state);
      addNarrative('narrative', response.narrative);
      addNarrative('system', 'Type your commands below. Try "look around" or "help" to get started.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start game';
      setError(message);
      addNarrative('error', message);
    } finally {
      setIsLoading(false);
    }
  }, [addNarrative]);

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
      const response: ActionResponse = await gameAPI.sendAction(sessionId, action);
      setGameState(response.state);
      addNarrative('narrative', response.narrative);
      
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
  }, [sessionId, addNarrative]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return (
    <GameContext.Provider value={{
      sessionId,
      gameState,
      narrative,
      isLoading,
      error,
      startNewGame,
      sendAction,
      clearError,
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

