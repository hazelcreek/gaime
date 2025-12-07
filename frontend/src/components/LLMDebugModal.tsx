/**
 * LLMDebugModal - Modal displaying LLM interaction details for a specific message
 * Shows system prompt, user prompt, raw response, and parsed result
 */

import { useState } from 'react';
import { LLMDebugInfo } from '../api/client';

interface LLMDebugModalProps {
  debugInfo: LLMDebugInfo;
  onClose: () => void;
}

export default function LLMDebugModal({ debugInfo, onClose }: LLMDebugModalProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    system: false,
    user: true,
    raw: true,
    parsed: true,
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div 
        className="bg-terminal-surface border border-terminal-warning/30 rounded-lg max-w-3xl w-full mx-4 
                   max-h-[85vh] overflow-hidden flex flex-col animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-terminal-warning/30 bg-terminal-warning/10">
          <div className="flex items-center gap-2">
            <span className="text-terminal-warning">🔧</span>
            <h2 className="font-display text-terminal-warning tracking-wider text-sm uppercase">
              LLM Debug Info
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-terminal-dim text-xs">{debugInfo.model}</span>
            <button
              onClick={onClose}
              className="text-terminal-dim hover:text-terminal-text transition-colors text-lg leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {/* Timestamp */}
          <div className="text-terminal-dim text-xs px-1">
            {new Date(debugInfo.timestamp).toLocaleString()}
          </div>

          {/* System Prompt Section */}
          <CollapsibleSection
            title="System Prompt"
            isExpanded={expandedSections.system}
            onToggle={() => toggleSection('system')}
            badge={`${debugInfo.system_prompt.length} chars`}
          >
            <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
              {debugInfo.system_prompt}
            </pre>
          </CollapsibleSection>

          {/* User Prompt Section */}
          <CollapsibleSection
            title="User Prompt"
            isExpanded={expandedSections.user}
            onToggle={() => toggleSection('user')}
          >
            <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
              {debugInfo.user_prompt}
            </pre>
          </CollapsibleSection>

          {/* Raw Response Section */}
          <CollapsibleSection
            title="Raw Response"
            isExpanded={expandedSections.raw}
            onToggle={() => toggleSection('raw')}
          >
            <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
              {debugInfo.raw_response}
            </pre>
          </CollapsibleSection>

          {/* Parsed Result Section */}
          <CollapsibleSection
            title="Parsed Result"
            isExpanded={expandedSections.parsed}
            onToggle={() => toggleSection('parsed')}
          >
            <pre className="text-xs text-terminal-success whitespace-pre-wrap font-mono leading-relaxed">
              {JSON.stringify(debugInfo.parsed_response, null, 2)}
            </pre>
          </CollapsibleSection>
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-terminal-warning/30 bg-terminal-bg/30 text-center">
          <span className="text-terminal-dim text-xs">
            Press Escape or click outside to close
          </span>
        </div>
      </div>
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
        <div className="p-2 bg-terminal-bg/20 max-h-64 overflow-y-auto">
          {children}
        </div>
      )}
    </div>
  );
}

