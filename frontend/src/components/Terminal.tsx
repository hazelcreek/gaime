/**
 * Terminal - Main narrative display component
 * Shows the scrolling game narrative with different styling for different entry types
 */

import { useEffect, useRef, useState } from 'react';
import { useGame, NarrativeEntry } from '../hooks/useGame';
import { gameAPI, WorldInfo, LLMDebugInfo } from '../api/client';
import LLMDebugModal from './LLMDebugModal';

export default function Terminal() {
  const { narrative, isLoading, sessionId, startNewGame } = useGame();
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // World selection state
  const [worlds, setWorlds] = useState<WorldInfo[]>([]);
  const [selectedWorld, setSelectedWorld] = useState<string>('');
  const [playerName, setPlayerName] = useState('Traveler');
  const [loadingWorlds, setLoadingWorlds] = useState(true);
  
  // LLM Debug modal state
  const [selectedDebugInfo, setSelectedDebugInfo] = useState<LLMDebugInfo | null>(null);

  // Close debug modal on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedDebugInfo) {
        setSelectedDebugInfo(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedDebugInfo]);

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
      const selectedWorldInfo = worlds.find(w => w.id === selectedWorld);
      startNewGame(selectedWorld, playerName.trim(), selectedWorldInfo?.name);
    }
  };

  // Show welcome screen if no session
  if (!sessionId) {
    const selectedWorldInfo = worlds.find(w => w.id === selectedWorld);
    
    return (
      <div className="h-full bg-terminal-surface border border-terminal-border rounded-lg p-4 lg:p-6 
                      flex flex-col items-center justify-center overflow-y-auto">
        <div className="text-center w-full max-w-md mx-auto">
          <h2 className="font-display text-xl lg:text-2xl text-terminal-accent mb-1">
            Welcome, Traveler
          </h2>
          <p className="text-terminal-dim text-sm mb-4 leading-relaxed">
            Choose your world and prepare for adventure.
          </p>
          
          {loadingWorlds ? (
            <div className="text-terminal-dim animate-pulse">Loading worlds...</div>
          ) : (
            <div className="space-y-3">
              {/* Player Name Input */}
              <div className="text-left">
                <label className="block text-terminal-dim text-xs mb-1">Your Name</label>
                <input
                  type="text"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  placeholder="Enter your name..."
                  className="w-full px-3 py-2 bg-terminal-bg border border-terminal-border rounded
                           text-terminal-text text-sm placeholder-terminal-dim/50 focus:outline-none 
                           focus:border-terminal-accent transition-colors"
                />
              </div>
              
              {/* World Selection */}
              <div className="text-left">
                <label className="block text-terminal-dim text-xs mb-1">Choose World</label>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {worlds.map((world) => (
                    <button
                      key={world.id}
                      onClick={() => setSelectedWorld(world.id)}
                      className={`w-full text-left p-2.5 rounded border transition-all ${
                        selectedWorld === world.id
                          ? 'bg-terminal-accent/20 border-terminal-accent'
                          : 'bg-terminal-bg border-terminal-border hover:border-terminal-dim'
                      }`}
                    >
                      <div className="font-display text-sm text-terminal-accent">{world.name}</div>
                      <div className="text-terminal-dim text-xs">{world.theme}</div>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* World Description */}
              {selectedWorldInfo?.description && (
                <div className="text-left p-2.5 bg-terminal-bg/50 rounded border border-terminal-border/50">
                  <p className="text-terminal-dim text-xs leading-relaxed">
                    {selectedWorldInfo.description}
                  </p>
                </div>
              )}
              
              {/* Start Button */}
              <button
                onClick={handleStartGame}
                disabled={isLoading || !selectedWorld || !playerName.trim()}
                className="w-full px-4 py-2.5 bg-terminal-accent/20 border border-terminal-accent text-terminal-accent 
                           rounded hover:bg-terminal-accent/30 transition-colors disabled:opacity-50
                           font-display tracking-wider text-sm mt-2"
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
    <>
      <div 
        ref={scrollRef}
        className="h-full bg-terminal-surface border border-terminal-border rounded-lg p-3 
                   overflow-y-auto space-y-2.5"
      >
        {narrative.map((entry) => (
          <NarrativeEntryRow 
            key={entry.id}
            entry={entry}
            onDebugClick={() => entry.debugInfo && setSelectedDebugInfo(entry.debugInfo)}
          />
        ))}
        
        {isLoading && (
          <div className="flex items-center gap-2 text-terminal-dim text-sm">
            <span className="animate-pulse">●</span>
            <span>The world shifts around you...</span>
          </div>
        )}
      </div>

      {/* LLM Debug Modal */}
      {selectedDebugInfo && (
        <LLMDebugModal 
          debugInfo={selectedDebugInfo}
          onClose={() => setSelectedDebugInfo(null)}
        />
      )}
    </>
  );
}

interface NarrativeEntryRowProps {
  entry: NarrativeEntry;
  onDebugClick: () => void;
}

function NarrativeEntryRow({ entry, onDebugClick }: NarrativeEntryRowProps) {
  return (
    <div className={`animate-fade-in flex items-start gap-2 group ${getEntryStyles(entry.type)}`}>
      <div className="flex-1 min-w-0">
        {entry.type === 'player' && (
          <span className="text-terminal-accent mr-1.5">›</span>
        )}
        <span className="whitespace-pre-wrap break-words">{entry.content}</span>
      </div>
      
      {/* Debug icon - only show for entries with debug info */}
      {entry.debugInfo && (
        <button
          onClick={onDebugClick}
          className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
                     text-terminal-dim hover:text-terminal-warning text-xs p-1 rounded
                     hover:bg-terminal-warning/10"
          title="View LLM interaction details"
        >
          🔧
        </button>
      )}
    </div>
  );
}

function getEntryStyles(type: string): string {
  switch (type) {
    case 'narrative':
      return 'text-terminal-text text-sm leading-relaxed';
    case 'player':
      return 'text-terminal-accent text-sm font-medium';
    case 'system':
      return 'text-terminal-dim italic text-xs';
    case 'error':
      return 'text-terminal-error text-sm';
    default:
      return 'text-terminal-text text-sm';
  }
}

