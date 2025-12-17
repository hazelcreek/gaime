# GAIME Documentation

Welcome to the GAIME developer documentation. This guide will help you understand the system architecture, create game worlds, and extend the engine.

## Docs Index

| File | Description |
|------|-------------|
| [VISION.md](VISION.md) | Product and technical vision (guides all development) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, and key decisions |
| [WORLD_AUTHORING.md](WORLD_AUTHORING.md) | How to create game worlds using YAML |
| [STYLE_AUTHORING.md](STYLE_AUTHORING.md) | How to create visual style presets for image generation |
| [LLM_INTEGRATION.md](LLM_INTEGRATION.md) | AI providers, prompts, and configuration |
| [API.md](API.md) | Backend endpoint documentation |

## What is GAIME?

GAIME (Game AI Master Engine) is an AI-powered text adventure engine that combines:

- **Classic text adventure mechanics**: Exploration, inventory, puzzles
- **Modern LLM capabilities**: Dynamic narrative generation, contextual dialogue
- **Hybrid world building**: Authored content + AI enhancement

## Core Concepts

### The Two AI Modes

1. **Game Master (Runtime)**
   - Processes player actions ("look around", "talk to butler")
   - Generates narrative responses
   - Updates game state (inventory, location)
   - Maintains consistency with world rules

2. **World Builder (Authoring)**
   - Generates world content from prompts
   - Creates locations, NPCs, items
   - Outputs structured YAML files

### Hybrid World Building

We don't rely entirely on AI generation. Instead:

```
                    ┌─────────────────────┐
                    │   World Author      │
                    │   (You!)            │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   YAML Files        │
                    │   - Key locations   │
                    │   - Major NPCs      │
                    │   - Plot points     │
                    │   - Constraints     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼───────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │ Runtime AI      │ │ Author AI   │ │ Static Data │
    │ - Descriptions  │ │ - Expansion │ │ - As-is     │
    │ - Dialogue      │ │ - Details   │ │             │
    │ - Atmosphere    │ │ - Ideas     │ │             │
    └─────────────────┘ └─────────────┘ └─────────────┘
```

This gives you **control** over the story while letting AI handle **detail and variety**.

## Getting Started

1. Read [Architecture](ARCHITECTURE.md) for the big picture
2. Try [World Authoring](WORLD_AUTHORING.md) to create content
3. Check [LLM Integration](LLM_INTEGRATION.md) for AI configuration
4. Use [API Reference](API.md) when building integrations

## Tech Stack Overview

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI (Python) | REST API, game logic |
| Frontend | React + TypeScript | Terminal-style UI |
| LLM | LiteLLM | Provider-agnostic AI |
| Data | YAML | World definitions |
| Styling | Tailwind CSS | UI theming |
