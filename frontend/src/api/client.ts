/**
 * API client for communicating with the GAIME backend
 */

const API_BASE = '/api';

export interface LLMDebugInfo {
  system_prompt: string;
  user_prompt: string;
  raw_response: string;
  parsed_response: Record<string, unknown>;
  model: string;
  timestamp: string;
  // Performance metrics
  duration_ms?: number | null;
  tokens_input?: number | null;
  tokens_output?: number | null;
  tokens_total?: number | null;
}

// =============================================================================
// Game State Types
// =============================================================================

/**
 * Game state for the two-phase engine.
 */
export interface GameState {
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
export interface PipelineDebugInfo {
  raw_input: string;
  parser_type: string;  // "rule_based" or "interactor_ai"
  parsed_intent: Record<string, unknown> | null;
  interactor_debug: LLMDebugInfo | null;
  validation_result: Record<string, unknown> | null;
  events: Record<string, unknown>[];
  narrator_debug: LLMDebugInfo | null;
}

// =============================================================================
// Response Types
// =============================================================================

/**
 * Response from action processing
 */
export interface ActionResponse {
  narrative: string;
  state: GameState;
  events: Record<string, unknown>[];
  game_complete: boolean;
  ending_narrative?: string | null;
  pipeline_debug?: PipelineDebugInfo | null;
}

/**
 * Response from starting a new game
 */
export interface NewGameResponse {
  session_id: string;
  narrative: string;
  state: GameState;
  pipeline_debug?: PipelineDebugInfo | null;
}

export interface WorldInfo {
  id: string;
  name: string;
  theme: string;
  description?: string;
}

// =============================================================================
// Location Debug Snapshot Types
// =============================================================================
//
// These types mirror the backend models in:
//   backend/app/engine/two_phase/models/perception.py
//
// EXTENSIBILITY: When backend models are updated, these types must be updated
// to match. See docs/DEBUG_SNAPSHOT.md for the full pattern.
// =============================================================================

/**
 * Item at location with full visibility analysis.
 *
 * Source: backend/app/engine/two_phase/models/perception.py::LocationItemDebug
 */
export interface LocationItemDebug {
  /** The item's unique identifier */
  item_id: string;
  /** Display name from world definition */
  name: string;
  /** How item appears in scene (from Item.found_description) */
  found_description: string;
  /** Whether player can currently see this item */
  is_visible: boolean;
  /** Whether player has already taken this item */
  is_in_inventory: boolean;
  /** Why the item is visible/hidden: "visible", "hidden", "taken", "condition_not_met:{flag}" */
  visibility_reason: string;
  /** Where item is placed in location (from Location.item_placements) */
  placement: string | null;
  /** Whether item can be taken */
  portable: boolean;
  /** Full examination text */
  examine: string;
}

/**
 * NPC at location with full visibility analysis.
 *
 * Source: backend/app/engine/two_phase/models/perception.py::LocationNPCDebug
 */
export interface LocationNPCDebug {
  /** The NPC's unique identifier */
  npc_id: string;
  /** Display name from world definition */
  name: string;
  /** NPC's role/occupation */
  role: string;
  /** Physical description */
  appearance: string;
  /** Whether NPC is currently visible to player */
  is_visible: boolean;
  /** Why the NPC is visible/hidden: "visible", "condition_not_met:{flag}", "removed", "wrong_location:{loc}" */
  visibility_reason: string;
  /** Where NPC is positioned (from Location.npc_placements) */
  placement: string | null;
  /** NPC's current location (may differ from base due to triggers) */
  current_location: string | null;
}

/**
 * Exit with accessibility analysis.
 *
 * Source: backend/app/engine/two_phase/models/perception.py::LocationExitDebug
 */
export interface LocationExitDebug {
  /** The exit direction (north, south, etc.) */
  direction: string;
  /** ID of the destination location */
  destination_id: string;
  /** Display name of destination */
  destination_name: string;
  /** Whether player can currently use this exit */
  is_accessible: boolean;
  /** Why the exit is accessible/blocked: "accessible", "requires_flag:{x}", "requires_item:{y}" */
  access_reason: string;
  /** Exit description from location details */
  description: string | null;
}

/**
 * Interaction available at location.
 *
 * Source: backend/app/engine/two_phase/models/perception.py::LocationInteractionDebug
 */
export interface LocationInteractionDebug {
  /** The interaction's unique identifier */
  interaction_id: string;
  /** List of trigger words/phrases */
  triggers: string[];
  /** Flag that gets set when triggered */
  sets_flag: string | null;
  /** Exit that gets revealed */
  reveals_exit: string | null;
  /** Item given to player */
  gives_item: string | null;
  /** Item removed from player */
  removes_item: string | null;
}

/**
 * Full location state for debug view - shows everything with status.
 *
 * Unlike the player-facing state, this shows ALL entities at the location
 * with their visibility status flags, allowing developers to understand
 * exactly why things are visible or hidden.
 *
 * Source: backend/app/engine/two_phase/models/perception.py::LocationDebugSnapshot
 */
export interface LocationDebugSnapshot {
  /** Current location ID */
  location_id: string;
  /** Display name of location */
  name: string;
  /** Atmosphere description for the location */
  atmosphere: string;
  /** All exits with accessibility status */
  exits: LocationExitDebug[];
  /** All items with visibility status */
  items: LocationItemDebug[];
  /** All NPCs with visibility status */
  npcs: LocationNPCDebug[];
  /** Examinable scenery elements (key -> description) */
  details: Record<string, string>;
  /** Available interactions at this location */
  interactions: LocationInteractionDebug[];
  /** Access requirements for this location (if any) */
  requires: Record<string, string> | null;
}

/**
 * Extended state response including location debug info.
 */
export interface StateWithDebug {
  state: GameState;
  location_debug: LocationDebugSnapshot;
}

class GameAPIClient {
  /**
   * Start a new game session
   */
  async newGame(
    worldId: string = 'cursed-manor',
    debug: boolean = false
  ): Promise<NewGameResponse> {
    const body: Record<string, unknown> = { world_id: worldId, debug };

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
   * Get current game state with location debug information.
   *
   * Returns state plus full location details merged with game state visibility information.
   */
  async getState(sessionId: string): Promise<StateWithDebug> {
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
}

export const gameAPI = new GameAPIClient();
