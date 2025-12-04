import { useState } from 'react'
import { GameProvider, useGame } from './hooks/useGame'
import Terminal from './components/Terminal'
import Sidebar from './components/Sidebar'
import CommandInput from './components/CommandInput'
import WorldBuilder from './components/WorldBuilder'
import SceneImage from './components/SceneImage'
import DebugPanel from './components/DebugPanel'

function App() {
  const [view, setView] = useState<'game' | 'builder'>('game')

  if (view === 'builder') {
    return (
      <div>
        <WorldBuilder />
        <div className="fixed bottom-4 left-4">
          <button
            onClick={() => setView('game')}
            className="px-4 py-2 bg-terminal-surface border border-terminal-border 
                     text-terminal-dim hover:text-terminal-accent rounded transition-colors"
          >
            ← Back to Game
          </button>
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
  const { sessionId, resetGame, worldId } = useGame();
  
  return (
    <div className="h-screen bg-terminal-bg flex flex-col overflow-hidden">
      {/* Minimal inline header */}
      <header className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b border-terminal-border/30">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-lg text-terminal-accent tracking-wider">
            GAIME
          </h1>
          <span className="text-terminal-dim text-xs hidden sm:inline">
            AI-Powered Text Adventure
          </span>
        </div>
        <nav className="flex items-center gap-4">
          {sessionId && (
            <button
              onClick={resetGame}
              className="text-xs text-terminal-dim hover:text-terminal-error transition-colors"
            >
              ← Reset
            </button>
          )}
          <button
            onClick={() => setView('builder')}
            className="text-xs text-terminal-dim hover:text-terminal-accent transition-colors"
          >
            World Builder →
          </button>
        </nav>
      </header>
      
      {/* Main game area - takes all remaining height */}
      <div className="flex-1 flex gap-4 p-4 min-h-0 max-w-7xl mx-auto w-full">
        {/* Left column: Scene image + Terminal + Input */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Scene image - prominent, taller */}
          <div className="flex-shrink-0">
            <SceneImage worldId={worldId || 'cursed-manor'} />
          </div>
          
          {/* Terminal - scrollable */}
          <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
            <Terminal />
          </div>
          
          {/* Debug Panel - shows LLM interactions when enabled */}
          <div className="flex-shrink-0">
            <DebugPanel />
          </div>
          
          {/* Command input - fixed at bottom */}
          <div className="flex-shrink-0">
            <CommandInput />
          </div>
        </div>
        
        {/* Right column: Sidebar */}
        <Sidebar />
      </div>
    </div>
  )
}

export default App
