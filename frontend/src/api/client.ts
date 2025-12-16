/**
 * API client for communicating with the GAIME backend
 */

const API_BASE = '/api';

export interface NarrativeExchange {
  turn: number;
  player_action: string;
  narrative_summary: string;
}

export interface NPCInteractionMemory {
  encounter_count: number;
  first_met_location: string | null;
  first_met_turn: number | null;
  topics_discussed: string[];
  player_disposition: string;
  npc_disposition: string;
  notable_moments: string[];
  last_interaction_turn: number;
}

export interface NarrativeMemory {
  recent_exchanges: NarrativeExchange[];
  npc_memory: Record<string, NPCInteractionMemory>;
  discoveries: string[];
}

export interface GameState {
  session_id: string;
  current_location: string;
  inventory: string[];
  discovered_locations: string[];
  flags: Record<string, boolean>;
  turn_count: number;
  narrative_memory: NarrativeMemory;
  npc_trust: Record<string, number>;
  status: string;
}

export interface LLMDebugInfo {
  system_prompt: string;
  user_prompt: string;
  raw_response: string;
  parsed_response: Record<string, unknown>;
  model: string;
  timestamp: string;
}

export interface ActionResponse {
  narrative: string;
  state: GameState;
  hints?: string[];
  llm_debug?: LLMDebugInfo;
}

export interface NewGameResponse {
  session_id: string;
  narrative: string;
  state: GameState;
  engine_version: string;
  llm_debug?: LLMDebugInfo;
}

export interface WorldInfo {
  id: string;
  name: string;
  theme: string;
  description?: string;
}

export interface EngineInfo {
  id: string;
  name: string;
  description: string;
}

export interface EnginesResponse {
  engines: EngineInfo[];
  default: string;
}

class GameAPIClient {
  /**
   * Start a new game session
   */
  async newGame(
    worldId: string = 'cursed-manor',
    debug: boolean = false,
    engine?: string
  ): Promise<NewGameResponse> {
    const body: Record<string, unknown> = { world_id: worldId, debug };
    if (engine) {
      body.engine = engine;
    }

    const response = await fetch(`${API_BASE}/game/new`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
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
  async sendAction(sessionId: string, action: string, debug: boolean = false): Promise<ActionResponse> {
    const response = await fetch(`${API_BASE}/game/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, action, debug }),
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

  /**
   * Get list of available menu music tracks
   */
  async getMenuTracks(): Promise<{ tracks: string[] }> {
    const response = await fetch(`${API_BASE}/audio/menu-tracks`);
    
    if (!response.ok) {
      // Return empty list on error - audio is non-critical
      return { tracks: [] };
    }
    
    return response.json();
  }

  /**
   * List available game engine versions
   * 
   * Engine selection is primarily for migration testing between
   * classic and two-phase engines.
   */
  async listEngines(): Promise<EnginesResponse> {
    const response = await fetch(`${API_BASE}/game/engines`);
    
    if (!response.ok) {
      // Return default engine on error
      return {
        engines: [{ id: 'classic', name: 'Classic Engine', description: 'Default engine' }],
        default: 'classic',
      };
    }
    
    return response.json();
  }
}

export const gameAPI = new GameAPIClient();
