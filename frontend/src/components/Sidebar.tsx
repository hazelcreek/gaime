/**
 * Sidebar - Displays player stats, inventory, and location info
 */

import { useGame } from '../hooks/useGame';

export default function Sidebar() {
  const { gameState, sessionId, startNewGame, isLoading } = useGame();

  if (!sessionId) {
    return null;
  }

  return (
    <aside className="w-64 flex-shrink-0 space-y-4 sticky top-4 self-start max-h-[calc(100vh-2rem)] overflow-y-auto">
      {/* Location */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
        <h3 className="text-terminal-dim text-xs uppercase tracking-wider mb-2">Location</h3>
        <p className="text-terminal-accent font-display">
          {gameState?.current_location ? formatLocationName(gameState.current_location) : 'Unknown'}
        </p>
      </div>

      {/* Stats */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
        <h3 className="text-terminal-dim text-xs uppercase tracking-wider mb-3">Status</h3>
        <div className="space-y-2">
          <StatBar 
            label="Health" 
            value={gameState?.stats?.health ?? 100} 
            max={100} 
            color="terminal-success" 
          />
        </div>
      </div>

      {/* Inventory */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
        <h3 className="text-terminal-dim text-xs uppercase tracking-wider mb-2">Inventory</h3>
        {gameState?.inventory && gameState.inventory.length > 0 ? (
          <ul className="space-y-1">
            {gameState.inventory.map((item, idx) => (
              <li key={idx} className="text-terminal-text text-sm flex items-center gap-2">
                <span className="text-terminal-warning">•</span>
                {formatItemName(item)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-terminal-dim text-sm italic">Empty</p>
        )}
      </div>

      {/* Turn counter */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
        <div className="flex justify-between text-sm">
          <span className="text-terminal-dim">Turn</span>
          <span className="text-terminal-text">{gameState?.turn_count ?? 0}</span>
        </div>
      </div>

      {/* New Game button */}
      <button
        onClick={() => startNewGame()}
        disabled={isLoading}
        className="w-full px-4 py-2 text-sm text-terminal-dim hover:text-terminal-error 
                   border border-terminal-border rounded-lg hover:border-terminal-error/50
                   transition-colors disabled:opacity-50"
      >
        Start New Game
      </button>
    </aside>
  );
}

function StatBar({ 
  label, 
  value, 
  max, 
  color 
}: { 
  label: string; 
  value: number; 
  max: number; 
  color: string;
}) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-terminal-dim">{label}</span>
        <span className="text-terminal-text">{value}/{max}</span>
      </div>
      <div className="h-2 bg-terminal-bg rounded-full overflow-hidden">
        <div 
          className={`h-full bg-${color} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function formatLocationName(location: string): string {
  return location
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatItemName(item: string): string {
  return item
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

