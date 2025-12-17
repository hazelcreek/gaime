/**
 * SceneImage - Displays the current location's scene image
 * Now fills the container and includes an inventory overlay badge
 */

import { useState, useEffect } from 'react';
import { useGame } from '../hooks/useGame';

interface SceneImageProps {
  onStateClick?: () => void;
}

export default function SceneImage({ onStateClick }: SceneImageProps) {
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
      setImageUrl(null);
      setIsLoading(false);
    };
    img.src = url;
  }, [currentLocation, sessionId, turnCount, flagCount]);

  // Don't render if no session
  if (!sessionId) {
    return null;
  }

  const showPlaceholder = isLoading || !imageUrl;

  return (
    <>
      {/* Scene Image Container - Full height on desktop with Ambilight effect */}
      <div
        className="relative overflow-hidden rounded-lg border border-terminal-border
                   h-64 lg:h-full lg:min-h-[400px] cursor-pointer group
                   bg-terminal-bg"
        onClick={() => setIsFullscreen(true)}
      >
        {/* Ambilight layer - blurred, scaled image creates ambient glow */}
        {imageUrl && (
          <div
            className={`absolute inset-0 transition-opacity duration-1000
                       ${showPlaceholder ? 'opacity-0' : 'opacity-100'}`}
          >
            <img
              src={imageUrl}
              alt=""
              aria-hidden="true"
              className="absolute w-[140%] h-[140%] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                         object-cover blur-[60px] saturate-[1.3] opacity-60"
            />
            {/* Darken edges for depth */}
            <div
              className="absolute inset-0"
              style={{
                background: `radial-gradient(ellipse 80% 70% at 50% 50%,
                  transparent 30%,
                  rgba(10, 10, 15, 0.7) 70%,
                  rgba(10, 10, 15, 0.95) 100%)`
              }}
            />
          </div>
        )}

        {/* Placeholder state when no image */}
        <div
          className={`absolute inset-0 z-10 flex items-center justify-center
                      transition-opacity duration-500 ${showPlaceholder ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        >
          <div className="text-center px-4">
            {isLoading ? (
              <div className="flex items-center gap-2 text-terminal-dim">
                <span className="animate-pulse">◈</span>
                <span className="font-display text-sm tracking-wider">Loading scene...</span>
              </div>
            ) : !imageUrl && (
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

        {/* Main scene image - crisp, centered with object-contain */}
        {imageUrl && (
          <img
            src={imageUrl}
            alt={`Scene: ${currentLocation || 'Unknown'}`}
            className={`absolute inset-0 w-full h-full object-contain transition-opacity duration-700 z-10
                       ${showPlaceholder ? 'opacity-0' : 'opacity-100'}`}
          />
        )}

        {/* Cinematic vignette - subtle for in-game view */}
        <div
          className="absolute inset-0 pointer-events-none z-20"
          style={{
            boxShadow: 'inset 0 0 50px 15px rgba(0, 0, 0, 0.35)',
          }}
        />

        {/* Gradient overlay for text legibility - bottom area */}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/60 via-black/20 to-transparent pointer-events-none z-20" />

        {/* Location name overlay - bottom left with cinematic treatment */}
        <div className="absolute bottom-0 left-0 right-0 p-4 pointer-events-none z-30">
          <h2 className="font-display text-xl text-terminal-accent drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] tracking-wide">
            {formatLocationName(currentLocation || 'Unknown Location')}
          </h2>
        </div>

        {/* Expand hint - shows on hover */}
        <div className="absolute top-3 right-3 text-terminal-dim/0 group-hover:text-terminal-dim/70
                        text-xs transition-all duration-300 pointer-events-none z-30">
          Click to expand
        </div>

        {/* Bottom right overlay badges - State and Inventory */}
        <div className="absolute bottom-3 right-3 z-40 flex items-end gap-2">
          {/* State Button - 36x36px square */}
          {onStateClick && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStateClick();
              }}
              className="bg-terminal-bg/90 backdrop-blur-sm border border-terminal-border
                        rounded-lg w-9 h-9 flex items-center justify-center
                        hover:bg-terminal-surface/50 hover:border-terminal-warning/50
                        text-terminal-dim hover:text-terminal-warning transition-colors"
              title="View game state"
            >
              <span className="text-sm">🔧</span>
            </button>
          )}

          {/* Inventory Badge - expands upward */}
          {inventory.length > 0 && (
            <div
              onClick={(e) => {
                e.stopPropagation();
                setInventoryExpanded(!inventoryExpanded);
              }}
            >
              <div className="bg-terminal-bg/90 backdrop-blur-sm border border-terminal-border
                            rounded-lg overflow-hidden min-w-[140px] transition-all duration-200">
                {/* Expanded items list - appears above the header */}
                {inventoryExpanded && (
                  <ul className="p-2 space-y-1 border-b border-terminal-border/50 animate-fade-in">
                    {inventory.map((item, idx) => (
                      <li key={idx} className="text-terminal-text text-sm flex items-center gap-2">
                        <span className="text-terminal-warning">•</span>
                        {formatItemName(item)}
                      </li>
                    ))}
                  </ul>
                )}

                {/* Always visible header/button - 34px so with 2px container border = 36px total */}
                <button
                  className="w-full h-[34px] px-3 flex items-center justify-between gap-3
                            hover:bg-terminal-surface/50 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    setInventoryExpanded(!inventoryExpanded);
                  }}
                >
                  <span className="text-terminal-dim text-xs uppercase tracking-wider">Inventory</span>
                  <span className="text-terminal-accent font-medium text-sm">{inventory.length}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen overlay for zoom viewing - with Ambilight effect */}
      {isFullscreen && (
        <div
          className="fixed inset-0 z-50 bg-terminal-bg flex items-center justify-center cursor-pointer overflow-hidden"
          onClick={() => setIsFullscreen(false)}
        >
          {/* Ambilight background - blurred image fills the screen */}
          {imageUrl && (
            <div className="absolute inset-0">
              <img
                src={imageUrl}
                alt=""
                aria-hidden="true"
                className="absolute w-[150%] h-[150%] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                           object-cover blur-[80px] saturate-[1.4] opacity-50"
              />
              {/* Darken edges for depth and focus on center */}
              <div
                className="absolute inset-0"
                style={{
                  background: `radial-gradient(ellipse 70% 60% at 50% 50%,
                    transparent 20%,
                    rgba(10, 10, 15, 0.6) 60%,
                    rgba(10, 10, 15, 0.9) 100%)`
                }}
              />
            </div>
          )}

          <div className="relative max-w-7xl max-h-[95vh] w-full h-full flex items-center justify-center p-4 z-10">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={`Scene: ${currentLocation || 'Unknown'}`}
                className="max-w-full max-h-full object-contain rounded-sm"
                style={{
                  boxShadow: '0 0 80px rgba(0, 0, 0, 0.6), 0 25px 50px -12px rgba(0, 0, 0, 0.7)',
                }}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <p className="font-display text-3xl text-terminal-accent">
                  {formatLocationName(currentLocation || 'Unknown')}
                </p>
              </div>
            )}

            {/* Subtle vignette for extra depth */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                boxShadow: 'inset 0 0 150px 50px rgba(0, 0, 0, 0.4)',
              }}
            />

            {/* Close hint - top right */}
            <div className="absolute top-6 right-6 text-terminal-dim/60 text-sm tracking-wide">
              Press anywhere to close
            </div>

            {/* Location info - centered bottom */}
            <div className="absolute bottom-0 left-0 right-0 p-8 bg-gradient-to-t from-black via-black/60 to-transparent">
              <h2 className="font-display text-3xl text-terminal-accent text-center tracking-wide drop-shadow-[0_2px_12px_rgba(0,0,0,0.9)]">
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
