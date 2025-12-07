/**
 * StateOverlay - Modal overlay displaying current game state
 * Shows location, inventory, flags, discoveries, NPC trust, and narrative memory
 */

import { GameState } from '../api/client';

interface StateOverlayProps {
  gameState: GameState;
  onClose: () => void;
}

export default function StateOverlay({ gameState, onClose }: StateOverlayProps) {
  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div 
        className="bg-terminal-surface border border-terminal-border rounded-lg max-w-2xl w-full mx-4 
                   max-h-[85vh] overflow-hidden flex flex-col animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-terminal-border bg-terminal-bg/50">
          <div className="flex items-center gap-2">
            <span className="text-terminal-accent">◈</span>
            <h2 className="font-display text-terminal-accent tracking-wider">Game State</h2>
          </div>
          <button
            onClick={onClose}
            className="text-terminal-dim hover:text-terminal-text transition-colors text-lg leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Location & Turn */}
          <Section title="Current Status">
            <div className="grid grid-cols-2 gap-4">
              <InfoItem label="Location" value={formatLocationId(gameState.current_location)} />
              <InfoItem label="Turn" value={gameState.turn_count.toString()} />
            </div>
          </Section>

          {/* Inventory */}
          <Section title="Inventory">
            {gameState.inventory.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {gameState.inventory.map((item) => (
                  <span 
                    key={item}
                    className="px-2 py-1 bg-terminal-accent/10 border border-terminal-accent/30 
                             rounded text-terminal-accent text-xs"
                  >
                    {formatItemId(item)}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-terminal-dim text-sm italic">Empty</span>
            )}
          </Section>

          {/* Flags */}
          <Section title="Flags">
            {Object.keys(gameState.flags).length > 0 ? (
              <div className="space-y-1">
                {Object.entries(gameState.flags)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([flag, value]) => (
                    <div key={flag} className="flex items-center gap-2 text-sm">
                      <span className={value ? 'text-terminal-success' : 'text-terminal-dim'}>
                        {value ? '●' : '○'}
                      </span>
                      <span className="text-terminal-text">{flag}</span>
                    </div>
                  ))}
              </div>
            ) : (
              <span className="text-terminal-dim text-sm italic">No flags set</span>
            )}
          </Section>

          {/* Discovered Locations */}
          <Section title="Discovered Locations">
            {gameState.discovered_locations.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {gameState.discovered_locations.map((loc) => (
                  <span 
                    key={loc}
                    className={`px-2 py-1 rounded text-xs border ${
                      loc === gameState.current_location
                        ? 'bg-terminal-success/10 border-terminal-success/30 text-terminal-success'
                        : 'bg-terminal-bg border-terminal-border text-terminal-dim'
                    }`}
                  >
                    {formatLocationId(loc)}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-terminal-dim text-sm italic">None yet</span>
            )}
          </Section>

          {/* NPC Trust */}
          {gameState.npc_trust && Object.keys(gameState.npc_trust).length > 0 && (
            <Section title="NPC Trust">
              <div className="space-y-2">
                {Object.entries(gameState.npc_trust).map(([npc, trust]) => (
                  <div key={npc} className="flex items-center gap-3">
                    <span className="text-terminal-text text-sm min-w-[100px]">
                      {formatNpcId(npc)}
                    </span>
                    <div className="flex-1 h-2 bg-terminal-bg rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all ${getTrustColor(trust as number)}`}
                        style={{ width: `${Math.max(0, Math.min(100, ((trust as number) + 100) / 2))}%` }}
                      />
                    </div>
                    <span className="text-terminal-dim text-xs w-8 text-right">{trust}</span>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Narrative Memory Summary */}
          <Section title="Narrative Memory">
            <div className="space-y-3">
              {/* Recent Exchanges */}
              <div>
                <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-1">
                  Recent Exchanges ({gameState.narrative_memory.recent_exchanges.length})
                </h4>
                {gameState.narrative_memory.recent_exchanges.length > 0 ? (
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {gameState.narrative_memory.recent_exchanges.slice(-5).map((ex, i) => (
                      <div key={i} className="text-xs">
                        <span className="text-terminal-accent">Turn {ex.turn}:</span>{' '}
                        <span className="text-terminal-dim">{truncate(ex.player_action, 50)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-terminal-dim text-xs italic">None</span>
                )}
              </div>

              {/* Discoveries */}
              <div>
                <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-1">
                  Discoveries ({gameState.narrative_memory.discoveries.length})
                </h4>
                {gameState.narrative_memory.discoveries.length > 0 ? (
                  <div className="space-y-1 max-h-24 overflow-y-auto">
                    {gameState.narrative_memory.discoveries.map((d, i) => (
                      <div key={i} className="text-xs text-terminal-text">• {d}</div>
                    ))}
                  </div>
                ) : (
                  <span className="text-terminal-dim text-xs italic">None</span>
                )}
              </div>

              {/* NPC Interactions */}
              {Object.keys(gameState.narrative_memory.npc_memory).length > 0 && (
                <div>
                  <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-1">
                    NPC Interactions
                  </h4>
                  <div className="space-y-2">
                    {Object.entries(gameState.narrative_memory.npc_memory).map(([npcId, mem]) => (
                      <div key={npcId} className="text-xs bg-terminal-bg/50 p-2 rounded">
                        <div className="text-terminal-accent font-medium">{formatNpcId(npcId)}</div>
                        <div className="text-terminal-dim">
                          Met {mem.encounter_count}× at {formatLocationId(mem.first_met_location || 'unknown')}
                        </div>
                        {mem.topics_discussed.length > 0 && (
                          <div className="text-terminal-dim mt-1">
                            Topics: {mem.topics_discussed.slice(-3).join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Section>
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-terminal-border bg-terminal-bg/30 text-center">
          <span className="text-terminal-dim text-xs">
            Press Escape or click outside to close
          </span>
        </div>
      </div>
    </div>
  );
}

// Helper components
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-terminal-dim text-xs uppercase tracking-wider mb-2 border-b border-terminal-border/30 pb-1">
        {title}
      </h3>
      {children}
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-terminal-dim text-xs uppercase tracking-wider">{label}</div>
      <div className="text-terminal-text text-sm">{value}</div>
    </div>
  );
}

// Helper functions
function formatLocationId(id: string): string {
  return id.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function formatItemId(id: string): string {
  return id.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function formatNpcId(id: string): string {
  return id.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function truncate(str: string, len: number): string {
  return str.length > len ? str.slice(0, len) + '...' : str;
}

function getTrustColor(trust: number): string {
  if (trust >= 50) return 'bg-terminal-success';
  if (trust >= 0) return 'bg-terminal-accent';
  if (trust >= -50) return 'bg-terminal-warning';
  return 'bg-terminal-error';
}

