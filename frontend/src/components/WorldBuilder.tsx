/**
 * WorldBuilder - AI-assisted world generation UI
 */

import { useState } from 'react';

interface GeneratedWorld {
  world_id: string;
  world_yaml: string;
  locations_yaml: string;
  npcs_yaml: string;
  items_yaml: string;
  message: string;
}

export default function WorldBuilder() {
  const [prompt, setPrompt] = useState('');
  const [theme, setTheme] = useState('');
  const [numLocations, setNumLocations] = useState(6);
  const [numNpcs, setNumNpcs] = useState(3);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<GeneratedWorld | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'world' | 'locations' | 'npcs' | 'items'>('world');

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('Please enter a world description');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/builder/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          theme: theme.trim() || null,
          num_locations: numLocations,
          num_npcs: numNpcs,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate world');
      }

      const data: GeneratedWorld = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!result) return;

    try {
      const response = await fetch(`/api/builder/save/${result.world_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_yaml: result.world_yaml,
          locations_yaml: result.locations_yaml,
          npcs_yaml: result.npcs_yaml,
          items_yaml: result.items_yaml,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save world');
      }

      alert(`World "${result.world_id}" saved successfully!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    }
  };

  const getTabContent = () => {
    if (!result) return '';
    switch (activeTab) {
      case 'world': return result.world_yaml;
      case 'locations': return result.locations_yaml;
      case 'npcs': return result.npcs_yaml;
      case 'items': return result.items_yaml;
    }
  };

  return (
    <div className="min-h-screen bg-terminal-bg p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="mb-8 text-center">
          <h1 className="font-display text-3xl text-terminal-accent tracking-wider mb-2">
            World Builder
          </h1>
          <p className="text-terminal-dim">
            Use AI to generate game worlds from descriptions
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Panel */}
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6">
            <h2 className="text-terminal-text font-display text-lg mb-4">Describe Your World</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-terminal-dim text-sm mb-1">World Description *</label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="A haunted lighthouse on a remote island, where the keeper has gone mad..."
                  className="w-full h-32 bg-terminal-bg border border-terminal-border rounded p-3 
                           text-terminal-text placeholder-terminal-dim resize-none
                           focus:border-terminal-accent focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-terminal-dim text-sm mb-1">Theme (optional)</label>
                <input
                  type="text"
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  placeholder="cosmic horror, mystery, fantasy..."
                  className="w-full bg-terminal-bg border border-terminal-border rounded p-3 
                           text-terminal-text placeholder-terminal-dim
                           focus:border-terminal-accent focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-terminal-dim text-sm mb-1">Locations</label>
                  <input
                    type="number"
                    value={numLocations}
                    onChange={(e) => setNumLocations(parseInt(e.target.value) || 6)}
                    min={3}
                    max={15}
                    className="w-full bg-terminal-bg border border-terminal-border rounded p-3 
                             text-terminal-text focus:border-terminal-accent focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-terminal-dim text-sm mb-1">NPCs</label>
                  <input
                    type="number"
                    value={numNpcs}
                    onChange={(e) => setNumNpcs(parseInt(e.target.value) || 3)}
                    min={1}
                    max={10}
                    className="w-full bg-terminal-bg border border-terminal-border rounded p-3 
                             text-terminal-text focus:border-terminal-accent focus:outline-none"
                  />
                </div>
              </div>

              <button
                onClick={handleGenerate}
                disabled={isLoading || !prompt.trim()}
                className="w-full py-3 bg-terminal-accent/20 border border-terminal-accent 
                         text-terminal-accent rounded font-display tracking-wider
                         hover:bg-terminal-accent/30 transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Generating...' : 'Generate World'}
              </button>

              {error && (
                <p className="text-terminal-error text-sm">{error}</p>
              )}
            </div>
          </div>

          {/* Output Panel */}
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-terminal-text font-display text-lg">
                {result ? `Generated: ${result.world_id}` : 'Generated World'}
              </h2>
              {result && (
                <button
                  onClick={handleSave}
                  className="px-4 py-2 text-sm border border-terminal-success text-terminal-success
                           rounded hover:bg-terminal-success/20 transition-colors"
                >
                  Save World
                </button>
              )}
            </div>

            {result ? (
              <>
                {/* Tabs */}
                <div className="flex gap-2 mb-4">
                  {(['world', 'locations', 'npcs', 'items'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-3 py-1 text-sm rounded transition-colors ${
                        activeTab === tab
                          ? 'bg-terminal-accent/20 text-terminal-accent'
                          : 'text-terminal-dim hover:text-terminal-text'
                      }`}
                    >
                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                  ))}
                </div>

                {/* Content */}
                <pre className="bg-terminal-bg border border-terminal-border rounded p-4 
                              overflow-auto max-h-96 text-sm text-terminal-text font-mono">
                  {getTabContent()}
                </pre>
              </>
            ) : (
              <div className="flex items-center justify-center h-64 text-terminal-dim">
                <p>Generated world will appear here</p>
              </div>
            )}
          </div>
        </div>

        {/* Back to game link */}
        <div className="mt-8 text-center">
          <a
            href="/"
            className="text-terminal-dim hover:text-terminal-accent transition-colors"
          >
            ← Back to Game
          </a>
        </div>
      </div>
    </div>
  );
}

