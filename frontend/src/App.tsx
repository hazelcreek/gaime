import { useState } from 'react'
import { GameProvider } from './hooks/useGame'
import Terminal from './components/Terminal'
import Sidebar from './components/Sidebar'
import CommandInput from './components/CommandInput'
import WorldBuilder from './components/WorldBuilder'

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
      <div className="min-h-screen bg-terminal-bg flex">
        {/* Main game area */}
        <div className="flex-1 flex flex-col max-w-4xl mx-auto p-4">
          {/* Header */}
          <header className="mb-4 text-center">
            <h1 className="font-display text-3xl text-terminal-accent tracking-wider">
              GAIME
            </h1>
            <p className="text-terminal-dim text-sm mt-1">
              AI-Powered Text Adventure
            </p>
            <button
              onClick={() => setView('builder')}
              className="mt-2 text-xs text-terminal-dim hover:text-terminal-accent transition-colors"
            >
              Open World Builder →
            </button>
          </header>
          
          {/* Terminal display */}
          <div className="flex-1 flex gap-4 min-h-0 items-start">
            <div className="flex-1 flex flex-col min-w-0">
              <Terminal />
              <CommandInput />
            </div>
            
            {/* Sidebar */}
            <Sidebar />
          </div>
        </div>
      </div>
    </GameProvider>
  )
}

export default App

