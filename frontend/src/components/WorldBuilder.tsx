/**
 * WorldBuilder - AI-assisted world generation UI with image generation
 */

import { useState, useEffect } from 'react';
import { gameAPI, ImageGenerationResult, WorldImagesInfo } from '../api/client';

interface GeneratedWorld {
  world_id: string;
  world_yaml: string;
  locations_yaml: string;
  npcs_yaml: string;
  items_yaml: string;
  message: string;
}

interface LocationInfo {
  id: string;
  name: string;
  hasImage: boolean;
}

export default function WorldBuilder() {
  const [prompt, setPrompt] = useState('');
  const [theme, setTheme] = useState('');
  const [numLocations, setNumLocations] = useState(6);
  const [numNpcs, setNumNpcs] = useState(3);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<GeneratedWorld | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'world' | 'locations' | 'npcs' | 'items' | 'images'>('world');
  
  // Image generation state
  const [existingWorlds, setExistingWorlds] = useState<{id: string, name: string}[]>([]);
  const [selectedWorld, setSelectedWorld] = useState<string>('cursed-manor');
  const [worldImages, setWorldImages] = useState<Record<string, string>>({});
  const [locations, setLocations] = useState<LocationInfo[]>([]);
  const [isGeneratingImages, setIsGeneratingImages] = useState(false);
  const [generatingLocation, setGeneratingLocation] = useState<string | null>(null);
  const [imageGenProgress, setImageGenProgress] = useState<string>('');

  // Load existing worlds on mount
  useEffect(() => {
    loadWorlds();
  }, []);

  // Load world images when selected world changes
  useEffect(() => {
    if (selectedWorld) {
      loadWorldImages(selectedWorld);
    }
  }, [selectedWorld]);

  const loadWorlds = async () => {
    try {
      const response = await gameAPI.listWorlds();
      setExistingWorlds(response.worlds.map(w => ({ id: w.id, name: w.name })));
    } catch (err) {
      console.error('Failed to load worlds:', err);
    }
  };

  const loadWorldImages = async (worldId: string) => {
    try {
      const response = await gameAPI.listWorldImages(worldId);
      setWorldImages(response.images);
      
      // Parse locations from the world (we'll need to fetch locations separately)
      // For now, we'll extract from the images API
      const locationIds = Object.keys(response.images);
      
      // Also try to get all locations by fetching the world data
      await fetchLocations(worldId, response.images);
    } catch (err) {
      console.error('Failed to load world images:', err);
      setWorldImages({});
    }
  };

  const fetchLocations = async (worldId: string, existingImages: Record<string, string>) => {
    try {
      // Fetch locations from the dedicated endpoint
      const response = await fetch(`/api/builder/${worldId}/locations`);
      if (response.ok) {
        const data = await response.json();
        setLocations(data.locations.map((loc: any) => ({
          id: loc.id,
          name: loc.name,
          hasImage: loc.has_image || !!existingImages[loc.id]
        })));
      } else {
        // Fallback: just use image keys as locations if world not found
        const imageKeys = Object.keys(existingImages);
        if (imageKeys.length > 0) {
          setLocations(imageKeys.map(id => ({
            id,
            name: formatLocationName(id),
            hasImage: true
          })));
        } else {
          setLocations([]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch locations:', err);
      // Fallback: use existing images
      const imageKeys = Object.keys(existingImages);
      if (imageKeys.length > 0) {
        setLocations(imageKeys.map(id => ({
          id,
          name: formatLocationName(id),
          hasImage: true
        })));
      } else {
        setLocations([]);
      }
    }
  };

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
      
      // Refresh worlds list
      await loadWorlds();
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
      
      // Refresh worlds list and select the new world
      await loadWorlds();
      setSelectedWorld(result.world_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    }
  };

  const handleGenerateAllImages = async () => {
    if (!selectedWorld) return;
    
    setIsGeneratingImages(true);
    setImageGenProgress('Starting image generation...');
    setError(null);

    try {
      const response = await gameAPI.generateImages(selectedWorld);
      
      const successful = response.results.filter(r => r.success).length;
      const total = response.results.length;
      
      setImageGenProgress(`Generated ${successful}/${total} images`);
      
      // Refresh the images list
      await loadWorldImages(selectedWorld);
      
      // Show any errors
      const errors = response.results.filter(r => !r.success);
      if (errors.length > 0) {
        setError(`Some images failed: ${errors.map(e => e.location_id).join(', ')}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate images');
    } finally {
      setIsGeneratingImages(false);
      setTimeout(() => setImageGenProgress(''), 3000);
    }
  };

  const handleGenerateSingleImage = async (locationId: string) => {
    if (!selectedWorld) return;
    
    setGeneratingLocation(locationId);
    setError(null);

    try {
      const response = await gameAPI.generateSingleImage(selectedWorld, locationId);
      
      if (response.success) {
        // Refresh the images list
        await loadWorldImages(selectedWorld);
      } else {
        setError(`Failed to generate image for ${locationId}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate image');
    } finally {
      setGeneratingLocation(null);
    }
  };

  const getTabContent = () => {
    if (!result) return '';
    switch (activeTab) {
      case 'world': return result.world_yaml;
      case 'locations': return result.locations_yaml;
      case 'npcs': return result.npcs_yaml;
      case 'items': return result.items_yaml;
      default: return '';
    }
  };

  return (
    <div className="min-h-screen bg-terminal-bg p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-8 text-center">
          <h1 className="font-display text-3xl text-terminal-accent tracking-wider mb-2">
            World Builder
          </h1>
          <p className="text-terminal-dim">
            Use AI to generate game worlds and scene images
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

        {/* Image Generation Section */}
        <div className="mt-8 bg-terminal-surface border border-terminal-border rounded-lg p-6">
          <h2 className="text-terminal-text font-display text-lg mb-4 flex items-center gap-2">
            <span className="text-terminal-highlight">◈</span>
            Scene Image Generator
          </h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* World Selection */}
            <div className="space-y-4">
              <div>
                <label className="block text-terminal-dim text-sm mb-2">Select World</label>
                <select
                  value={selectedWorld}
                  onChange={(e) => setSelectedWorld(e.target.value)}
                  className="w-full bg-terminal-bg border border-terminal-border rounded p-3 
                           text-terminal-text focus:border-terminal-accent focus:outline-none"
                >
                  {existingWorlds.map(world => (
                    <option key={world.id} value={world.id}>
                      {world.name} ({world.id})
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleGenerateAllImages}
                disabled={isGeneratingImages || !selectedWorld}
                className="w-full py-3 bg-terminal-highlight/20 border border-terminal-highlight 
                         text-terminal-highlight rounded font-display tracking-wider
                         hover:bg-terminal-highlight/30 transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGeneratingImages ? 'Generating All Images...' : 'Generate All Scene Images'}
              </button>

              {imageGenProgress && (
                <p className="text-terminal-success text-sm text-center">{imageGenProgress}</p>
              )}
            </div>

            {/* Location List with Image Status */}
            <div className="lg:col-span-2">
              <label className="block text-terminal-dim text-sm mb-2">
                Locations ({Object.keys(worldImages).length} images available)
              </label>
              
              <div className="bg-terminal-bg border border-terminal-border rounded p-4 max-h-64 overflow-y-auto">
                {locations.length > 0 ? (
                  <div className="grid grid-cols-2 gap-2">
                    {locations.map(loc => (
                      <div 
                        key={loc.id}
                        className="flex items-center justify-between p-2 rounded bg-terminal-surface/50"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className={worldImages[loc.id] ? 'text-terminal-success' : 'text-terminal-dim'}>
                            {worldImages[loc.id] ? '●' : '○'}
                          </span>
                          <span className="text-terminal-text text-sm truncate">
                            {loc.name}
                          </span>
                        </div>
                        <button
                          onClick={() => handleGenerateSingleImage(loc.id)}
                          disabled={generatingLocation === loc.id}
                          className="px-2 py-1 text-xs border border-terminal-border text-terminal-dim
                                   hover:text-terminal-accent hover:border-terminal-accent
                                   rounded transition-colors disabled:opacity-50 flex-shrink-0"
                        >
                          {generatingLocation === loc.id ? '...' : worldImages[loc.id] ? '↻' : '+'}
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-terminal-dim text-sm text-center py-4">
                    No locations found. Generate or save a world first.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Image Preview Grid */}
          {Object.keys(worldImages).length > 0 && (
            <div className="mt-6">
              <label className="block text-terminal-dim text-sm mb-2">Generated Images</label>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {Object.entries(worldImages).map(([locId, url]) => (
                  <div 
                    key={locId}
                    className="relative aspect-video rounded-lg overflow-hidden border border-terminal-border
                             group cursor-pointer hover:border-terminal-accent transition-colors"
                    onClick={() => window.open(url, '_blank')}
                  >
                    <img
                      src={url}
                      alt={formatLocationName(locId)}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-terminal-bg via-transparent to-transparent" />
                    <div className="absolute bottom-0 left-0 right-0 p-2">
                      <p className="text-terminal-text text-xs font-display truncate">
                        {formatLocationName(locId)}
                      </p>
                    </div>
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleGenerateSingleImage(locId);
                        }}
                        disabled={generatingLocation === locId}
                        className="px-2 py-1 text-xs bg-terminal-surface/80 border border-terminal-border
                                 text-terminal-dim hover:text-terminal-accent rounded transition-colors"
                      >
                        {generatingLocation === locId ? '...' : '↻ Regenerate'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
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

function formatLocationName(location: string): string {
  return location
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

