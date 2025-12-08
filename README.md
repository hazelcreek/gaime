# GAIME - AI Text Adventure Engine

An AI-powered text adventure game engine that combines classic text-based gameplay with modern LLM capabilities. The AI acts as a dynamic game master, generating rich narrative responses while maintaining game state consistency.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Gemini API key (get one at [aistudio.google.com](https://aistudio.google.com))

### Setup

1. **Clone and configure environment**

   ```bash
   # Copy environment template
   cp env.example .env
   
   # Edit .env and add your Gemini API key
   # GEMINI_API_KEY=your_key_here
   ```

2. **Start the backend**

   ```bash
   cd backend
   
   # Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run the server
   uvicorn app.main:app --reload
   ```

3. **Start the frontend** (in a new terminal)

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Play!** Open [http://localhost:5173](http://localhost:5173)

## Project Structure

```
gaime/
├── backend/          # Python FastAPI server
├── frontend/         # React + TypeScript UI
├── worlds/           # YAML game world definitions
├── docs/             # Developer documentation
└── ideas/            # Future plans and feature concepts
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and data flow
- [World Authoring](docs/WORLD_AUTHORING.md) - How to create game worlds
- [LLM Integration](docs/LLM_INTEGRATION.md) - AI prompts and provider setup
- [API Reference](docs/API.md) - Backend endpoint documentation

### Docs site (GitHub Pages)

- Source: all Markdown in `docs/`, `ideas/`, and the repository `README.md`
- Build: automated on pushes to `main` via `.github/workflows/docs.yml`
- Preview locally:
  ```bash
  pip install -r requirements-docs.txt
  mkdocs serve
  ```

## Features

- **AI Game Master**: LLM generates contextual narrative responses
- **Hybrid World Building**: Define key elements in YAML, AI fills in details
- **Provider Agnostic**: Switch between Gemini, OpenAI, Anthropic, or local models
- **Light Game Mechanics**: Track inventory, location, flags, and NPC trust
- **Victory Conditions**: Define win states with location, flag, and item requirements
- **AI World Builder**: Generate complete game worlds from text descriptions

## License

MIT
