/**
 * CommandInput - Player input component with command history and debug toggle
 */

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { useGame } from '../hooks/useGame';

export default function CommandInput() {
  const { sendAction, isLoading, sessionId, debugMode, setDebugMode, lastDebugInfo } = useGame();
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [showDebugHint, setShowDebugHint] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on mount and when session changes
  useEffect(() => {
    if (sessionId) {
      inputRef.current?.focus();
    }
  }, [sessionId]);

  const handleSubmit = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    // Add to history
    setHistory(prev => [...prev.filter(h => h !== trimmed), trimmed]);
    setHistoryIndex(-1);
    setInput('');

    await sendAction(trimmed);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSubmit();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0) {
        const newIndex = historyIndex < history.length - 1 ? historyIndex + 1 : historyIndex;
        setHistoryIndex(newIndex);
        setInput(history[history.length - 1 - newIndex] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(history[history.length - 1 - newIndex] || '');
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInput('');
      }
    }
  };

  if (!sessionId) {
    return null;
  }

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded-lg p-3 flex items-center gap-2">
      {/* Debug toggle button */}
      <button
        onClick={() => setDebugMode(!debugMode)}
        onMouseEnter={() => setShowDebugHint(true)}
        onMouseLeave={() => setShowDebugHint(false)}
        className={`relative p-1.5 rounded transition-colors ${
          debugMode 
            ? 'text-terminal-warning bg-terminal-warning/10 border border-terminal-warning/30' 
            : 'text-terminal-dim hover:text-terminal-accent'
        }`}
        title={debugMode ? 'Debug mode ON - click to disable' : 'Enable debug mode'}
      >
        <span className="text-sm">🔧</span>
        {/* Debug mode indicator dot */}
        {debugMode && lastDebugInfo && (
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-terminal-warning rounded-full animate-pulse" />
        )}
        {/* Tooltip */}
        {showDebugHint && (
          <div className="absolute bottom-full left-0 mb-2 px-2 py-1 bg-terminal-bg border border-terminal-border 
                          rounded text-xs text-terminal-dim whitespace-nowrap z-10">
            {debugMode ? 'Debug ON - view LLM details below' : 'Enable debug mode'}
          </div>
        )}
      </button>
      
      {/* Command prompt */}
      <span className="text-terminal-accent font-bold">›</span>
      
      {/* Input field */}
      <input
        ref={inputRef}
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
        placeholder={isLoading ? 'Processing...' : 'What do you do?'}
        className="flex-1 bg-transparent outline-none text-terminal-text placeholder-terminal-dim"
        autoComplete="off"
        spellCheck="false"
      />
      
      {/* Send button */}
      <button
        onClick={handleSubmit}
        disabled={isLoading || !input.trim()}
        className="px-3 py-1 text-sm text-terminal-dim hover:text-terminal-accent 
                   disabled:opacity-50 disabled:hover:text-terminal-dim transition-colors"
      >
        Send
      </button>
    </div>
  );
}
