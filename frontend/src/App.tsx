import { useState } from 'react'
import { GameProvider, useGame } from './hooks/useGame'
import Terminal from './components/Terminal'
import Sidebar from './components/Sidebar'
import CommandInput from './components/CommandInput'
import WorldBuilder from './components/WorldBuilder'
import SceneImage from './components/SceneImage'

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
    <div className="min-h-screen bg-terminal-bg flex">
      {/* Main game area - wider to accommodate image */}
      <div className="flex-1 flex flex-col max-w-6xl mx-auto p-4">
        {/* Header */}
        <header className="mb-4 text-center flex-shrink-0">
          <h1 className="font-display text-3xl text-terminal-accent tracking-wider">
            GAIME
          </h1>
          <p className="text-terminal-dim text-sm mt-1">
            AI-Powered Text Adventure
          </p>
          <div className="mt-2 flex justify-center gap-4">
            {sessionId && (
              <button
                onClick={resetGame}
                className="text-xs text-terminal-dim hover:text-terminal-error transition-colors"
              >
                ← Return to Start
              </button>
            )}
            <button
              onClick={() => setView('builder')}
              className="text-xs text-terminal-dim hover:text-terminal-accent transition-colors"
            >
              Open World Builder →
            </button>
          </div>
        </header>
        
        {/* Game content area */}
        <div className="flex-1 flex gap-4 min-h-0">
          {/* Left column: Scene image + Terminal + Input */}
          <div className="flex-1 flex flex-col min-w-0 max-h-[calc(100vh-8rem)]">
            {/* Scene image - sticky at top, clickable to expand */}
            <div className="flex-shrink-0">
              <SceneImage worldId={worldId || 'cursed-manor'} />
            </div>
            
            {/* Terminal - scrollable */}
            <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
              <Terminal />
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
    </div>
  )
}

export default App
