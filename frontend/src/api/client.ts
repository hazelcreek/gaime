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

// =============================================================================
// Two-Phase Engine Types
// =============================================================================

/**
 * Game state for the two-phase engine.
 * Different structure from classic GameState.
 */
export interface TwoPhaseGameState {
  session_id: string;
  current_location: string;
  inventory: string[];
  flags: Record<string, boolean>;
  visited_locations: string[];  // Backend sends set as list
  container_states: Record<string, boolean>;
  turn_count: number;
  status: string;
}

/**
 * Pipeline debug info for the two-phase engine.
 * Captures debug info at each stage: Parser -> Validator -> Narrator
 */
export interface TwoPhaseDebugInfo {
  raw_input: string;
  parser_type: string;  // "rule_based" or "interactor_ai"
  parsed_intent: Record<string, unknown> | null;
  interactor_debug: LLMDebugInfo | null;
  validation_result: Record<string, unknown> | null;
  events: Record<string, unknown>[];
  narrator_debug: LLMDebugInfo | null;
}

/**
 * Union type for debug info - can be classic or two-phase
 */
export type DebugInfo = LLMDebugInfo | TwoPhaseDebugInfo;

/**
 * Type guard to check if debug info is from two-phase engine
 */
export function isTwoPhaseDebugInfo(info: DebugInfo): info is TwoPhaseDebugInfo {
  return 'parser_type' in info && 'events' in info;
}

/**
 * Union type for game state - can be classic or two-phase
 */
export type AnyGameState = GameState | TwoPhaseGameState;

/**
 * Type guard to check if state is from two-phase engine
 */
export function isTwoPhaseGameState(state: AnyGameState): state is TwoPhaseGameState {
  return 'visited_locations' in state && !('narrative_memory' in state);
}

// =============================================================================
// Response Types
// =============================================================================

export interface ActionResponse {
  narrative: string;
  state: GameState;
  hints?: string[];
  llm_debug?: LLMDebugInfo;
}

/**
 * Response from two-phase engine action processing
 */
export interface TwoPhaseActionResponse {
  narrative: string;
  state: TwoPhaseGameState;
  events: Record<string, unknown>[];
  game_complete: boolean;
  ending_narrative?: string | null;
  pipeline_debug?: TwoPhaseDebugInfo | null;
}

/**
 * Union type for action responses
 */
export type AnyActionResponse = ActionResponse | TwoPhaseActionResponse;

/**
 * Type guard to check if response is from two-phase engine
 */
export function isTwoPhaseActionResponse(response: AnyActionResponse): response is TwoPhaseActionResponse {
  return 'pipeline_debug' in response || ('events' in response && Array.isArray(response.events));
}

export interface NewGameResponse {
  session_id: string;
  narrative: string;
  state: GameState;
  engine_version: string;
  llm_debug?: LLMDebugInfo;
}

/**
 * Response from starting a two-phase engine game
 */
export interface TwoPhaseNewGameResponse {
  session_id: string;
  narrative: string;
  state: TwoPhaseGameState;
  engine_version: string;
  pipeline_debug?: TwoPhaseDebugInfo | null;  // Uses two-phase debug info
}

/**
 * Union type for new game responses
 */
export type AnyNewGameResponse = NewGameResponse | TwoPhaseNewGameResponse;

/**
 * Type guard to check if new game response is from two-phase engine
 */
export function isTwoPhaseNewGameResponse(response: AnyNewGameResponse): response is TwoPhaseNewGameResponse {
  return 'pipeline_debug' in response || response.engine_version === 'two_phase';
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
   *
   * Returns different response types based on engine:
   * - classic: NewGameResponse with GameState
   * - two_phase: TwoPhaseNewGameResponse with TwoPhaseGameState
   */
  async newGame(
    worldId: string = 'cursed-manor',
    debug: boolean = false,
    engine?: string
  ): Promise<AnyNewGameResponse> {
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
   *
   * Returns different response types based on engine:
   * - classic: ActionResponse with llm_debug
   * - two_phase: TwoPhaseActionResponse with pipeline_debug
   */
  async sendAction(sessionId: string, action: string, debug: boolean = false): Promise<AnyActionResponse> {
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
   *
   * Returns state for either engine type.
   */
  async getState(sessionId: string): Promise<{ state: AnyGameState; engine?: string }> {
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
