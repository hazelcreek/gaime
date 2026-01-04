# Prompt Files

This directory contains LLM prompts used by the GAIME backend runtime.

## Directory Structure

```
prompts/
├── interactor/           # Interactor prompts (entity resolution)
│   └── system_prompt.txt
└── narrator/             # Narrator prompts (narrative generation)
    └── system_prompt.txt
```

> **Note**: Image generation and world builder prompts are in `gaime_builder/core/prompts/` (TUI app).

## Usage

Prompts are loaded automatically at server startup via `app.llm.prompt_loader`. They are cached in memory and support hot reloading - if you edit a prompt file, it will be automatically reloaded on the next request (checks file modification time).

### Accessing Prompts in Code

```python
from app.llm.prompt_loader import get_loader

# Get a prompt template
template = get_loader().get_prompt("narrator", "system_prompt.txt")

# Format with variables
formatted = template.format(
    world_name="My World",
    theme="gothic horror",
    # ... other variables
)
```

### Hot Reloading

For development, you can force reload prompts:

```python
from app.llm.prompt_loader import reload_prompts, reload_category

# Reload all prompts
reload_prompts()

# Reload only a specific category
reload_category("narrator")
```

## Prompt Reference

### Interactor Prompts

**`system_prompt.txt`**
- **Used in**: `app.llm.two_phase.interactor.InteractorAI`
- **Purpose**: System prompt for entity resolution and action parsing

### Narrator Prompts

**`system_prompt.txt`**
- **Used in**: `app.llm.two_phase.narrator.NarratorAI`
- **Purpose**: System prompt for generating narrative responses

## Editing Prompts

1. Edit the prompt file directly in this directory
2. The prompt loader will automatically detect changes and reload on next use
3. For immediate reload, call `reload_prompts()` or `reload_category()` in your code

## Formatting

- Prompts use Python `.format()` style placeholders: `{variable_name}`
- Use double braces `{{` and `}}` to include literal braces in the output
- Keep prompts readable with clear sections and formatting
- Comments in prompts should be clear and explain the purpose of sections
