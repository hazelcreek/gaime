/**
 * MainMenu - World selection and game start screen
 * Features a gothic gate background with a left sidebar for UI elements
 */

import { useState, useEffect } from 'react';
import { gameAPI, WorldInfo } from '../api/client';

interface MainMenuProps {
  onStartGame: (worldId: string, playerName: string, worldName?: string) => void;
  isLoading: boolean;
}

export default function MainMenu({ onStartGame, isLoading }: MainMenuProps) {
  const [worlds, setWorlds] = useState<WorldInfo[]>([]);
  const [selectedWorld, setSelectedWorld] = useState<string>('');
  const [loadingWorlds, setLoadingWorlds] = useState(true);

  // Load available worlds on mount
  useEffect(() => {
    setLoadingWorlds(true);
    gameAPI.listWorlds()
      .then(({ worlds }) => {
        setWorlds(worlds);
        if (worlds.length > 0 && !selectedWorld) {
          setSelectedWorld(worlds[0].id);
        }
      })
      .catch(() => {
        // Fallback to default world
        setWorlds([{ id: 'cursed-manor', name: 'The Cursed Manor', theme: 'Victorian gothic horror' }]);
        setSelectedWorld('cursed-manor');
      })
      .finally(() => setLoadingWorlds(false));
  }, []);

  const handleStartGame = () => {
    if (selectedWorld) {
      const selectedWorldInfo = worlds.find(w => w.id === selectedWorld);
      onStartGame(selectedWorld, 'Traveler', selectedWorldInfo?.name);
    }
  };

  const selectedWorldInfo = worlds.find(w => w.id === selectedWorld);

  return (
    <div 
      className="h-full w-full bg-cover bg-center bg-no-repeat relative"
      style={{ backgroundImage: "url('/menu-bg.jpg')" }}
    >
      {/* Dark overlay for better text readability */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent" />
      
      {/* Content container - left sidebar layout */}
      <div className="relative h-full flex">
        {/* Left sidebar panel */}
        <div className="w-full max-w-md lg:max-w-lg h-full flex flex-col p-6 lg:p-8">
          {/* Greeting */}
          <div className="mb-6">
            <h2 className="font-display text-2xl lg:text-3xl text-terminal-accent mb-2 tracking-wide">
              Hello, adventurer
            </h2>
            <p className="text-terminal-dim text-sm leading-relaxed">
              Choose your world and step through the gate.
            </p>
          </div>

          {loadingWorlds ? (
            <div className="text-terminal-dim animate-pulse">Loading worlds...</div>
          ) : (
            <div className="flex-1 flex flex-col min-h-0 gap-4">
              {/* World Selection Grid */}
              <div className="flex-shrink-0">
                <label className="block text-terminal-dim text-xs mb-2 uppercase tracking-wider">
                  Select World
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1 scrollbar-thin">
                  {worlds.map((world) => (
                    <button
                      key={world.id}
                      onClick={() => setSelectedWorld(world.id)}
                      className={`text-left p-3 rounded-lg border transition-all backdrop-blur-sm ${
                        selectedWorld === world.id
                          ? 'bg-terminal-accent/20 border-terminal-accent shadow-lg shadow-terminal-accent/10'
                          : 'bg-terminal-bg/60 border-terminal-border/50 hover:border-terminal-dim hover:bg-terminal-bg/80'
                      }`}
                    >
                      <div className="font-display text-sm text-terminal-accent">
                        {world.name}
                      </div>
                      <div className="text-terminal-dim text-xs mt-0.5">
                        {world.theme}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* World Description - Full text, scrollable if needed */}
              {selectedWorldInfo?.description && (
                <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
                  <label className="block text-terminal-dim text-xs mb-2 uppercase tracking-wider flex-shrink-0">
                    About This World
                  </label>
                  <div className="flex-1 overflow-y-auto bg-terminal-bg/50 backdrop-blur-sm rounded-lg border border-terminal-border/30 p-4">
                    <p className="text-terminal-text text-sm leading-relaxed">
                      {selectedWorldInfo.description}
                    </p>
                  </div>
                </div>
              )}

              {/* Start Button */}
              <div className="flex-shrink-0 pt-2">
                <button
                  onClick={handleStartGame}
                  disabled={isLoading || !selectedWorld}
                  className="w-full px-6 py-3 bg-terminal-accent/20 border-2 border-terminal-accent 
                           text-terminal-accent rounded-lg hover:bg-terminal-accent/30 
                           transition-all disabled:opacity-50 disabled:cursor-not-allowed
                           font-display tracking-widest text-sm uppercase
                           shadow-lg shadow-terminal-accent/20 hover:shadow-terminal-accent/30"
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="animate-pulse">●</span>
                      Preparing...
                    </span>
                  ) : (
                    'Begin Adventure'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right side - empty to show the gate */}
        <div className="flex-1" />
      </div>
    </div>
  );
}

