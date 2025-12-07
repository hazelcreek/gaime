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
  player_name: string;
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
  llm_debug?: LLMDebugInfo;
}

export interface WorldInfo {
  id: string;
  name: string;
  theme: string;
  description?: string;
}

export interface ImageGenerationResult {
  location_id: string;
  success: boolean;
  image_url?: string;
  error?: string;
}

export interface GenerateImagesResponse {
  world_id: string;
  results: ImageGenerationResult[];
  message: string;
}

export interface WorldImagesInfo {
  world_id: string;
  images: Record<string, string>;
  count: number;
}

export interface VariantInfo {
  has_variants: boolean;
  location_id: string;
  base_image?: string;
  variants?: { npcs: string[]; image: string }[];
  conditional_npcs: string[];
  variant_count?: number;
  message?: string;
}

export interface GenerateVariantsResponse {
  success: boolean;
  location_id: string;
  base_image: string;
  variants: { npcs: string[]; image_url: string }[];
  manifest_path: string;
  images_generated: number;
  message: string;
}

class GameAPIClient {
  /**
   * Start a new game session
   */
  async newGame(worldId: string = 'cursed-manor', playerName: string = 'Traveler', debug: boolean = false): Promise<NewGameResponse> {
    const response = await fetch(`${API_BASE}/game/new`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ world_id: worldId, player_name: playerName, debug }),
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
   * Generate images for all or specific locations in a world
   */
  async generateImages(
    worldId: string, 
    locationIds?: string[]
  ): Promise<GenerateImagesResponse> {
    const response = await fetch(`${API_BASE}/builder/${worldId}/images/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ location_ids: locationIds || null }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate images');
    }
    
    return response.json();
  }

  /**
   * Generate or regenerate image for a single location
   */
  async generateSingleImage(worldId: string, locationId: string, model?: string): Promise<{
    success: boolean;
    location_id: string;
    image_url?: string;
    message: string;
  }> {
    const url = new URL(`${window.location.origin}${API_BASE}/builder/${worldId}/images/${locationId}/generate`);
    if (model) {
      url.searchParams.set('model', model);
    }
    
    const response = await fetch(url.toString(), { method: 'POST' });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate image');
    }
    
    return response.json();
  }

  /**
   * List all available images for a world
   */
  async listWorldImages(worldId: string): Promise<WorldImagesInfo> {
    const response = await fetch(`${API_BASE}/builder/${worldId}/images`);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to list images');
    }
    
    return response.json();
  }

  /**
   * Get the URL for a location image
   */
  getLocationImageUrl(worldId: string, locationId: string): string {
    return `${API_BASE}/builder/${worldId}/images/${locationId}`;
  }

  /**
   * Get variant information for a location
   */
  async getLocationVariantInfo(worldId: string, locationId: string): Promise<VariantInfo> {
    const response = await fetch(`${API_BASE}/builder/${worldId}/images/${locationId}/variants`);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get variant info');
    }
    
    return response.json();
  }

  /**
   * Generate image variants for a location with conditional NPCs
   */
  async generateLocationVariants(worldId: string, locationId: string): Promise<GenerateVariantsResponse> {
    const response = await fetch(`${API_BASE}/builder/${worldId}/images/${locationId}/generate-variants`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate variants');
    }
    
    return response.json();
  }
}

export const gameAPI = new GameAPIClient();

