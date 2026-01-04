/**
 * StateOverlay - Modal overlay displaying current game state
 *
 * Includes the Location Debug section which shows the current location's
 * world definition merged with game state visibility information.
 */

import { useEffect } from 'react';
import {
  GameState,
  LocationDebugSnapshot,
  LocationItemDebug,
  LocationNPCDebug,
  LocationExitDebug,
  LocationInteractionDebug,
} from '../api/client';

interface StateOverlayProps {
  gameState: GameState;
  locationDebug: LocationDebugSnapshot | null;
  onClose: () => void;
  onFetchDebug: () => void;
}

export default function StateOverlay({
  gameState,
  locationDebug,
  onClose,
  onFetchDebug,
}: StateOverlayProps) {
  // Fetch location debug info when overlay opens
  useEffect(() => {
    onFetchDebug();
  }, [onFetchDebug]);

  const visitedLocations: string[] = Array.isArray(gameState.visited_locations)
    ? gameState.visited_locations
    : Array.from(gameState.visited_locations as Iterable<string>);

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
          {/* Location Debug - Merged world data with game state */}
          {locationDebug && (
            <LocationDebugSection locationDebug={locationDebug} />
          )}

          {/* Location & Turn */}
          <Section title="Player Status">
            <div className="grid grid-cols-2 gap-4">
              <InfoItem label="Location" value={formatLocationId(gameState.current_location)} />
              <InfoItem label="Turn" value={gameState.turn_count.toString()} />
              <InfoItem label="Status" value={gameState.status} />
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

          {/* Visited Locations */}
          <Section title="Visited Locations">
            {visitedLocations.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {visitedLocations.map((loc) => (
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

          {/* Container States */}
          <Section title="Container States">
            {Object.keys(gameState.container_states).length > 0 ? (
              <div className="space-y-1">
                {Object.entries(gameState.container_states)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([container, isOpen]) => (
                    <div key={container} className="flex items-center gap-2 text-sm">
                      <span className={isOpen ? 'text-terminal-success' : 'text-terminal-dim'}>
                        {isOpen ? '◑' : '◐'}
                      </span>
                      <span className="text-terminal-text">{formatItemId(container)}</span>
                      <span className="text-terminal-dim text-xs">
                        ({isOpen ? 'open' : 'closed'})
                      </span>
                    </div>
                  ))}
              </div>
            ) : (
              <span className="text-terminal-dim text-sm italic">No containers interacted with</span>
            )}
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

// =============================================================================
// Location Debug Section - Shows world data merged with game state
// =============================================================================

function LocationDebugSection({ locationDebug }: { locationDebug: LocationDebugSnapshot }) {
  return (
    <Section title={`Current Location: ${locationDebug.name}`}>
      <div className="space-y-4">
        {/* Atmosphere */}
        {locationDebug.atmosphere && (
          <div className="text-terminal-dim text-sm italic border-l-2 border-terminal-accent/30 pl-3">
            {locationDebug.atmosphere}
          </div>
        )}

        {/* Exits */}
        <div>
          <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-2">
            Exits ({locationDebug.exits.length})
          </h4>
          {locationDebug.exits.length > 0 ? (
            <div className="space-y-1">
              {locationDebug.exits.map((exit) => (
                <ExitRow key={exit.direction} exit={exit} />
              ))}
            </div>
          ) : (
            <span className="text-terminal-dim text-xs italic">No exits</span>
          )}
        </div>

        {/* Items */}
        <div>
          <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-2">
            Items ({locationDebug.items.length})
          </h4>
          {locationDebug.items.length > 0 ? (
            <div className="space-y-1">
              {locationDebug.items.map((item) => (
                <ItemRow key={item.item_id} item={item} />
              ))}
            </div>
          ) : (
            <span className="text-terminal-dim text-xs italic">No items at this location</span>
          )}
        </div>

        {/* NPCs */}
        <div>
          <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-2">
            NPCs ({locationDebug.npcs.length})
          </h4>
          {locationDebug.npcs.length > 0 ? (
            <div className="space-y-1">
              {locationDebug.npcs.map((npc) => (
                <NPCRow key={npc.npc_id} npc={npc} />
              ))}
            </div>
          ) : (
            <span className="text-terminal-dim text-xs italic">No NPCs at this location</span>
          )}
        </div>

        {/* Details (Scenery) */}
        {Object.keys(locationDebug.details).length > 0 && (
          <div>
            <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-2">
              Scenery Details ({Object.keys(locationDebug.details).length})
            </h4>
            <div className="space-y-1">
              {Object.entries(locationDebug.details).map(([key, description]) => (
                <div key={key} className="text-xs">
                  <span className="text-terminal-accent">{formatId(key)}:</span>{' '}
                  <span className="text-terminal-dim">{truncate(description, 60)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Interactions */}
        {locationDebug.interactions.length > 0 && (
          <div>
            <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-2">
              Interactions ({locationDebug.interactions.length})
            </h4>
            <div className="space-y-1">
              {locationDebug.interactions.map((interaction) => (
                <InteractionRow key={interaction.interaction_id} interaction={interaction} />
              ))}
            </div>
          </div>
        )}

        {/* Access Requirements */}
        {locationDebug.requires && Object.keys(locationDebug.requires).length > 0 && (
          <div>
            <h4 className="text-terminal-dim text-xs uppercase tracking-wider mb-2">
              Access Requirements
            </h4>
            <div className="space-y-1">
              {Object.entries(locationDebug.requires).map(([type, value]) => (
                <div key={type} className="text-xs">
                  <span className="text-terminal-warning">Requires {type}:</span>{' '}
                  <span className="text-terminal-text">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Section>
  );
}

function ExitRow({ exit }: { exit: LocationExitDebug }) {
  const isAccessible = exit.is_accessible;
  const statusColor = isAccessible ? 'text-terminal-success' : 'text-terminal-warning';
  const statusIcon = isAccessible ? '→' : '⊘';

  return (
    <div className="flex items-start gap-2 text-xs">
      <span className={statusColor}>{statusIcon}</span>
      <div className="flex-1">
        <span className="text-terminal-accent font-medium">{exit.direction.toUpperCase()}</span>
        <span className="text-terminal-dim"> → </span>
        <span className="text-terminal-text">{exit.destination_name}</span>
        {!isAccessible && (
          <span className="text-terminal-warning ml-2">({exit.access_reason})</span>
        )}
        {exit.description && (
          <div className="text-terminal-dim mt-0.5 italic">{truncate(exit.description, 50)}</div>
        )}
      </div>
    </div>
  );
}

function ItemRow({ item }: { item: LocationItemDebug }) {
  const statusColor = item.is_visible
    ? 'text-terminal-success'
    : item.is_in_inventory
    ? 'text-terminal-accent'
    : 'text-terminal-dim';
  const statusIcon = item.is_visible ? '◆' : item.is_in_inventory ? '✓' : '◇';

  return (
    <div className="flex items-start gap-2 text-xs">
      <span className={statusColor}>{statusIcon}</span>
      <div className="flex-1">
        <span className="text-terminal-text font-medium">{item.name}</span>
        {!item.portable && (
          <span className="text-terminal-dim ml-1">(fixed)</span>
        )}
        <span className={`ml-2 ${statusColor}`}>
          [{item.visibility_reason}]
        </span>
        {item.placement && (
          <div className="text-terminal-dim mt-0.5 italic">{item.placement}</div>
        )}
      </div>
    </div>
  );
}

function NPCRow({ npc }: { npc: LocationNPCDebug }) {
  const isVisible = npc.is_visible;
  const statusColor = isVisible ? 'text-terminal-success' : 'text-terminal-dim';
  const statusIcon = isVisible ? '◉' : '◌';

  return (
    <div className="flex items-start gap-2 text-xs">
      <span className={statusColor}>{statusIcon}</span>
      <div className="flex-1">
        <span className="text-terminal-text font-medium">{npc.name}</span>
        {npc.role && (
          <span className="text-terminal-dim ml-1">({npc.role})</span>
        )}
        <span className={`ml-2 ${statusColor}`}>
          [{npc.visibility_reason}]
        </span>
        {npc.placement && (
          <div className="text-terminal-dim mt-0.5 italic">{npc.placement}</div>
        )}
      </div>
    </div>
  );
}

function InteractionRow({ interaction }: { interaction: LocationInteractionDebug }) {
  return (
    <div className="text-xs bg-terminal-bg/50 p-2 rounded">
      <div className="flex items-center gap-2">
        <span className="text-terminal-accent font-medium">{formatId(interaction.interaction_id)}</span>
        {interaction.triggers.length > 0 && (
          <span className="text-terminal-dim">
            triggers: {interaction.triggers.slice(0, 3).join(', ')}
            {interaction.triggers.length > 3 && '...'}
          </span>
        )}
      </div>
      <div className="text-terminal-dim mt-1 space-x-3">
        {interaction.sets_flag && (
          <span>sets: <span className="text-terminal-warning">{interaction.sets_flag}</span></span>
        )}
        {interaction.reveals_exit && (
          <span>reveals: <span className="text-terminal-success">{interaction.reveals_exit}</span></span>
        )}
        {interaction.gives_item && (
          <span>gives: <span className="text-terminal-accent">{interaction.gives_item}</span></span>
        )}
        {interaction.removes_item && (
          <span>removes: <span className="text-terminal-error">{interaction.removes_item}</span></span>
        )}
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

function formatId(id: string): string {
  return id.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function truncate(str: string, len: number): string {
  return str.length > len ? str.slice(0, len) + '...' : str;
}
