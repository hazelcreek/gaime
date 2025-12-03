/**
 * SceneImage - Displays the current location's scene image
 * Stays fixed/prominent at the top of the game area for immersion
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
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const currentLocation = gameState?.current_location;

  useEffect(() => {
    if (!currentLocation || !sessionId) {
      setImageUrl(null);
      return;
    }

    // Construct the image URL for the current location
    const url = `/api/builder/${worldId}/images/${currentLocation}`;
    
    // Check if image exists by attempting to load it
    setIsLoading(true);
    setError(null);
    
    const img = new Image();
    img.onload = () => {
      setImageUrl(url);
      setIsLoading(false);
    };
    img.onerror = () => {
      setImageUrl(null);
      setIsLoading(false);
      // Don't show error - just gracefully hide the image area
    };
    img.src = url;
  }, [currentLocation, worldId, sessionId]);

  // Don't render if no session or no image available
  if (!sessionId) {
    return null;
  }

  // Placeholder gradient for when image is loading or unavailable
  const showPlaceholder = isLoading || !imageUrl;

  return (
    <>
      {/* Scene Image Container - Prominent at top, always visible */}
      <div 
        className={`relative overflow-hidden rounded-lg border border-terminal-border 
                    transition-all duration-500 ease-out mb-3 cursor-pointer
                    ${isExpanded ? 'h-[60vh]' : 'h-72'}`}
        onClick={() => setIsExpanded(!isExpanded)}
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
                    {gameState?.current_location 
                      ? formatLocationName(gameState.current_location)
                      : 'Unknown Location'}
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
            alt={`Scene: ${gameState?.current_location || 'Unknown'}`}
            className={`w-full h-full object-cover transition-opacity duration-700
                       ${showPlaceholder ? 'opacity-0' : 'opacity-100'}`}
          />
        )}

        {/* Gradient overlay for text legibility */}
        <div className="absolute inset-0 bg-gradient-to-t from-terminal-bg/80 via-transparent to-transparent pointer-events-none" />

        {/* Location name overlay */}
        <div className="absolute bottom-0 left-0 right-0 p-4 pointer-events-none">
          <h2 className="font-display text-xl text-terminal-accent drop-shadow-lg tracking-wide">
            {gameState?.current_location 
              ? formatLocationName(gameState.current_location)
              : 'Unknown Location'}
          </h2>
        </div>

        {/* Expand/collapse indicator */}
        <div className="absolute top-2 right-2 text-terminal-dim/50 text-xs pointer-events-none">
          {isExpanded ? '▲ collapse' : '▼ expand'}
        </div>

        {/* Vignette effect for atmosphere */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            boxShadow: 'inset 0 0 80px rgba(0, 0, 0, 0.5)',
          }}
        />
      </div>

      {/* Expanded overlay for full-screen viewing */}
      {isExpanded && (
        <div 
          className="fixed inset-0 z-50 bg-terminal-bg/95 backdrop-blur-sm flex items-center justify-center p-8 cursor-pointer"
          onClick={() => setIsExpanded(false)}
        >
          <div className="relative max-w-6xl max-h-[85vh] w-full h-full rounded-lg overflow-hidden border border-terminal-border">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={`Scene: ${gameState?.current_location || 'Unknown'}`}
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-terminal-surface">
                <p className="font-display text-2xl text-terminal-accent">
                  {formatLocationName(gameState?.current_location || 'Unknown')}
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
                {formatLocationName(gameState?.current_location || 'Unknown')}
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
