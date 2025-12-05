/**
 * Sidebar - Displays inventory, location, and game controls
 */

import { useGame } from '../hooks/useGame';

export default function Sidebar() {
  const { gameState, sessionId, startNewGame, isLoading, debugMode, setDebugMode } = useGame();

  if (!sessionId) {
    return null;
  }

  return (
    <aside className="w-56 flex-shrink-0 space-y-3 self-start max-h-full overflow-y-auto">
      {/* Location */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-3">
        <h3 className="text-terminal-dim text-xs uppercase tracking-wider mb-1">Location</h3>
        <p className="text-terminal-accent font-display text-sm">
          {gameState?.current_location ? formatLocationName(gameState.current_location) : 'Unknown'}
        </p>
      </div>

      {/* Inventory */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-3">
        <h3 className="text-terminal-dim text-xs uppercase tracking-wider mb-1">Inventory</h3>
        {gameState?.inventory && gameState.inventory.length > 0 ? (
          <ul className="space-y-0.5">
            {gameState.inventory.map((item, idx) => (
              <li key={idx} className="text-terminal-text text-xs flex items-center gap-1.5">
                <span className="text-terminal-warning">•</span>
                {formatItemName(item)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-terminal-dim text-xs italic">Empty</p>
        )}
      </div>

      {/* Turn counter + New Game */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-3">
        <div className="flex justify-between text-xs mb-3">
          <span className="text-terminal-dim">Turn</span>
          <span className="text-terminal-text">{gameState?.turn_count ?? 0}</span>
        </div>
        <button
          onClick={() => startNewGame()}
          disabled={isLoading}
          className="w-full px-3 py-1.5 text-xs text-terminal-dim hover:text-terminal-error 
                     border border-terminal-border rounded hover:border-terminal-error/50
                     transition-colors disabled:opacity-50"
        >
          Start New Game
        </button>
      </div>

      {/* Debug Mode Toggle */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-3">
        <label className="flex items-center justify-between cursor-pointer">
          <span className="text-terminal-dim text-xs">Debug Mode</span>
          <button
            onClick={() => setDebugMode(!debugMode)}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              debugMode ? 'bg-terminal-warning' : 'bg-terminal-border'
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-terminal-text transition-transform ${
                debugMode ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </label>
        {debugMode && (
          <p className="text-terminal-dim/60 text-xs mt-2 italic">
            LLM interactions will be shown after each action
          </p>
        )}
      </div>
    </aside>
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

