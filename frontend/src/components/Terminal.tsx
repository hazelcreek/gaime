/**
 * Terminal - Main narrative display component
 * Shows the scrolling game narrative with different styling for different entry types
 */

import { useEffect, useRef, useState } from 'react';
import { useGame, NarrativeEntry } from '../hooks/useGame';
import {
  DebugInfo,
  LLMDebugInfo,
  TwoPhaseDebugInfo,
  isTwoPhaseDebugInfo,
} from '../api/client';
import LLMDebugModal from './LLMDebugModal';
import TwoPhaseDebugModal from './TwoPhaseDebugModal';

export default function Terminal() {
  const { narrative, isLoading } = useGame();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Debug modal state - can be either classic or two-phase
  const [selectedDebugInfo, setSelectedDebugInfo] = useState<DebugInfo | null>(null);

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

  // Auto-scroll to bottom when new content is added
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [narrative]);

  // Determine which modal to show based on debug info type
  const renderDebugModal = () => {
    if (!selectedDebugInfo) return null;

    if (isTwoPhaseDebugInfo(selectedDebugInfo)) {
      return (
        <TwoPhaseDebugModal
          debugInfo={selectedDebugInfo as TwoPhaseDebugInfo}
          onClose={() => setSelectedDebugInfo(null)}
        />
      );
    } else {
      return (
        <LLMDebugModal
          debugInfo={selectedDebugInfo as LLMDebugInfo}
          onClose={() => setSelectedDebugInfo(null)}
        />
      );
    }
  };

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

      {/* Debug Modal - renders appropriate type based on engine */}
      {renderDebugModal()}
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
          title="View debug details"
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
