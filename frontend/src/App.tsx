import { useState, useEffect } from 'react'
import { GameProvider, useGame } from './hooks/useGame'
import { useAudio } from './hooks/useAudio'
import Terminal from './components/Terminal'
import CommandInput from './components/CommandInput'
import SceneImage from './components/SceneImage'
import StateOverlay from './components/StateOverlay'
import MainMenu from './components/MainMenu'

function App() {
  return (
    <GameProvider>
      <GameContent />
    </GameProvider>
  )
}

function GameContent() {
  const { sessionId, resetGame, worldId, worldName, startNewGame, isLoading, gameState, locationDebug, fetchLocationDebug } = useGame();
  const { isMuted, isReady, toggleMute, playMenuMusic, stopMenuMusic } = useAudio();
  const [stateOverlayOpen, setStateOverlayOpen] = useState(false);

  // Play menu music when on main menu and audio is ready, stop when game starts
  useEffect(() => {
    if (!sessionId && isReady) {
      playMenuMusic();
    } else if (sessionId) {
      stopMenuMusic();
    }
  }, [sessionId, isReady, playMenuMusic, stopMenuMusic]);

  // Close overlay on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && stateOverlayOpen) {
        setStateOverlayOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [stateOverlayOpen]);

  // Show main menu when no active session
  if (!sessionId) {
    return (
      <div className="h-screen bg-terminal-bg flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b border-terminal-border/30 bg-terminal-bg/80 backdrop-blur-sm z-10">
          <div className="flex items-center gap-4">
            <h1 className="font-display text-lg text-terminal-accent tracking-wider">
              GAIME
            </h1>
            <span className="text-terminal-dim text-xs hidden sm:inline">
              AI-Powered Text Adventure
            </span>
          </div>
          <nav className="flex items-center gap-3">
            <button
              onClick={toggleMute}
              className="p-1.5 text-terminal-dim hover:text-terminal-accent
                       transition-colors"
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M11 5L6 9H2v6h4l5 4V5z" />
                  <line x1="22" y1="9" x2="16" y2="15" />
                  <line x1="16" y1="9" x2="22" y2="15" />
                </svg>
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M11 5L6 9H2v6h4l5 4V5z" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                </svg>
              )}
            </button>
          </nav>
        </header>

        {/* Main Menu */}
        <main className="flex-1 min-h-0 overflow-hidden">
          <MainMenu
            onStartGame={startNewGame}
            isLoading={isLoading}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="h-screen bg-terminal-bg flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b border-terminal-border/30">
        <div className="flex items-center gap-4">
          <h1 className="font-display text-lg text-terminal-accent tracking-wider">
            GAIME
          </h1>
          {worldName && (
            <>
              <span className="text-terminal-dim/50">|</span>
              <span className="text-terminal-text text-sm font-display tracking-wide">
                {worldName}
              </span>
            </>
          )}
        </div>
        <nav className="flex items-center gap-3">
          <button
            onClick={() => startNewGame(worldId ?? undefined, worldName ?? undefined)}
            disabled={isLoading}
            className="text-xs px-2 py-1 text-terminal-dim hover:text-terminal-accent
                     border border-terminal-border/50 hover:border-terminal-accent/50
                     rounded transition-colors disabled:opacity-50"
          >
            New Game
          </button>
          <button
            onClick={resetGame}
            className="text-xs px-2 py-1 text-terminal-dim hover:text-terminal-text
                     border border-terminal-border/50 hover:border-terminal-dim
                     rounded transition-colors"
          >
            ← Home
          </button>
        </nav>
      </header>

      {/* Main game area */}
      <main className="flex-1 flex flex-col lg:flex-row gap-4 p-4 min-h-0 w-full overflow-hidden">
        {/* Scene image */}
        <div className="lg:w-2/3 lg:h-full shrink-0 lg:shrink">
          <SceneImage
            onStateClick={() => setStateOverlayOpen(true)}
          />
        </div>

        {/* Terminal + Input */}
        <div className="flex-1 flex flex-col min-h-0 gap-2 overflow-hidden lg:w-1/3">
          {/* Terminal - scrollable */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <Terminal />
          </div>

          {/* Command input */}
          <div className="flex-shrink-0">
            <CommandInput />
          </div>
        </div>
      </main>

      {/* State Overlay */}
      {stateOverlayOpen && gameState && (
        <StateOverlay
          gameState={gameState}
          locationDebug={locationDebug}
          onClose={() => setStateOverlayOpen(false)}
          onFetchDebug={fetchLocationDebug}
        />
      )}
    </div>
  )
}

export default App
