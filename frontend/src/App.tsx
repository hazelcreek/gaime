import { useState } from 'react'
import { GameProvider, useGame } from './hooks/useGame'
import Terminal from './components/Terminal'
import CommandInput from './components/CommandInput'
import WorldBuilder from './components/WorldBuilder'
import SceneImage from './components/SceneImage'
import DebugPanel from './components/DebugPanel'

function App() {
  const [view, setView] = useState<'game' | 'builder'>('game')

  if (view === 'builder') {
    return (
      <div className="h-screen bg-terminal-bg flex flex-col overflow-hidden">
        {/* Header - consistent with game screen */}
        <header className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b border-terminal-border/30">
          <div className="flex items-center gap-4">
            <h1 className="font-display text-lg text-terminal-accent tracking-wider">
              GAIME
            </h1>
            <span className="text-terminal-dim/50">|</span>
            <span className="text-terminal-text text-sm font-display tracking-wide">
              World Builder
            </span>
          </div>
          <nav className="flex items-center gap-3">
            <button
              onClick={() => setView('game')}
              className="text-xs px-2 py-1 text-terminal-dim hover:text-terminal-text 
                       border border-terminal-border/50 hover:border-terminal-dim 
                       rounded transition-colors"
            >
              ← Home
            </button>
          </nav>
        </header>
        
        {/* World Builder content */}
        <div className="flex-1 overflow-hidden">
          <WorldBuilder />
        </div>
      </div>
    )
  }

  return (
    <GameProvider>
      <GameContent setView={setView} />
    </GameProvider>
  )
}

function GameContent({ setView }: { setView: (view: 'game' | 'builder') => void }) {
  const { sessionId, resetGame, worldId, worldName, startNewGame, isLoading } = useGame();
  
  return (
    <div className="h-screen bg-terminal-bg flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b border-terminal-border/30">
        <div className="flex items-center gap-4">
          <h1 className="font-display text-lg text-terminal-accent tracking-wider">
            GAIME
          </h1>
          {sessionId && worldName && (
            <>
              <span className="text-terminal-dim/50">|</span>
              <span className="text-terminal-text text-sm font-display tracking-wide">
                {worldName}
              </span>
            </>
          )}
          {!sessionId && (
            <span className="text-terminal-dim text-xs hidden sm:inline">
              AI-Powered Text Adventure
            </span>
          )}
        </div>
        <nav className="flex items-center gap-3">
          {sessionId && (
            <>
              <button
                onClick={() => startNewGame(worldId ?? undefined, undefined, worldName ?? undefined)}
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
            </>
          )}
          {!sessionId && (
            <button
              onClick={() => setView('builder')}
              className="text-xs px-2 py-1 text-terminal-dim hover:text-terminal-accent 
                       border border-terminal-border/50 hover:border-terminal-accent/50 
                       rounded transition-colors"
            >
              World Builder
            </button>
          )}
        </nav>
      </header>
      
      {/* Main game area - 2/3 image + 1/3 text on large screens, stacked on mobile */}
      <main className="flex-1 flex flex-col lg:flex-row gap-4 p-4 min-h-0 w-full overflow-hidden">
        {/* Left: Scene image (takes 2/3 width on large screens) */}
        <div className="lg:w-2/3 lg:h-full shrink-0 lg:shrink">
          <SceneImage worldId={worldId || 'cursed-manor'} />
        </div>
        
        {/* Right: Terminal + Debug + Input (takes 1/3 on large screens) */}
        <div className="flex-1 lg:w-1/3 flex flex-col min-h-0 gap-2 overflow-hidden">
          {/* Terminal - scrollable */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <Terminal />
          </div>
          
          {/* Debug Panel - collapsible */}
          <DebugPanel />
          
          {/* Command input - fixed at bottom */}
          <div className="flex-shrink-0">
            <CommandInput />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
