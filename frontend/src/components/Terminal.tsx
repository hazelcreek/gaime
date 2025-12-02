/**
 * Terminal - Main narrative display component
 * Shows the scrolling game narrative with different styling for different entry types
 */

import { useEffect, useRef, useState } from 'react';
import { useGame } from '../hooks/useGame';
import { gameAPI, WorldInfo } from '../api/client';

export default function Terminal() {
  const { narrative, isLoading, sessionId, startNewGame } = useGame();
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // World selection state
  const [worlds, setWorlds] = useState<WorldInfo[]>([]);
  const [selectedWorld, setSelectedWorld] = useState<string>('');
  const [playerName, setPlayerName] = useState('Traveler');
  const [loadingWorlds, setLoadingWorlds] = useState(true);

  // Load available worlds on mount
  useEffect(() => {
    if (!sessionId) {
      setLoadingWorlds(true);
      gameAPI.listWorlds()
        .then(({ worlds }) => {
          setWorlds(worlds);
          if (worlds.length > 0 && !selectedWorld) {
            setSelectedWorld(worlds[0].id);
          }
        })
        .catch(() => {
          // Fallback to default world
          setWorlds([{ id: 'cursed-manor', name: 'The Cursed Manor', theme: 'Victorian gothic horror' }]);
          setSelectedWorld('cursed-manor');
        })
        .finally(() => setLoadingWorlds(false));
    }
  }, [sessionId, selectedWorld]);

  // Auto-scroll to bottom when new content is added
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [narrative]);

  // Handle game start
  const handleStartGame = () => {
    if (selectedWorld && playerName.trim()) {
      startNewGame(selectedWorld, playerName.trim());
    }
  };

  // Show welcome screen if no session
  if (!sessionId) {
    const selectedWorldInfo = worlds.find(w => w.id === selectedWorld);
    
    return (
      <div className="flex-1 bg-terminal-surface border border-terminal-border rounded-lg p-6 flex flex-col items-center justify-center">
        <div className="text-center max-w-lg w-full">
          <h2 className="font-display text-2xl text-terminal-accent mb-2">
            Welcome, Traveler
          </h2>
          <p className="text-terminal-dim mb-6 leading-relaxed">
            Choose your world and prepare for adventure.
          </p>
          
          {loadingWorlds ? (
            <div className="text-terminal-dim animate-pulse">Loading worlds...</div>
          ) : (
            <div className="space-y-4">
              {/* Player Name Input */}
              <div className="text-left">
                <label className="block text-terminal-dim text-sm mb-1">Your Name</label>
                <input
                  type="text"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  placeholder="Enter your name..."
                  className="w-full px-3 py-2 bg-terminal-bg border border-terminal-border rounded
                           text-terminal-text placeholder-terminal-dim/50 focus:outline-none 
                           focus:border-terminal-accent transition-colors"
                />
              </div>
              
              {/* World Selection */}
              <div className="text-left">
                <label className="block text-terminal-dim text-sm mb-1">Choose World</label>
                <div className="space-y-2">
                  {worlds.map((world) => (
                    <button
                      key={world.id}
                      onClick={() => setSelectedWorld(world.id)}
                      className={`w-full text-left p-3 rounded border transition-all ${
                        selectedWorld === world.id
                          ? 'bg-terminal-accent/20 border-terminal-accent'
                          : 'bg-terminal-bg border-terminal-border hover:border-terminal-dim'
                      }`}
                    >
                      <div className="font-display text-terminal-accent">{world.name}</div>
                      <div className="text-terminal-dim text-sm">{world.theme}</div>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* World Description */}
              {selectedWorldInfo?.description && (
                <div className="text-left p-3 bg-terminal-bg/50 rounded border border-terminal-border/50">
                  <p className="text-terminal-dim text-sm leading-relaxed">
                    {selectedWorldInfo.description}
                  </p>
                </div>
              )}
              
              {/* Start Button */}
              <button
                onClick={handleStartGame}
                disabled={isLoading || !selectedWorld || !playerName.trim()}
                className="w-full px-6 py-3 bg-terminal-accent/20 border border-terminal-accent text-terminal-accent 
                           rounded hover:bg-terminal-accent/30 transition-colors disabled:opacity-50
                           font-display tracking-wider mt-4"
              >
                {isLoading ? 'Preparing...' : 'Begin Adventure'}
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={scrollRef}
      className="flex-1 bg-terminal-surface border border-terminal-border rounded-lg p-4 
                 overflow-y-auto space-y-4 min-h-[400px]"
    >
      {narrative.map((entry) => (
        <div 
          key={entry.id} 
          className={`animate-fade-in ${getEntryStyles(entry.type)}`}
        >
          {entry.type === 'player' && (
            <span className="text-terminal-accent mr-2">›</span>
          )}
          <span className="whitespace-pre-wrap">{entry.content}</span>
        </div>
      ))}
      
      {isLoading && (
        <div className="flex items-center gap-2 text-terminal-dim">
          <span className="animate-pulse">●</span>
          <span>The world shifts around you...</span>
        </div>
      )}
    </div>
  );
}

function getEntryStyles(type: string): string {
  switch (type) {
    case 'narrative':
      return 'text-terminal-text leading-relaxed';
    case 'player':
      return 'text-terminal-accent font-medium';
    case 'system':
      return 'text-terminal-dim italic text-sm';
    case 'error':
      return 'text-terminal-error';
    default:
      return 'text-terminal-text';
  }
}

