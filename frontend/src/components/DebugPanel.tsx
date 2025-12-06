/**
 * DebugPanel - Displays LLM interaction details in a compact, expandable panel
 * Shows only when debug mode is enabled
 */

import { useState } from 'react';
import { useGame } from '../hooks/useGame';

export default function DebugPanel() {
  const { debugMode, lastDebugInfo } = useGame();
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    system: false,
    user: true,
    raw: true,
    parsed: true,
  });

  // Don't render if debug mode is off or no debug info
  if (!debugMode || !lastDebugInfo) {
    return null;
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  return (
    <div className="flex-shrink-0">
      {/* Collapsed state - just a clickable bar */}
      {!isExpanded ? (
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full flex items-center justify-between px-3 py-2 
                     bg-terminal-warning/10 border border-terminal-warning/30 rounded-lg
                     hover:bg-terminal-warning/20 transition-colors group"
        >
          <div className="flex items-center gap-2">
            <span className="text-terminal-warning text-sm">🔧</span>
            <span className="text-terminal-warning text-xs font-medium uppercase tracking-wider">
              LLM Debug Info Available
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-terminal-dim text-xs">{lastDebugInfo.model}</span>
            <span className="text-terminal-dim text-xs group-hover:text-terminal-warning transition-colors">
              Click to expand ▼
            </span>
          </div>
        </button>
      ) : (
        /* Expanded state - full debug info */
        <div className="bg-terminal-surface border border-terminal-warning/30 rounded-lg overflow-hidden">
          {/* Header */}
          <button
            onClick={() => setIsExpanded(false)}
            className="w-full flex items-center justify-between px-3 py-2 
                       bg-terminal-warning/10 hover:bg-terminal-warning/20 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-terminal-warning text-sm">🔧</span>
              <span className="text-terminal-warning text-xs font-medium uppercase tracking-wider">
                LLM Debug
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-terminal-dim text-xs">{lastDebugInfo.model}</span>
              <span className="text-terminal-dim text-xs">▲ Collapse</span>
            </div>
          </button>

          <div className="p-2 space-y-2 max-h-[50vh] overflow-y-auto">
            {/* Timestamp */}
            <div className="text-terminal-dim text-xs px-1">
              {new Date(lastDebugInfo.timestamp).toLocaleString()}
            </div>

            {/* System Prompt Section */}
            <CollapsibleSection
              title="System Prompt"
              isExpanded={expandedSections.system}
              onToggle={() => toggleSection('system')}
              badge={`${lastDebugInfo.system_prompt.length} chars`}
            >
              <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
                {lastDebugInfo.system_prompt}
              </pre>
            </CollapsibleSection>

            {/* User Prompt Section */}
            <CollapsibleSection
              title="User Prompt"
              isExpanded={expandedSections.user}
              onToggle={() => toggleSection('user')}
            >
              <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
                {lastDebugInfo.user_prompt}
              </pre>
            </CollapsibleSection>

            {/* Raw Response Section */}
            <CollapsibleSection
              title="Raw Response"
              isExpanded={expandedSections.raw}
              onToggle={() => toggleSection('raw')}
            >
              <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
                {lastDebugInfo.raw_response}
              </pre>
            </CollapsibleSection>

            {/* Parsed Result Section */}
            <CollapsibleSection
              title="Parsed Result"
              isExpanded={expandedSections.parsed}
              onToggle={() => toggleSection('parsed')}
            >
              <pre className="text-xs text-terminal-success whitespace-pre-wrap font-mono leading-relaxed">
                {JSON.stringify(lastDebugInfo.parsed_response, null, 2)}
              </pre>
            </CollapsibleSection>
          </div>
        </div>
      )}
    </div>
  );
}

interface CollapsibleSectionProps {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  badge?: string;
  children: React.ReactNode;
}

function CollapsibleSection({ title, isExpanded, onToggle, badge, children }: CollapsibleSectionProps) {
  return (
    <div className="border border-terminal-border/50 rounded overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-2 py-1.5 
                   bg-terminal-bg/30 hover:bg-terminal-bg/50 transition-colors"
      >
        <span className="text-terminal-dim text-xs font-medium">{title}</span>
        <div className="flex items-center gap-2">
          {badge && (
            <span className="text-terminal-dim/60 text-xs">{badge}</span>
          )}
          <span className="text-terminal-dim text-xs">
            {isExpanded ? '−' : '+'}
          </span>
        </div>
      </button>
      {isExpanded && (
        <div className="p-2 bg-terminal-bg/20 max-h-48 overflow-y-auto">
          {children}
        </div>
      )}
    </div>
  );
}
