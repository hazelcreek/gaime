# Prompt Files

This directory contains all LLM prompts used by GAIME, organized by component.

## Directory Structure

```
prompts/
├── game_master/          # Game engine prompts
│   ├── system_prompt.txt      # Main system prompt for game master
│   └── opening_prompt.txt      # Prompt for generating opening narrative
├── world_builder/        # World builder prompts
│   ├── world_builder_prompt.txt  # Main prompt for world generation
│   └── system_message.txt         # System message for world builder
└── image_generator/      # Image generation prompts
    ├── image_prompt_template.txt      # Template for scene image generation
    ├── edit_prompt_template.txt       # Template for editing images (NPC variants)
    └── interactive_elements_section.txt  # Template section for interactive elements
```

## Usage

Prompts are loaded automatically at server startup via `app.llm.prompt_loader`. They are cached in memory and support hot reloading - if you edit a prompt file, it will be automatically reloaded on the next request (checks file modification time).

### Accessing Prompts in Code

```python
from app.llm.prompt_loader import get_loader

# Get a prompt template
template = get_loader().get_prompt("game_master", "system_prompt.txt")

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
reload_category("game_master")
```

## Prompt Reference

### Game Master Prompts

**`system_prompt.txt`**
- **Used in**: `app.llm.game_master.GameMaster._build_system_prompt()`
- **Purpose**: Main system prompt sent to LLM for all game actions
- **Variables**: `world_name`, `theme`, `tone`, `starting_situation`, `current_location`, `location_name`, `inventory`, `discovered`, `flags`, `recent_context`, `npc_relationships`, `discoveries`, `location_atmosphere`, `exits`, `npcs_here`, `items_here_detailed`, `item_details`, `location_details`, `constraints`, `npc_knowledge`

**`opening_prompt.txt`**
- **Used in**: `app.llm.game_master.GameMaster.generate_opening()`
- **Purpose**: User prompt for generating the opening narrative
- **Variables**: `location_name`, `premise`, `starting_situation`

### World Builder Prompts

**`world_builder_prompt.txt`**
- **Used in**: `app.llm.world_builder.WorldBuilder.generate()`
- **Purpose**: Main prompt for generating world content from user description
- **Variables**: `theme`, `num_locations`, `num_npcs`, `prompt`

**`system_message.txt`**
- **Used in**: `app.llm.world_builder.WorldBuilder.generate()`
- **Purpose**: System message sent to LLM for world building
- **Variables**: None (static message)

### Image Generator Prompts

**`image_prompt_template.txt`**
- **Used in**: `app.llm.image_generator.get_image_prompt()`
- **Purpose**: Template for generating scene images for locations
- **Variables**: `location_name`, `theme`, `tone`, `atmosphere`, `interactive_section`

**`edit_prompt_template.txt`**
- **Used in**: `app.llm.image_generator.get_edit_prompt()`
- **Purpose**: Template for editing base images to add NPCs (for variants)
- **Variables**: `location_name`, `theme`, `tone`, `npcs_text`

**`interactive_elements_section.txt`**
- **Used in**: `app.llm.image_generator.get_image_prompt()`
- **Purpose**: Template section describing exits, items, and NPCs in images
- **Variables**: `interactive_elements`

## Editing Prompts

1. Edit the prompt file directly in this directory
2. The prompt loader will automatically detect changes and reload on next use
3. For immediate reload, call `reload_prompts()` or `reload_category()` in your code

## Formatting

- Prompts use Python `.format()` style placeholders: `{variable_name}`
- Use double braces `{{` and `}}` to include literal braces in the output
- Keep prompts readable with clear sections and formatting
- Comments in prompts should be clear and explain the purpose of sections
