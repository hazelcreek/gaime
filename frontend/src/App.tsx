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
        
        {/* World Builder content - scrollable */}
        <div className="flex-1 overflow-y-auto">
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
      
      {/* Main game area */}
      <main className="flex-1 flex flex-col lg:flex-row gap-4 p-4 min-h-0 w-full overflow-hidden">
        {/* Scene image - only show when in game */}
        {sessionId && (
          <div className="lg:w-2/3 lg:h-full shrink-0 lg:shrink">
            <SceneImage worldId={worldId || 'cursed-manor'} />
          </div>
        )}
        
        {/* Terminal + Debug + Input */}
        <div className={`flex-1 flex flex-col min-h-0 gap-2 overflow-hidden ${sessionId ? 'lg:w-1/3' : 'w-full'}`}>
          {/* Terminal - scrollable */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <Terminal />
          </div>
          
          {/* Debug Panel - only in game */}
          {sessionId && <DebugPanel />}
          
          {/* Command input - only in game */}
          {sessionId && (
            <div className="flex-shrink-0">
              <CommandInput />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
