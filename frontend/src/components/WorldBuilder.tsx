/**
 * WorldBuilder - AI-assisted world generation UI with image generation
 */

import { useState, useEffect } from 'react';
import { gameAPI } from '../api/client';

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
  conditionalNpcs: string[];  // NPCs with appears_when conditions
  hasVariants: boolean;       // Whether variants have been generated
  variantCount: number;       // Number of variants available
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
  const [generatingVariants, setGeneratingVariants] = useState<string | null>(null);
  const [imageGenProgress, setImageGenProgress] = useState<string>('');
  const selectedImageModel = 'gemini-3-pro-image-preview';

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
      
      // Fetch all locations from the world data
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
        const locationsList = data.locations.map((loc: any) => ({
          id: loc.id,
          name: loc.name,
          hasImage: loc.has_image || !!existingImages[loc.id],
          conditionalNpcs: [] as string[],
          hasVariants: false,
          variantCount: 0
        }));
        
        // Fetch variant info for each location (in parallel)
        const variantPromises = locationsList.map(async (loc: LocationInfo) => {
          try {
            const variantInfo = await gameAPI.getLocationVariantInfo(worldId, loc.id);
            return {
              ...loc,
              conditionalNpcs: variantInfo.conditional_npcs || [],
              hasVariants: variantInfo.has_variants,
              variantCount: variantInfo.variant_count || 0
            };
          } catch {
            return loc;
          }
        });
        
        const locationsWithVariants = await Promise.all(variantPromises);
        setLocations(locationsWithVariants);
      } else {
        // Fallback: just use image keys as locations if world not found
        const imageKeys = Object.keys(existingImages);
        if (imageKeys.length > 0) {
          setLocations(imageKeys.map(id => ({
            id,
            name: formatLocationName(id),
            hasImage: true,
            conditionalNpcs: [],
            hasVariants: false,
            variantCount: 0
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
          hasImage: true,
          conditionalNpcs: [],
          hasVariants: false,
          variantCount: 0
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
    if (!selectedWorld || locations.length === 0) return;
    
    setIsGeneratingImages(true);
    setError(null);
    
    // Generate images one at a time for better progress feedback
    const locationsToGenerate = locations.filter(loc => !worldImages[loc.id]);
    const total = locationsToGenerate.length;
    
    if (total === 0) {
      setImageGenProgress('All images already generated!');
      setIsGeneratingImages(false);
      setTimeout(() => setImageGenProgress(''), 3000);
      return;
    }
    
    let successful = 0;
    const errors: string[] = [];
    
    for (let i = 0; i < locationsToGenerate.length; i++) {
      const loc = locationsToGenerate[i];
      setImageGenProgress(`Generating ${i + 1}/${total}: ${loc.name}...`);
      setGeneratingLocation(loc.id);
      
      try {
        const response = await gameAPI.generateSingleImage(selectedWorld, loc.id, selectedImageModel);
        if (response.success) {
          successful++;
          // Update the images list incrementally
          setWorldImages(prev => ({
            ...prev,
            [loc.id]: response.image_url || `/api/builder/${selectedWorld}/images/${loc.id}`
          }));
          setLocations(prev => prev.map(l => 
            l.id === loc.id ? { ...l, hasImage: true } : l
          ));
        } else {
          errors.push(loc.name);
        }
      } catch (err) {
        console.error(`Failed to generate image for ${loc.id}:`, err);
        errors.push(loc.name);
      }
    }
    
    setGeneratingLocation(null);
    setIsGeneratingImages(false);
    setImageGenProgress(`✓ Generated ${successful}/${total} images`);
    
    if (errors.length > 0) {
      setError(`Some images failed: ${errors.join(', ')}`);
    }
    
    // Refresh to ensure we have accurate data
    await loadWorldImages(selectedWorld);
    
    setTimeout(() => setImageGenProgress(''), 5000);
  };

  const handleGenerateSingleImage = async (locationId: string) => {
    if (!selectedWorld) return;
    
    setGeneratingLocation(locationId);
    setError(null);

    try {
      const response = await gameAPI.generateSingleImage(selectedWorld, locationId, selectedImageModel);
      
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

  const handleGenerateVariants = async (locationId: string) => {
    if (!selectedWorld) return;
    
    setGeneratingVariants(locationId);
    setError(null);

    try {
      const response = await gameAPI.generateLocationVariants(selectedWorld, locationId);
      
      if (response.success) {
        setImageGenProgress(`✓ Generated ${response.images_generated} variants for ${formatLocationName(locationId)}`);
        // Refresh to get updated variant info
        await loadWorldImages(selectedWorld);
        setTimeout(() => setImageGenProgress(''), 5000);
      } else {
        setError(`Failed to generate variants for ${locationId}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate variants');
    } finally {
      setGeneratingVariants(null);
    }
  };

  const handleGenerateAllVariants = async () => {
    if (!selectedWorld) return;
    
    const locationsNeedingVariants = locations.filter(
      loc => loc.conditionalNpcs.length > 0 && !loc.hasVariants
    );
    
    if (locationsNeedingVariants.length === 0) {
      setImageGenProgress('All variants already generated!');
      setTimeout(() => setImageGenProgress(''), 3000);
      return;
    }
    
    setIsGeneratingImages(true);
    let successful = 0;
    
    for (let i = 0; i < locationsNeedingVariants.length; i++) {
      const loc = locationsNeedingVariants[i];
      setGeneratingVariants(loc.id);
      setImageGenProgress(`Generating variants ${i + 1}/${locationsNeedingVariants.length}: ${loc.name}...`);
      
      try {
        const response = await gameAPI.generateLocationVariants(selectedWorld, loc.id);
        if (response.success) {
          successful++;
          // Update local state
          setLocations(prev => prev.map(l => 
            l.id === loc.id ? { ...l, hasVariants: true, variantCount: response.images_generated - 1 } : l
          ));
        }
      } catch (err) {
        console.error(`Failed to generate variants for ${loc.id}:`, err);
      }
    }
    
    setGeneratingVariants(null);
    setIsGeneratingImages(false);
    setImageGenProgress(`✓ Generated variants for ${successful}/${locationsNeedingVariants.length} locations`);
    
    await loadWorldImages(selectedWorld);
    setTimeout(() => setImageGenProgress(''), 5000);
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

              <div>
                <label className="block text-terminal-dim text-sm mb-2">Image Model</label>
                <div className="w-full bg-terminal-bg border border-terminal-border rounded p-3 text-terminal-text opacity-70">
                  Gemini 3 Pro Image Preview (Best Quality)
                </div>
              </div>

              <button
                onClick={handleGenerateAllImages}
                disabled={isGeneratingImages || !selectedWorld || locations.length === 0}
                className="w-full py-3 bg-terminal-highlight/20 border border-terminal-highlight 
                         text-terminal-highlight rounded font-display tracking-wider
                         hover:bg-terminal-highlight/30 transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGeneratingImages 
                  ? 'Generating...' 
                  : `Generate Missing Images (${locations.filter(l => !worldImages[l.id]).length})`}
              </button>

              {/* Variant generation button */}
              {locations.some(l => l.conditionalNpcs.length > 0 && !l.hasVariants) && (
                <button
                  onClick={handleGenerateAllVariants}
                  disabled={isGeneratingImages || generatingVariants !== null}
                  className="w-full py-3 bg-terminal-accent/20 border border-terminal-accent 
                           text-terminal-accent rounded font-display tracking-wider text-sm
                           hover:bg-terminal-accent/30 transition-colors
                           disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generatingVariants 
                    ? 'Generating Variants...' 
                    : `Generate NPC Variants (${locations.filter(l => l.conditionalNpcs.length > 0 && !l.hasVariants).length} locations)`}
                </button>
              )}

              {imageGenProgress && (
                <div className={`p-3 rounded border text-center ${
                  isGeneratingImages 
                    ? 'bg-terminal-highlight/10 border-terminal-highlight text-terminal-highlight animate-pulse' 
                    : 'bg-terminal-success/10 border-terminal-success text-terminal-success'
                }`}>
                  <p className="text-sm font-medium">{imageGenProgress}</p>
                  {isGeneratingImages && (
                    <p className="text-xs mt-1 opacity-70">
                      This may take 20-30 seconds per image...
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Location List with Image Status */}
            <div className="lg:col-span-2">
              <label className="block text-terminal-dim text-sm mb-2">
                Locations ({Object.keys(worldImages).length} images available)
              </label>
              
              <div className="bg-terminal-bg border border-terminal-border rounded p-4 max-h-64 overflow-y-auto">
                {locations.length > 0 ? (
                  <div className="grid grid-cols-1 gap-2">
                    {locations.map(loc => {
                      const isGenerating = generatingLocation === loc.id;
                      const isGeneratingVar = generatingVariants === loc.id;
                      const hasImage = !!worldImages[loc.id];
                      const needsVariants = loc.conditionalNpcs.length > 0;
                      
                      return (
                        <div 
                          key={loc.id}
                          className={`flex items-center justify-between p-2 rounded transition-colors ${
                            isGenerating || isGeneratingVar
                              ? 'bg-terminal-highlight/20 border border-terminal-highlight' 
                              : 'bg-terminal-surface/50'
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            <span className={`${
                              isGenerating 
                                ? 'text-terminal-highlight animate-pulse' 
                                : hasImage 
                                  ? 'text-terminal-success' 
                                  : 'text-terminal-dim'
                            }`}>
                              {isGenerating ? '◐' : hasImage ? '●' : '○'}
                            </span>
                            <div className="min-w-0 flex-1">
                              <span className={`text-sm truncate block ${
                                isGenerating ? 'text-terminal-highlight' : 'text-terminal-text'
                              }`}>
                                {loc.name}
                              </span>
                              {needsVariants && (
                                <span className={`text-xs ${
                                  loc.hasVariants ? 'text-terminal-success' : 'text-terminal-warning'
                                }`}>
                                  {loc.hasVariants 
                                    ? `✓ ${loc.variantCount} variant${loc.variantCount !== 1 ? 's' : ''}`
                                    : `⚠ Has conditional NPC: ${loc.conditionalNpcs.join(', ')}`
                                  }
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-1 flex-shrink-0">
                            {needsVariants ? (
                              // For locations with conditional NPCs, show a single button that regenerates all variants
                              <button
                                onClick={() => handleGenerateVariants(loc.id)}
                                disabled={isGeneratingVar || isGeneratingImages}
                                title={loc.hasVariants 
                                  ? 'Regenerate base image + all NPC variants' 
                                  : 'Generate base image + NPC variants'
                                }
                                className={`px-2 py-1 text-xs border rounded transition-colors ${
                                  isGeneratingVar
                                    ? 'border-terminal-accent text-terminal-accent animate-pulse'
                                    : loc.hasVariants
                                      ? 'border-terminal-success/50 text-terminal-success/50 hover:text-terminal-success hover:border-terminal-success'
                                      : hasImage
                                        ? 'border-terminal-warning text-terminal-warning hover:bg-terminal-warning/10'
                                        : 'border-terminal-accent text-terminal-accent hover:bg-terminal-accent/10'
                                }`}
                              >
                                {isGeneratingVar ? '⟳' : loc.hasVariants ? '↻ All' : hasImage ? '+V' : '+ All'}
                              </button>
                            ) : (
                              // For simple locations (no variants), show regular generate/regenerate button
                              <button
                                onClick={() => handleGenerateSingleImage(loc.id)}
                                disabled={isGenerating || isGeneratingImages}
                                className={`px-2 py-1 text-xs border rounded transition-colors ${
                                  isGenerating
                                    ? 'border-terminal-highlight text-terminal-highlight animate-pulse'
                                    : 'border-terminal-border text-terminal-dim hover:text-terminal-accent hover:border-terminal-accent disabled:opacity-50'
                                }`}
                              >
                                {isGenerating ? '⟳' : hasImage ? '↻' : '+'}
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
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
                {Object.entries(worldImages)
                  // Filter out variant images (they contain __with__) - only show base images
                  .filter(([locId]) => !locId.includes('__with__'))
                  .map(([locId, url]) => {
                    const location = locations.find(l => l.id === locId);
                    const hasVariants = location?.hasVariants || false;
                    const needsVariants = (location?.conditionalNpcs.length || 0) > 0;
                    const isGeneratingThis = generatingLocation === locId || generatingVariants === locId;
                    
                    return (
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
                          {hasVariants && (
                            <p className="text-terminal-success text-[10px] truncate">
                              ✓ {location?.variantCount} variant{location?.variantCount !== 1 ? 's' : ''}
                            </p>
                          )}
                        </div>
                        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          {needsVariants ? (
                            // For locations with conditional NPCs, regenerating means regenerating all variants
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleGenerateVariants(locId);
                              }}
                              disabled={isGeneratingThis}
                              title="Regenerate base + all variants"
                              className="px-2 py-1 text-xs bg-terminal-surface/80 border border-terminal-border
                                       text-terminal-dim hover:text-terminal-accent rounded transition-colors"
                            >
                              {isGeneratingThis ? '...' : '↻ Regen All'}
                            </button>
                          ) : (
                            // Simple location - just regenerate the single image
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleGenerateSingleImage(locId);
                              }}
                              disabled={isGeneratingThis}
                              className="px-2 py-1 text-xs bg-terminal-surface/80 border border-terminal-border
                                       text-terminal-dim hover:text-terminal-accent rounded transition-colors"
                            >
                              {isGeneratingThis ? '...' : '↻ Regenerate'}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
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

