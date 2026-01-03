/**
 * TwoPhaseDebugModal - Modal displaying the full two-phase pipeline debug info
 * Shows: User Input -> Parser -> Validation -> Events -> Narrator
 */

import { useState } from 'react';
import { TwoPhaseDebugInfo, LLMDebugInfo } from '../api/client';

interface TwoPhaseDebugModalProps {
  debugInfo: TwoPhaseDebugInfo;
  onClose: () => void;
}

export default function TwoPhaseDebugModal({ debugInfo, onClose }: TwoPhaseDebugModalProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    input: true,
    parser: true,
    interactor: false,
    validation: true,
    events: true,
    narrator: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // Determine validation status
  const validationValid = debugInfo.validation_result?.valid ?? null;
  const validationStatusColor = validationValid === true
    ? 'text-terminal-success'
    : validationValid === false
      ? 'text-terminal-error'
      : 'text-terminal-dim';
  const validationStatusText = validationValid === true
    ? '✓ Valid'
    : validationValid === false
      ? '✗ Rejected'
      : '—';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-terminal-surface border border-terminal-accent/30 rounded-lg max-w-4xl w-full mx-4
                   max-h-[90vh] overflow-hidden flex flex-col animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-terminal-accent/30 bg-terminal-accent/10">
          <div className="flex items-center gap-2">
            <span className="text-terminal-accent">⚙</span>
            <h2 className="font-display text-terminal-accent tracking-wider text-sm uppercase">
              Two-Phase Pipeline Debug
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-terminal-dim text-xs">
              {debugInfo.parser_type === 'rule_based' ? 'Rule-Based' : 'Interactor AI'}
            </span>
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
          {/* 1. User Input */}
          <CollapsibleSection
            title="1. User Input"
            isExpanded={expandedSections.input}
            onToggle={() => toggleSection('input')}
            badge={`${debugInfo.raw_input.length} chars`}
          >
            <div className="bg-terminal-bg/50 px-3 py-2 rounded border border-terminal-border/50">
              <code className="text-terminal-accent text-sm font-mono">
                &gt; {debugInfo.raw_input}
              </code>
            </div>
          </CollapsibleSection>

          {/* 2. Parser */}
          <CollapsibleSection
            title="2. Parser"
            isExpanded={expandedSections.parser}
            onToggle={() => toggleSection('parser')}
            badge={debugInfo.parser_type}
            badgeColor={debugInfo.parser_type === 'rule_based' ? 'text-terminal-success' : 'text-terminal-warning'}
          >
            {debugInfo.parsed_intent ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-terminal-dim">Action Type:</span>
                  <span className="text-terminal-accent font-mono">
                    {String(debugInfo.parsed_intent.action_type ?? 'unknown').toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-terminal-dim">Target:</span>
                  <span className="text-terminal-text font-mono">
                    {String(debugInfo.parsed_intent.target_id ?? '—')}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-terminal-dim">Confidence:</span>
                  <span className="text-terminal-text">
                    {((debugInfo.parsed_intent.confidence as number) * 100).toFixed(0)}%
                  </span>
                </div>
                <details className="mt-2">
                  <summary className="text-terminal-dim text-xs cursor-pointer hover:text-terminal-text">
                    Full ActionIntent JSON
                  </summary>
                  <pre className="text-xs text-terminal-dim whitespace-pre-wrap font-mono mt-1 bg-terminal-bg/30 p-2 rounded">
                    {JSON.stringify(debugInfo.parsed_intent, null, 2)}
                  </pre>
                </details>
              </div>
            ) : (
              <div className="text-terminal-dim text-sm italic">
                Input not recognized by parser
              </div>
            )}
          </CollapsibleSection>

          {/* 3. InteractorAI (only show if used) */}
          {debugInfo.interactor_debug && (
            <CollapsibleSection
              title="3. Interactor AI"
              isExpanded={expandedSections.interactor}
              onToggle={() => toggleSection('interactor')}
              badge={debugInfo.interactor_debug.model}
            >
              <LLMDebugContent debugInfo={debugInfo.interactor_debug} />
            </CollapsibleSection>
          )}

          {/* 4. Validation */}
          <CollapsibleSection
            title={debugInfo.interactor_debug ? '4. Validation' : '3. Validation'}
            isExpanded={expandedSections.validation}
            onToggle={() => toggleSection('validation')}
            badge={validationStatusText}
            badgeColor={validationStatusColor}
          >
            {debugInfo.validation_result ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-terminal-dim">Result:</span>
                  <span className={validationStatusColor}>
                    {validationValid ? 'Valid' : 'Rejected'}
                  </span>
                </div>
                {!validationValid && debugInfo.validation_result.rejection_code && (
                  <>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-terminal-dim">Code:</span>
                      <span className="text-terminal-error font-mono">
                        {String(debugInfo.validation_result.rejection_code)}
                      </span>
                    </div>
                    <div className="flex items-start gap-2 text-xs">
                      <span className="text-terminal-dim shrink-0">Reason:</span>
                      <span className="text-terminal-text">
                        {String(debugInfo.validation_result.rejection_reason ?? '—')}
                      </span>
                    </div>
                  </>
                )}
                {debugInfo.validation_result.hint && (
                  <div className="flex items-start gap-2 text-xs">
                    <span className="text-terminal-dim shrink-0">Hint:</span>
                    <span className="text-terminal-warning">
                      {String(debugInfo.validation_result.hint)}
                    </span>
                  </div>
                )}
                {debugInfo.validation_result.context && Object.keys(debugInfo.validation_result.context as object).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-terminal-dim text-xs cursor-pointer hover:text-terminal-text">
                      Context
                    </summary>
                    <pre className="text-xs text-terminal-dim whitespace-pre-wrap font-mono mt-1 bg-terminal-bg/30 p-2 rounded">
                      {JSON.stringify(debugInfo.validation_result.context, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ) : (
              <div className="text-terminal-dim text-sm italic">
                No validation performed
              </div>
            )}
          </CollapsibleSection>

          {/* 5. Events */}
          <CollapsibleSection
            title={debugInfo.interactor_debug ? '5. Events' : '4. Events'}
            isExpanded={expandedSections.events}
            onToggle={() => toggleSection('events')}
            badge={`${debugInfo.events.length} event${debugInfo.events.length !== 1 ? 's' : ''}`}
          >
            {debugInfo.events.length > 0 ? (
              <div className="space-y-2">
                {debugInfo.events.map((event, idx) => (
                  <div
                    key={idx}
                    className="bg-terminal-bg/30 px-3 py-2 rounded border border-terminal-border/30"
                  >
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-terminal-accent font-mono font-medium">
                        {String(event.type ?? 'unknown').toUpperCase()}
                      </span>
                      {event.subject && (
                        <>
                          <span className="text-terminal-dim">→</span>
                          <span className="text-terminal-text">{String(event.subject)}</span>
                        </>
                      )}
                    </div>
                    {event.context && Object.keys(event.context as object).length > 0 && (
                      <details className="mt-1">
                        <summary className="text-terminal-dim text-xs cursor-pointer hover:text-terminal-text">
                          Context
                        </summary>
                        <pre className="text-xs text-terminal-dim whitespace-pre-wrap font-mono mt-1">
                          {JSON.stringify(event.context, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-terminal-dim text-sm italic">
                No events generated
              </div>
            )}
          </CollapsibleSection>

          {/* 6. Narrator */}
          {debugInfo.narrator_debug && (
            <CollapsibleSection
              title={debugInfo.interactor_debug ? '6. Narrator' : '5. Narrator'}
              isExpanded={expandedSections.narrator}
              onToggle={() => toggleSection('narrator')}
              badge={debugInfo.narrator_debug.model}
            >
              <LLMDebugContent debugInfo={debugInfo.narrator_debug} />
            </CollapsibleSection>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-terminal-accent/30 bg-terminal-bg/30 text-center">
          <span className="text-terminal-dim text-xs">
            Press Escape or click outside to close
          </span>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Helper Components
// =============================================================================

interface CollapsibleSectionProps {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  badge?: string;
  badgeColor?: string;
  children: React.ReactNode;
}

function CollapsibleSection({
  title,
  isExpanded,
  onToggle,
  badge,
  badgeColor = 'text-terminal-dim/60',
  children,
}: CollapsibleSectionProps) {
  return (
    <div className="border border-terminal-border/50 rounded overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2
                   bg-terminal-bg/30 hover:bg-terminal-bg/50 transition-colors"
      >
        <span className="text-terminal-text text-xs font-medium">{title}</span>
        <div className="flex items-center gap-2">
          {badge && (
            <span className={`text-xs ${badgeColor}`}>{badge}</span>
          )}
          <span className="text-terminal-dim text-xs">
            {isExpanded ? '−' : '+'}
          </span>
        </div>
      </button>
      {isExpanded && (
        <div className="p-3 bg-terminal-bg/20">
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * Reusable component for displaying LLM debug info (system prompt, user prompt, response)
 */
function LLMDebugContent({ debugInfo }: { debugInfo: LLMDebugInfo }) {
  const [innerExpanded, setInnerExpanded] = useState<Record<string, boolean>>({
    system: false,
    user: true,
    raw: true,
    parsed: false,
  });

  const toggleInner = (section: string) => {
    setInnerExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  return (
    <div className="space-y-2">
      {/* Timestamp and Metrics */}
      <div className="flex items-center justify-between text-terminal-dim text-xs">
        <span>{new Date(debugInfo.timestamp).toLocaleString()}</span>
        <div className="flex items-center gap-3">
          {debugInfo.duration_ms != null && (
            <span className="text-terminal-accent">
              {debugInfo.duration_ms.toLocaleString(undefined, { maximumFractionDigits: 0 })}ms
            </span>
          )}
          {debugInfo.tokens_total != null && (
            <span>
              {debugInfo.tokens_input?.toLocaleString() ?? '?'} in / {debugInfo.tokens_output?.toLocaleString() ?? '?'} out = {debugInfo.tokens_total.toLocaleString()} tokens
            </span>
          )}
        </div>
      </div>

      {/* System Prompt */}
      <InnerCollapsible
        title="System Prompt"
        isExpanded={innerExpanded.system}
        onToggle={() => toggleInner('system')}
        badge={`${debugInfo.system_prompt.length} chars`}
      >
        <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
          {debugInfo.system_prompt}
        </pre>
      </InnerCollapsible>

      {/* User Prompt */}
      <InnerCollapsible
        title="User Prompt"
        isExpanded={innerExpanded.user}
        onToggle={() => toggleInner('user')}
      >
        <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
          {debugInfo.user_prompt}
        </pre>
      </InnerCollapsible>

      {/* Raw Response */}
      <InnerCollapsible
        title="Raw Response"
        isExpanded={innerExpanded.raw}
        onToggle={() => toggleInner('raw')}
      >
        <pre className="text-xs text-terminal-text whitespace-pre-wrap font-mono leading-relaxed">
          {debugInfo.raw_response}
        </pre>
      </InnerCollapsible>

      {/* Parsed Result */}
      <InnerCollapsible
        title="Parsed Result"
        isExpanded={innerExpanded.parsed}
        onToggle={() => toggleInner('parsed')}
      >
        <pre className="text-xs text-terminal-success whitespace-pre-wrap font-mono leading-relaxed">
          {JSON.stringify(debugInfo.parsed_response, null, 2)}
        </pre>
      </InnerCollapsible>
    </div>
  );
}

interface InnerCollapsibleProps {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  badge?: string;
  children: React.ReactNode;
}

function InnerCollapsible({ title, isExpanded, onToggle, badge, children }: InnerCollapsibleProps) {
  return (
    <div className="border border-terminal-border/30 rounded overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-2 py-1
                   bg-terminal-bg/20 hover:bg-terminal-bg/40 transition-colors"
      >
        <span className="text-terminal-dim text-xs">{title}</span>
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
        <div className="p-2 bg-terminal-bg/10">
          {children}
        </div>
      )}
    </div>
  );
}
