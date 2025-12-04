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

### System Prompt Structure

The game master system prompt includes:

1. **Role Definition**: Who the AI is
2. **World Context**: Theme, setting, constraints, starting situation
3. **Current State**: Location, inventory, flags
4. **Location Details**: Atmosphere, exit descriptions, visible items with found_descriptions
5. **Scene Description Rules**: How to describe scenes, items, and exits narratively
6. **Response Format**: Expected JSON structure

```python
SYSTEM_PROMPT = """You are the Game Master for a text adventure game.

## World Context
{world_context}

## Current Game State
- Location: {current_location}
- Inventory: {inventory}
- Stats: {stats}
- Discovered: {discovered}
- Story Flags: {flags}

## Your Role
- Narrate the world in second person ("You see...")
- Respond to player actions appropriately
- Maintain consistency with world rules
- Track state changes from actions

## Constraints
{constraints}

## Response Format
Respond with JSON only:
{{
  "narrative": "Your narrative text here...",
  "state_changes": {{
    "inventory": {{ "add": [], "remove": [] }},
    "location": null or "new_location",
    "stats": {{ "health": 0 }},
    "llm_flags": {{ "flag_name": true }}
  }},
  "hints": []
}}
"""
```

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
            stats=data["state_changes"].get("stats", {}),
            llm_flags=data["state_changes"].get("llm_flags", {})
        ),
        hints=data.get("hints", [])
    )
```

**Note on Flag Types**: The game uses two separate flag namespaces:
- `flags`: World-defined flags set by location interactions and item use actions
- `llm_flags`: AI-generated contextual flags for narrative tracking

The LLM should only set `llm_flags` - world-defined `flags` are set automatically when matching interactions are triggered.

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

The world builder uses a different prompt style with critical consistency rules:

```python
WORLD_BUILDER_PROMPT = """Generate a text adventure game world.

Theme: {theme}
Description: {prompt}
Number of locations: {num_locations}
Number of NPCs: {num_npcs}

Generate complete YAML content for:
1. world.yaml - Theme, premise, starting_situation, victory condition, constraints
2. locations.yaml - All locations with connections and exit details
3. npcs.yaml - Characters with personalities
4. items.yaml - Key items with found_descriptions

## CRITICAL CONSISTENCY RULES:
1. Every exit MUST have narrative justification in details (e.g., details.north: "A door leads north")
2. starting_situation MUST explain WHY the player can act NOW
3. Every item MUST have a found_description for discoverability
4. Include a victory condition with target location and optional flag/item
5. Starting location must make narrative sense

Ensure all references between files are consistent.
Output valid YAML for each file.
"""
```

The world builder validation also checks for:
- Missing `found_description` on items (warning)
- Missing `starting_situation` (warning)
- Missing `victory` condition (warning)
- Victory location that doesn't exist (error)
- Exit details for narrative context (warning)

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

### Image Prompt Template

The prompt now includes interactive elements:

```python
prompt = f"""Create a dramatic, atmospheric scene illustration for a text adventure game.

Location: {location_name}
Theme: {theme}
Tone: {tone}

Scene Description:
{atmosphere}

Interactive Elements to Include:
Visible pathways: doorway to the left; passage ahead; stairs descending, secured with lock
Objects in the scene: Silver Key placed naturally within the scene
Significant objects: Ancient Amulet that draws the eye with subtle presence
Characters visible in the scene: A figure - Jenkins (Butler): An elderly man...

Important: These elements should be integrated naturally into the scene, not highlighted 
or labelled. They should reward careful observation - exits should look like real 
architectural features, items should be placed where they would naturally be found, 
and any characters should be positioned authentically within the space.

Style Requirements:
- Digital painting style with rich colors and dramatic lighting
- Painterly, evocative atmosphere suitable for a text adventure game
- First-person perspective as if the player is viewing the scene
- Moody, immersive lighting that matches the tone
- 16:9 widescreen composition
- Detailed environment with depth and atmospheric effects
- Natural integration of doorways, passages, and architectural features
- Subtle visual storytelling through object placement and environmental details
"""
```

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

