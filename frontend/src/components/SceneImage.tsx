/**
 * SceneImage - Displays the current location's scene image
 * Now fills the container and includes an inventory overlay badge
 */

import { useState, useEffect } from 'react';
import { useGame } from '../hooks/useGame';

interface SceneImageProps {
  worldId?: string;
}

export default function SceneImage({ worldId = 'cursed-manor' }: SceneImageProps) {
  const { gameState, sessionId } = useGame();
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [inventoryExpanded, setInventoryExpanded] = useState(false);

  const currentLocation = gameState?.current_location;
  const inventory = gameState?.inventory ?? [];

  // Get flag count to detect when NPCs might have appeared/disappeared
  const flagCount = gameState?.flags ? Object.keys(gameState.flags).length : 0;
  const turnCount = gameState?.turn_count ?? 0;
  
  useEffect(() => {
    if (!currentLocation || !sessionId) {
      setImageUrl(null);
      return;
    }

    // Use the state-aware game endpoint to get the correct image variant
    const cacheBuster = `t=${turnCount}&f=${flagCount}`;
    const url = `/api/game/image/${sessionId}/${currentLocation}?${cacheBuster}`;
    
    setIsLoading(true);
    
    const img = new Image();
    img.onload = () => {
      setImageUrl(url);
      setIsLoading(false);
    };
    img.onerror = () => {
      // Fallback to static builder image if game endpoint fails
      const fallbackUrl = `/api/builder/${worldId}/images/${currentLocation}`;
      const fallbackImg = new Image();
      fallbackImg.onload = () => {
        setImageUrl(fallbackUrl);
        setIsLoading(false);
      };
      fallbackImg.onerror = () => {
        setImageUrl(null);
        setIsLoading(false);
      };
      fallbackImg.src = fallbackUrl;
    };
    img.src = url;
  }, [currentLocation, worldId, sessionId, turnCount, flagCount]);

  // Don't render if no session
  if (!sessionId) {
    return null;
  }

  const showPlaceholder = isLoading || !imageUrl;

  return (
    <>
      {/* Scene Image Container - Full height on desktop */}
      <div 
        className="relative overflow-hidden rounded-lg border border-terminal-border 
                   h-64 lg:h-full lg:min-h-[400px] cursor-pointer group"
        onClick={() => setIsFullscreen(true)}
      >
        {/* Gradient background for atmosphere when no image */}
        <div 
          className={`absolute inset-0 bg-gradient-to-b from-terminal-surface via-terminal-bg to-terminal-surface
                      transition-opacity duration-500 ${showPlaceholder ? 'opacity-100' : 'opacity-0'}`}
        >
          {/* Atmospheric pattern overlay */}
          <div className="absolute inset-0 opacity-20"
               style={{
                 backgroundImage: `radial-gradient(circle at 50% 50%, rgba(125, 211, 252, 0.1) 0%, transparent 50%)`,
               }}
          />
          
          {/* Location name when no image */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center px-4">
              {isLoading ? (
                <div className="flex items-center gap-2 text-terminal-dim">
                  <span className="animate-pulse">◈</span>
                  <span className="font-display text-sm tracking-wider">Loading scene...</span>
                </div>
              ) : (
                <>
                  <p className="font-display text-2xl text-terminal-accent mb-2 tracking-wide">
                    {formatLocationName(currentLocation || 'Unknown Location')}
                  </p>
                  <p className="text-terminal-dim text-sm italic">
                    No scene image available
                  </p>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Actual scene image */}
        {imageUrl && (
          <img
            src={imageUrl}
            alt={`Scene: ${currentLocation || 'Unknown'}`}
            className={`w-full h-full object-cover transition-opacity duration-700
                       ${showPlaceholder ? 'opacity-0' : 'opacity-100'}`}
          />
        )}

        {/* Gradient overlay for text legibility */}
        <div className="absolute inset-0 bg-gradient-to-t from-terminal-bg/80 via-transparent to-transparent pointer-events-none" />

        {/* Location name overlay - bottom left */}
        <div className="absolute bottom-0 left-0 right-0 p-4 pointer-events-none">
          <h2 className="font-display text-xl text-terminal-accent drop-shadow-lg tracking-wide">
            {formatLocationName(currentLocation || 'Unknown Location')}
          </h2>
        </div>

        {/* Expand hint - shows on hover */}
        <div className="absolute top-3 right-3 text-terminal-dim/0 group-hover:text-terminal-dim/70 
                        text-xs transition-all duration-300 pointer-events-none">
          Click to expand
        </div>

        {/* Vignette effect for atmosphere */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            boxShadow: 'inset 0 0 80px rgba(0, 0, 0, 0.5)',
          }}
        />

        {/* Inventory Badge Overlay - bottom right */}
        {inventory.length > 0 && (
          <div 
            className="absolute bottom-3 right-3 z-10"
            onClick={(e) => {
              e.stopPropagation();
              setInventoryExpanded(!inventoryExpanded);
            }}
          >
            {inventoryExpanded ? (
              // Expanded inventory list
              <div className="bg-terminal-bg/90 backdrop-blur-sm border border-terminal-border 
                            rounded-lg p-3 min-w-[160px] animate-fade-in">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-terminal-dim text-xs uppercase tracking-wider">Inventory</span>
                  <button 
                    className="text-terminal-dim hover:text-terminal-text text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      setInventoryExpanded(false);
                    }}
                  >
                    ✕
                  </button>
                </div>
                <ul className="space-y-1">
                  {inventory.map((item, idx) => (
                    <li key={idx} className="text-terminal-text text-sm flex items-center gap-2">
                      <span className="text-terminal-warning">•</span>
                      {formatItemName(item)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              // Collapsed badge
              <button 
                className="bg-terminal-bg/80 backdrop-blur-sm border border-terminal-border 
                          hover:border-terminal-accent/50 rounded-lg px-3 py-2
                          flex items-center gap-2 transition-colors"
              >
                <span className="text-base">🎒</span>
                <span className="text-terminal-accent font-medium text-sm">{inventory.length}</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Fullscreen overlay for zoom viewing */}
      {isFullscreen && (
        <div 
          className="fixed inset-0 z-50 bg-terminal-bg/95 backdrop-blur-sm 
                     flex items-center justify-center p-8 cursor-pointer"
          onClick={() => setIsFullscreen(false)}
        >
          <div className="relative max-w-6xl max-h-[90vh] w-full h-full rounded-lg overflow-hidden border border-terminal-border">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={`Scene: ${currentLocation || 'Unknown'}`}
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-terminal-surface">
                <p className="font-display text-2xl text-terminal-accent">
                  {formatLocationName(currentLocation || 'Unknown')}
                </p>
              </div>
            )}
            
            {/* Close hint */}
            <div className="absolute top-4 right-4 text-terminal-dim text-sm">
              Click anywhere to close
            </div>
            
            {/* Location info */}
            <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-terminal-bg to-transparent">
              <h2 className="font-display text-3xl text-terminal-accent tracking-wide">
                {formatLocationName(currentLocation || 'Unknown')}
              </h2>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function formatLocationName(location: string): string {
  return location
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatItemName(item: string): string {
  return item
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
