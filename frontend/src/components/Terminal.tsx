/**
 * Terminal - Main narrative display component
 * Shows the scrolling game narrative with different styling for different entry types
 */

import { useEffect, useRef } from 'react';
import { useGame } from '../hooks/useGame';

export default function Terminal() {
  const { narrative, isLoading, sessionId, startNewGame } = useGame();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new content is added
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [narrative]);

  // Show welcome screen if no session
  if (!sessionId) {
    return (
      <div className="flex-1 bg-terminal-surface border border-terminal-border rounded-lg p-6 flex flex-col items-center justify-center">
        <div className="text-center max-w-md">
          <h2 className="font-display text-2xl text-terminal-accent mb-4">
            Welcome, Traveler
          </h2>
          <p className="text-terminal-dim mb-6 leading-relaxed">
            You stand at the threshold of adventure. Ancient mysteries await those 
            brave enough to seek them. Will you answer the call?
          </p>
          <button
            onClick={() => startNewGame()}
            disabled={isLoading}
            className="px-6 py-3 bg-terminal-accent/20 border border-terminal-accent text-terminal-accent 
                       rounded hover:bg-terminal-accent/30 transition-colors disabled:opacity-50
                       font-display tracking-wider"
          >
            {isLoading ? 'Preparing...' : 'Begin Adventure'}
          </button>
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

