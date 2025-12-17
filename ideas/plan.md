# AI Text Adventure Prototype - Implementation Plan

## Vision

Build a browser-based text adventure game where player input is processed by an LLM acting as a dynamic game master. The AI maintains game state (inventory, location, flags) while generating rich, immersive narrative responses.

## Architecture

```
┌────────────────────┐      HTTP/JSON      ┌────────────────────┐
│   React Frontend   │ ◄──────────────────► │   Python Backend   │
│   (Vite + React)   │                      │     (FastAPI)      │
│                    │                      │                    │
│  - Terminal UI     │                      │  - Game engine     │
│  - State display   │                      │  - LLM integration │
│  - World builder   │                      │  - World loader    │
└────────────────────┘                      └────────────────────┘
                                                     │
                                   ┌─────────────────┼─────────────────┐
                                   ▼                 ▼                 ▼
                               Gemini            OpenAI            Ollama
                              (default)        (optional)        (optional)
```

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Frontend | Vite + React + TypeScript | Fast dev, simple setup |
| Styling | Tailwind CSS | Rapid UI development |
| Backend | FastAPI + Python 3.11+ | Excellent for AI/LLM work |
| LLM | LiteLLM + Gemini | Free tier for dev, easy provider switch |
| World Data | YAML files | Human-readable, version-controlled |
| Docs | Markdown in `/docs` | Developer onboarding |

## Project Structure

```
gaime/
├── docs/                           # Developer documentation
│   ├── README.md                   # Project overview & quick start
│   ├── ARCHITECTURE.md             # System design & data flow
│   ├── WORLD_AUTHORING.md          # How to create game worlds
│   ├── LLM_INTEGRATION.md          # AI prompts & provider setup
│   └── API.md                      # Backend API reference
│
├── backend/                        # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── api/
│   │   │   ├── game.py             # Game action endpoints
│   │   │   └── builder.py          # World builder endpoints
│   │   ├── engine/
│   │   │   ├── state.py            # Game state management
│   │   │   ├── world.py            # World loader (YAML)
│   │   │   └── actions.py          # Action processing
│   │   ├── llm/
│   │   │   ├── client.py           # LiteLLM setup
│   │   │   ├── game_master.py      # Runtime prompts
│   │   │   └── world_builder.py    # Generation prompts
│   │   └── models/
│   │       ├── game.py             # Pydantic models
│   │       └── world.py            # World schema models
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/                       # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Terminal.tsx        # Narrative display
│   │   │   ├── CommandInput.tsx    # Player input
│   │   │   ├── Sidebar.tsx         # Inventory/location
│   │   │   └── WorldBuilder.tsx    # Builder UI
│   │   ├── hooks/
│   │   │   └── useGame.ts          # Game state hook
│   │   ├── api/
│   │   │   └── client.ts           # Backend API client
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── worlds/                         # Game world definitions
│   └── cursed-manor/               # Example world
│       ├── world.yaml
│       ├── locations.yaml
│       ├── npcs.yaml
│       └── items.yaml
│
├── .env.example                    # API keys template
├── .cursorrules                    # AI assistant context
└── README.md                       # Quick start
```

## World-Building System

### Philosophy: Hybrid Authoring

Define the **skeleton** (key locations, major NPCs, plot constraints), and the AI:
- **At author time**: Helps generate and expand world content
- **At runtime**: Fills in narrative details, dialogue, atmosphere

### World Definition Schema

**world.yaml** - Theme, premise, player setup, global constraints
```yaml
name: "The Cursed Manor"
theme: "Victorian gothic horror"
premise: "A scholar seeks shelter in a mysterious mansion..."
constraints:
  - "The basement requires the iron key"
  - "Jenkins never reveals secrets directly"
```

**locations.yaml** - Rooms with atmosphere hints, exits, interactions
```yaml
library:
  atmosphere: "ancient books, cold draft, dust motes in moonlight"
  exits: { south: entrance_hall, hidden: secret_passage }
  items: [dusty_tome]
  interactions:
    pull_red_book: { reveals: secret_passage }
```

**npcs.yaml** - Characters with personality, knowledge, behavior
```yaml
butler_jenkins:
  personality: [formal, secretive, guilt-ridden]
  speech_style: "Victorian formal, hints and deflections"
  knowledge: ["knows the curse truth", "witnessed the tragedy"]
```

**items.yaml** - Objects with descriptions, uses, puzzle connections
```yaml
iron_key:
  portable: true
  unlocks: basement_door
  found_in: library  # hidden until puzzle solved
```

## Key Backend Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/game/new` | Start new game, returns initial state |
| `POST /api/game/action` | Process player action, returns narrative + state |
| `GET /api/game/state` | Get current game state |
| `POST /api/builder/generate` | AI-generate world from prompt |
| `GET /api/worlds` | List available worlds |

## Implementation Phases

### Phase 1: Foundation
- [x] Project planning and architecture design
- [ ] Initialize backend (FastAPI) and frontend (Vite + React)
- [ ] Create documentation skeleton
- [ ] Set up environment configuration

### Phase 2: World System
- [ ] Define Pydantic models for world schema
- [ ] Build YAML world loader
- [ ] Create example "cursed-manor" world

### Phase 3: Game Engine
- [ ] Implement game state management
- [ ] Build action processing logic
- [ ] Create game API endpoints

### Phase 4: LLM Integration
- [ ] Set up LiteLLM with Gemini
- [ ] Design game master system prompts
- [ ] Implement structured response parsing

### Phase 5: Frontend
- [ ] Build terminal-style UI component
- [ ] Create command input with history
- [x] Add sidebar for inventory/location
- [ ] Connect to backend API

### Phase 6: World Builder
- [ ] Design world generation prompts
- [ ] Build generation API endpoint
- [ ] Create builder UI

### Phase 7: Polish
- [ ] Add localStorage persistence
- [ ] Improve UI with typing effects
- [ ] Complete documentation
- [ ] Create demo scenario

## Success Criteria

1. Player can start a new game and explore the example world
2. AI generates contextually appropriate narrative responses
3. Inventory, location, and flags update correctly
4. World builder can generate new worlds from prompts
5. Documentation enables new developers to contribute
