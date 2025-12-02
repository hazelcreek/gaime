/**
 * API client for communicating with the GAIME backend
 */

const API_BASE = '/api';

export interface GameState {
  session_id: string;
  player_name: string;
  current_location: string;
  inventory: string[];
  stats: {
    health: number;
    [key: string]: number;
  };
  discovered_locations: string[];
  flags: Record<string, boolean>;
  turn_count: number;
}

export interface ActionResponse {
  narrative: string;
  state: GameState;
  hints?: string[];
}

export interface NewGameResponse {
  session_id: string;
  narrative: string;
  state: GameState;
}

export interface WorldInfo {
  id: string;
  name: string;
  theme: string;
  description?: string;
}

class GameAPIClient {
  /**
   * Start a new game session
   */
  async newGame(worldId: string = 'cursed-manor', playerName: string = 'Traveler'): Promise<NewGameResponse> {
    const response = await fetch(`${API_BASE}/game/new`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ world_id: worldId, player_name: playerName }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start new game');
    }
    
    return response.json();
  }

  /**
   * Send a player action and get the narrative response
   */
  async sendAction(sessionId: string, action: string): Promise<ActionResponse> {
    const response = await fetch(`${API_BASE}/game/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, action }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to process action');
    }
    
    return response.json();
  }

  /**
   * Get current game state
   */
  async getState(sessionId: string): Promise<{ state: GameState }> {
    const response = await fetch(`${API_BASE}/game/state/${sessionId}`);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get game state');
    }
    
    return response.json();
  }

  /**
   * List available worlds
   */
  async listWorlds(): Promise<{ worlds: WorldInfo[] }> {
    const response = await fetch(`${API_BASE}/worlds`);
    
    if (!response.ok) {
      throw new Error('Failed to load worlds');
    }
    
    return response.json();
  }
}

export const gameAPI = new GameAPIClient();

