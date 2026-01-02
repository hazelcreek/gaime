# LLM Integration

This document covers how GAIME integrates with Large Language Models, including configuration, prompts, and provider setup.

## Supported Providers

GAIME uses [LiteLLM](https://github.com/BerriAI/litellm) for provider-agnostic LLM calls.

| Provider | Models | Setup |
|----------|--------|-------|
| **Google Gemini** | gemini-3-pro-preview (default), gemini-1.5-flash, gemini-1.5-pro | API key from [aistudio.google.com](https://aistudio.google.com) |
| **OpenAI** | gpt-4o, gpt-4o-mini | API key from [platform.openai.com](https://platform.openai.com) |
| **Anthropic** | claude-3-5-sonnet, claude-3-haiku | API key from [console.anthropic.com](https://console.anthropic.com) |
| **Ollama** | llama3.1, mistral, etc. | Local install from [ollama.ai](https://ollama.ai) |

## Configuration

Set these environment variables in your `.env` file:

```bash
# Provider selection
LLM_PROVIDER=gemini  # gemini, openai, anthropic, ollama

# API Keys (set the one for your provider)
GEMINI_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here

# Model selection
LLM_MODEL=gemini-3-pro-preview

# For Ollama (local)
# OLLAMA_BASE_URL=http://localhost:11434
```

## How It Works

### LLM Client Setup

```python
# backend/app/llm/client.py
from litellm import completion

def get_completion(messages: list, model: str = None) -> str:
    """Get completion from configured LLM provider."""
    model = model or get_model_string()

    response = completion(
        model=model,
        messages=messages,
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    return response.choices[0].message.content
```

### Model String Format

LiteLLM uses prefixed model strings:

| Provider | Format | Example |
|----------|--------|---------|
| Gemini | `gemini/model-name` | `gemini/gemini-3-pro-preview` |
| OpenAI | `model-name` | `gpt-4o` |
| Anthropic | `anthropic/model-name` | `anthropic/claude-3-5-sonnet-20241022` |
| Ollama | `ollama/model-name` | `ollama/llama3.1` |

## Prompt Architecture

### Prompt Organization

All prompts are stored as text files in `backend/app/llm/prompts/` and organized by component:

```
backend/app/llm/prompts/
├── game_master/          # Classic game engine prompts
│   ├── system_prompt.txt      # Main system prompt for game master
│   └── opening_prompt.txt      # Prompt for generating opening narrative
├── narrator/             # Two-phase engine: narrative generation
│   └── system_prompt.txt      # Narrator prompt for prose generation
├── interactor/           # Two-phase engine: action parsing
│   └── system_prompt.txt      # Interactor prompt for entity resolution
└── image_generator/      # Image generation prompts
    ├── image_prompt_template.txt      # Template for scene image generation
    ├── edit_prompt_template.txt       # Template for editing images (NPC variants)
    └── interactive_elements_section.txt  # Template section for interactive elements

gaime_builder/core/prompts/
└── world_builder/        # World builder prompts (used by TUI)
    ├── world_builder_prompt.txt  # Main prompt for world generation
    ├── design_brief_prompt.txt   # First-pass design brief generation
    ├── fix_error_prompt.txt      # LLM-assisted validation fixes
    └── system_message.txt        # System message for world builder
```

**Prompt Loading**: Prompts are loaded at server startup and cached in memory. The prompt loader supports hot reloading - if you edit a prompt file, it will be automatically reloaded on the next request (checks file modification time).

**Usage in Code**: Prompts are accessed via the `prompt_loader` module:

```python
from app.llm.prompt_loader import get_loader

# Get a prompt template
system_prompt_template = get_loader().get_prompt("game_master", "system_prompt.txt")

# Format with variables
formatted_prompt = system_prompt_template.format(
    world_name="My World",
    theme="gothic horror",
    # ... other variables
)
```

**Hot Reloading**: For development, you can force reload prompts:

```python
from app.llm.prompt_loader import reload_prompts, reload_category

# Reload all prompts
reload_prompts()

# Reload only game master prompts
reload_category("game_master")
```

**Which Prompt is Used Where**:

| Component | Prompt File | Used In | Purpose |
|-----------|-------------|---------|---------|
| Game Master (Classic) | `game_master/system_prompt.txt` | `game_master.py` | Main system prompt for all game actions |
| Game Master (Classic) | `game_master/opening_prompt.txt` | `game_master.py` | Generates opening narrative for new games |
| Interactor (Two-Phase) | `interactor/system_prompt.txt` | `interactor.py` | Parses player input into ActionIntent/FlavorIntent with entity resolution |
| Narrator (Two-Phase) | `narrator/system_prompt.txt` | `narrator.py` | Generates prose from confirmed events (with history context) |
| World Builder (TUI) | `world_builder_prompt.txt` | `gaime_builder/` | Generates world YAML from design brief |
| World Builder (TUI) | `design_brief_prompt.txt` | `gaime_builder/` | First pass: creates design brief from description |
| World Builder (TUI) | `fix_error_prompt.txt` | `gaime_builder/` | LLM-assisted fixes for creative validation errors |
| Image Generator | `image_prompt_template.txt` | `image_generator.py` | Generates scene images for locations |
| Image Generator | `edit_prompt_template.txt` | `image_generator.py` | Edits base images to add NPCs (variants) |
| Image Generator | `interactive_elements_section.txt` | `image_generator.py` | Section describing exits/items/NPCs in images |

### Narrator History Context (Two-Phase Engine)

The two-phase engine's Narrator receives narration history for style variation:

```
## Recent Narration History

Use this to AVOID repetition in phrasing, imagery, and structure.

### Recent (full text):
[Turn 5, main_hallway] (same location)
The linoleum floor stretches before you...

[Turn 4, cafeteria]
The smell of mystery meat lingers in the air...

### Older (summaries):
[Turn 2] Player examined the trophy case.
```

**Purpose**: Prevent repetitive phrasing, AI clichés, and content repetition.

**Anti-Cliché Guidance**: The prompt includes explicit instructions to avoid:
- Metaphorical "humming" (actual machine humming is fine)
- "find yourself"
- "seems to" / "appears to"
- "the air is thick with"
- "echoes of" (unless actual sound)
- "weight of" (silence, history, etc.)

**Adaptive Tone**: When history shows repeated browsing at the same location, the narrator:
- Responds with increasing brevity
- Adds subtle irony ("The lockers remain stubbornly locker-like.")
- Gently nudges the player to explore elsewhere

### Interactor Prompt Structure (Two-Phase Engine)

The Interactor parses player input into structured intents. Its prompt includes:

**Section 1: Output Formats**
- `ActionIntent`: For state-changing actions (returns action_type, target_id, etc.)
- `FlavorIntent`: For atmospheric actions or unresolved targets

**Section 2: Action Type Reference**

| ActionType | When to Use | Required Fields |
|------------|-------------|-----------------|
| MOVE | Navigation (go, walk, enter, leave) | target_id (exit direction) |
| BROWSE | Survey surroundings (look, look around) | target_id="" |
| EXAMINE | Inspect specific entity | target_id |
| TAKE | Pick up item | target_id |
| DROP | Put down item | target_id |
| USE | Use item, optionally on target | target_id, optional instrument_id |
| OPEN | Open container/door | target_id |
| CLOSE | Close container/door | target_id |
| TALK | Initiate conversation | target_id (npc_id) |
| ASK | Ask NPC about topic | target_id (npc_id), topic_id |
| GIVE | Give item to NPC | target_id (item_id), recipient_id |
| SHOW | Show item to NPC | target_id (item_id), recipient_id |
| SEARCH | Search area/container | target_id |
| WAIT | Pass time | target_id="" |

**Section 3: Decision Process**
Guides the LLM through classification priority:
1. Movement? → Check exits by direction, destination name, or description
2. Observation? → BROWSE vs EXAMINE
3. Item Interaction? → TAKE, DROP, USE, OPEN, CLOSE
4. NPC Interaction? → TALK, ASK, GIVE, SHOW
5. Flavor Action? → Unknown verbs or unresolved targets

**Section 4: FlavorIntent Guidance**
When to use FlavorIntent instead of ActionIntent:
- Unknown verbs (dance, jump, sing)
- Known verb but target not in available entities
- ASK about undefined topic (improvised dialogue)
- Ambiguous movement (multiple exits match description)

**Section 5: World Context (dynamic)**
Populated at runtime with:
- Location ID and name
- Items at location (format: `id - "Name"`)
- Location details/scenery
- NPCs present
- Player inventory
- Available exits with descriptions (format: `direction: Destination (description)`)

**Exit Description Matching**: The Interactor can match natural language like "walk through the oak door" to the correct exit by matching against exit descriptions (e.g., `north: Office (heavy oak door)`).

**Ambiguity Handling**: When multiple exits match the player's description, the Interactor returns a FlavorIntent with `action_hint=MOVE`. The Narrator then naturally asks the player to clarify.

### System Prompt Structure

The game master system prompt includes:

1. **Role Definition**: Who the AI is
2. **World Context**: Theme, setting, constraints, starting situation
3. **Current State**: Location, inventory, flags
4. **Location Details**: Atmosphere, exit descriptions, visible items with found_descriptions
5. **Scene Description Rules**: How to describe scenes, items, and exits narratively
6. **Response Format**: Expected JSON structure

The system prompt is defined in `backend/app/llm/prompts/game_master/system_prompt.txt`. It includes:

```text
You are the Game Master for a text adventure game called "{world_name}".

## World Setting
Theme: {theme}
Tone: {tone}
{starting_situation}

## Current Game State
- Location: {current_location} ({location_name})
- Inventory: {inventory}
- Discovered Areas: {discovered}
- Story Progress: {flags}

## Narrative Memory (use this to maintain continuity)
### Recent Context
{recent_context}

### NPC Relationships
{npc_relationships}

### Already Discovered (mention briefly, do NOT describe in detail again)
{discoveries}

[... full prompt content ...]

## Response Format
You MUST respond with valid JSON in this exact format:
{{
  "narrative": "Your narrative text here...",
  "state_changes": {{
    "inventory": {{ "add": [], "remove": [] }},
    "location": null or "new_location",
    "discovered_locations": []
  }},
  "memory_updates": {{
    "npc_interactions": {{
      "npc_id": {{
        "topic_discussed": "key topic from exchange",
        "player_disposition": "how player is acting",
        "npc_disposition": "how NPC now feels",
        "notable_moment": "memorable exchange (1 sentence)"
      }}
    }},
    "new_discoveries": ["type:id", "type:id"]
  }},
  "hints": []
}}
```

**Note**: The actual prompt file contains the full template. See `backend/app/llm/prompts/game_master/system_prompt.txt` for the complete content.

### User Prompt

The player's action is passed as the user message:

```python
user_prompt = f"The player action is: {action}"
```

### Response Parsing

The LLM response is parsed as JSON:

```python
def parse_response(response: str) -> ActionResult:
    """Parse LLM JSON response into structured result."""
    data = json.loads(response)

    return ActionResult(
        narrative=data["narrative"],
        state_changes=StateChanges(
            inventory=data["state_changes"].get("inventory", {}),
            location=data["state_changes"].get("location"),
            memory_updates=MemoryUpdates(
                npc_interactions=data.get("memory_updates", {}).get("npc_interactions", {}),
                new_discoveries=data.get("memory_updates", {}).get("new_discoveries", [])
            )
        ),
        hints=data.get("hints", [])
    )
```

**Note on Flags vs Memory**: The game uses separate systems:
- `flags`: World-defined flags set by location interactions and item use actions (for game mechanics)
- `memory_updates`: Narrative memory for immersion and continuity (does not affect game mechanics)

The LLM should only provide `memory_updates` - world-defined `flags` are set automatically when matching interactions are triggered.

### Narrative Memory Guidelines

The `memory_updates` field helps the LLM track context:

**npc_interactions**: Track meaningful NPC exchanges
- `topic_discussed`: Key topic (e.g., "the dagger", "her death")
- `player_disposition`: How player is acting (e.g., "sympathetic", "aggressive")
- `npc_disposition`: How NPC feels (e.g., "warming up", "suspicious")
- `notable_moment`: Brief memorable quote or event

**new_discoveries**: Mark first descriptions using typed format
- `item:rusty_key` - first time examining/finding an item
- `npc:ghost_child` - first time meeting an NPC
- `feature:slash_marks` - first time noticing a location feature

The system prompt includes previous memory so the LLM can:
1. **Avoid repetitive descriptions**: Items/features in "Already Discovered" are mentioned briefly, not fully described again
2. **Vary repeated actions**: When player says "look around" multiple times, give abbreviated descriptions focusing on atmosphere, not repeating full details
3. **Reference previous conversations**: Acknowledge past NPC interactions naturally
4. **Maintain emotional continuity**: Use "Recent Context" to keep tone consistent

## Prompt Engineering Tips

### Scene Description Rules

The system prompt now includes explicit rules for scene descriptions:

```
## Scene Description Rules (CRITICAL)
11. When describing ANY scene (look, look around, entering a new location), ALWAYS:
    - State the location name and physical context clearly
    - Describe ALL visible items using their found_description text
    - Describe exits narratively with context (e.g., "a flickering barrier to the north")
12. If an exit seems implausible for the setting, explain WHY it's accessible
13. Only mention items that are listed in "Visible Items at Location"
14. Maintain physical reality constraints consistent with the world's theme
```

### Starting Situation Context

The `starting_situation` field from world.yaml is included in both the system prompt and opening prompt, explaining why the player can begin acting:

```python
# In system prompt
Starting Situation: {starting_situation}

# Example
Starting Situation: The power grid has failed. Your cell's energy barrier is down.
```

### Maintaining Consistency

Include explicit reminders:

```
IMPORTANT: The player does NOT have a torch. They cannot see in dark areas without one.
IMPORTANT: Jenkins is currently in the dining_room, not the entrance_hall.
```

### Handling Invalid Actions

Guide the AI on impossible actions:

```
If the player attempts an impossible action:
1. Acknowledge their intent
2. Explain why it can't be done
3. Suggest alternatives
4. Do NOT change any game state
```

### Tone Control

Use the world's `tone` field:

```yaml
# In world.yaml
tone: "gothic horror, atmospheric, Victorian prose"
```

```python
# In prompt
Write in this style: {world.tone}
```

## Token Usage

### Estimation

| Component | Approximate Tokens |
|-----------|-------------------|
| System prompt base | ~500 |
| World context | ~300-800 |
| Current state | ~100-300 |
| Location details | ~100-200 |
| Player action | ~10-50 |
| **Total Input** | ~1000-1800 |
| Response | ~200-500 |

### Cost Optimization

1. **Use efficient models**: gemini-3-pro-preview (default) or gemini-1.5-flash for cost savings
2. **Truncate history**: Don't include all narrative history
3. **Cache world context**: Reuse compiled prompts
4. **Set max_tokens**: Limit response length

```python
response = completion(
    model=model,
    messages=messages,
    max_tokens=500,  # Limit response
)
```

## Error Handling

### JSON Parse Failures

```python
try:
    data = json.loads(response)
except json.JSONDecodeError:
    # Fallback: treat as narrative only
    return ActionResult(
        narrative=response,
        state_changes=StateChanges()
    )
```

### API Errors

```python
from litellm import exceptions

try:
    response = completion(...)
except exceptions.RateLimitError:
    # Wait and retry
except exceptions.AuthenticationError:
    # Check API key
except exceptions.APIError as e:
    # General API error
```

## Local Development with Ollama

For free, private development:

1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull llama3.1`
3. Configure GAIME:
   ```bash
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   LLM_MODEL=llama3.1
   ```

**Note**: Local models may be less capable at following JSON format. Consider using a larger model (llama3.1:70b) or adding more explicit formatting instructions.

## Comparing Providers

| Provider | Speed | Quality | Cost | JSON Reliability |
|----------|-------|---------|------|-----------------|
| Gemini 3 Pro (default) | Medium | Excellent | Low | Excellent |
| Gemini 1.5 Flash | Fast | Good | Free tier | Good |
| Gemini 1.5 Pro | Medium | Excellent | Low | Excellent |
| GPT-4o | Medium | Excellent | Medium | Excellent |
| GPT-4o-mini | Fast | Good | Low | Good |
| Claude 3.5 | Medium | Excellent | Medium | Excellent |
| Ollama (local) | Varies | Varies | Free | Variable |

## Debugging

Enable verbose logging:

```bash
DEBUG=true
```

This logs:
- Full prompts sent to LLM
- Raw LLM responses
- Parsed state changes
- Token usage

## World Builder Prompts

The world builder (TUI) uses prompts defined in `gaime_builder/core/prompts/world_builder/`:

- **`world_builder_prompt.txt`**: Main prompt template for generating world YAML
- **`design_brief_prompt.txt`**: First-pass prompt to generate a design brief before YAML
- **`fix_error_prompt.txt`**: Prompt for LLM-assisted fixes of validation errors
- **`system_message.txt`**: System message for world builder LLM calls

### Schema Synchronization

Prompts are kept in sync with Pydantic models via `gaime_builder/core/schema_generator.py`:
- Generates canonical YAML examples from model definitions
- Validates that prompts use correct field structures
- Run directly to see the current schema reference

### Consistency Rules

The world builder prompt enforces:

1. Every exit MUST have narrative justification in details (e.g., `details.north: "A door leads north"`)
2. `starting_situation` MUST explain WHY the player can act NOW
3. Every item MUST have a `found_description` for discoverability
4. Include a victory condition with target location and optional flag/item
5. NPC `personality` MUST be an object with `traits`, `speech_style`, `quirks`
6. NPC dialogue rules use `dialogue_rules` list (not `dialogue_hints` dict)
7. Location access restrictions use `requires` field (not `constraints` with `locked_exit`)

### Validation System

World validation runs at three levels:

1. **File/Syntax**: YAML files exist and parse correctly
2. **Schema Compliance**: Detects deprecated patterns the loader tolerates for backwards compat
3. **Consistency**: Flag references, location/item/NPC references via `WorldValidator`

### Fix System (Generation Only)

When generating worlds, validation errors trigger the hybrid fixer:

- **Rule-based fixes**: Typos in IDs (fuzzy matching), missing simple fields
- **LLM-assisted fixes**: Creative problems like "flag X is required but never set"

The fixer creates narratively sensible interactions rather than mechanical patches.

## Image Generation

GAIME uses Google's Gemini native image generation capabilities to create immersive scene images for game locations. Images include visual hints for exits, items, and NPCs to give players natural indications for interaction.

### Configuration

Image generation uses the same `GEMINI_API_KEY` as text generation. No additional configuration is required.

### Supported Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `gemini-3-pro-image-preview` | Advanced image generation | Primary image generator |
| `gemini-2.5-flash-image` | Fast image generation | Fallback model |
| `gemini-2.0-flash-exp` | Experimental fast model | Secondary fallback |

### How It Works

1. **Context Building**: The system gathers interactive elements from the world data:
   - **Exits**: Visible doorways/passages based on direction
   - **Items**: Objects present at the location (regular, hidden, or artifacts)
   - **NPCs**: Characters at the location with their appearance

2. **Prompt Generation**: Creates a detailed art prompt from:
   - Location name, atmosphere, theme, and tone
   - Interactive elements with appropriate visibility levels
   - Style requirements (painterly, first-person, 16:9)

3. **Image Generation**: Calls Gemini's native image generation API

4. **Storage**: Images are saved to `worlds/{world_id}/images/{location_id}.png`

### Interactive Elements in Images

The image generator includes visual hints for interactive elements:

| Element Type | Visibility | Visual Representation |
|--------------|------------|----------------------|
| **Normal Exits** | Clearly visible | Doorways, passages, stairs based on direction |
| **Locked Exits** | Visible but blocked | Doors with locks or barriers |
| **Secret Exits** | Subtle hints | Faint drafts, wall irregularities, shadows |
| **Regular Items** | Naturally placed | Objects in logical locations |
| **Hidden Items** | Barely perceptible | Faint glints, partial obscuring |
| **Artifacts** | Notable presence | Subtle glow, prominent placement |
| **NPCs** | Present in scene | Figures with described appearance |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/builder/{world_id}/images/generate` | POST | Generate images for all/selected locations |
| `/api/builder/{world_id}/images/{location_id}/generate` | POST | Generate/regenerate single image |
| `/api/builder/{world_id}/images/{location_id}` | GET | Retrieve generated image |
| `/api/builder/{world_id}/images` | GET | List all available images |

### Usage Example

```python
# Generate all images for a world (with context)
from app.llm.image_generator import generate_world_images

results = await generate_world_images(
    world_id="cursed-manor",
    worlds_dir=Path("worlds")
)
# Images include visual hints for all exits, items, and NPCs

# Generate single image with custom context
from app.llm.image_generator import (
    generate_location_image,
    LocationContext,
    ExitInfo,
    ItemInfo,
    NPCInfo
)

context = LocationContext(
    exits=[
        ExitInfo(direction="north", destination_name="Kitchen"),
        ExitInfo(direction="down", destination_name="Basement", requires_key=True),
    ],
    items=[
        ItemInfo(name="Silver Key", is_hidden=False),
        ItemInfo(name="Ancient Amulet", is_artifact=True),
    ],
    npcs=[
        NPCInfo(name="Jenkins", role="Butler", appearance="An elderly man..."),
    ]
)

image_path = await generate_location_image(
    location_id="dining_room",
    location_name="Dining Room",
    atmosphere="A long mahogany table dominates this room...",
    theme="Victorian gothic horror",
    tone="atmospheric, mysterious",
    output_dir=Path("worlds/cursed-manor/images"),
    context=context
)
```

### Image Prompt Templates

Image generation is handled by the **gaime-builder TUI** (not the backend). Prompts and style presets are located in `gaime_builder/core/prompts/image_generator/`.

See `docs/STYLE_AUTHORING.md` for complete documentation on the Modular Prompt Architecture (MPA) and style presets.

### Best Practices

1. **Rich Atmosphere**: More detailed atmosphere text = better images
2. **Consistent Theme**: Theme and tone affect image style
3. **Interactive Elements**: Items and NPCs should be defined in YAML for visual inclusion
4. **Hidden Items**: Mark items as `hidden: true` for subtle representation
5. **Artifacts**: Mark items as `artifact: true` for mysterious prominence
6. **Secret Passages**: Exits to locations with `requires: flag:` are shown subtly
7. **Locked Exits**: Exits to locations with `requires: item:` show as locked
8. **Regenerate As Needed**: Use the single-image endpoint to refine specific locations
9. **Rate Limiting**: Generation includes delays to avoid API rate limits
