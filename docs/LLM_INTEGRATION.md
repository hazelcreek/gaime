# LLM Integration

This document covers how GAIME integrates with Large Language Models, including configuration, prompts, and provider setup.

## Supported Providers

GAIME uses [LiteLLM](https://github.com/BerriAI/litellm) for provider-agnostic LLM calls.

| Provider | Models | Setup |
|----------|--------|-------|
| **Google Gemini** | gemini-1.5-flash, gemini-1.5-pro | API key from [aistudio.google.com](https://aistudio.google.com) |
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
LLM_MODEL=gemini-1.5-flash

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
| Gemini | `gemini/model-name` | `gemini/gemini-1.5-flash` |
| OpenAI | `model-name` | `gpt-4o` |
| Anthropic | `anthropic/model-name` | `anthropic/claude-3-5-sonnet-20241022` |
| Ollama | `ollama/model-name` | `ollama/llama3.1` |

## Prompt Architecture

### System Prompt Structure

The game master system prompt includes:

1. **Role Definition**: Who the AI is
2. **World Context**: Theme, setting, constraints
3. **Current State**: Location, inventory, flags
4. **Response Format**: Expected JSON structure

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
    "flags": {{ "flag_name": true }}
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
            flags=data["state_changes"].get("flags", {})
        ),
        hints=data.get("hints", [])
    )
```

## Prompt Engineering Tips

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

1. **Use efficient models**: gemini-1.5-flash is cheap and fast
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
| Gemini Flash | Fast | Good | Free tier | Good |
| Gemini Pro | Medium | Excellent | Low | Excellent |
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

The world builder uses a different prompt style:

```python
WORLD_BUILDER_PROMPT = """Generate a text adventure game world.

Theme: {theme}
Description: {prompt}
Number of locations: {num_locations}
Number of NPCs: {num_npcs}

Generate complete YAML content for:
1. world.yaml - Theme, premise, constraints
2. locations.yaml - All locations with connections
3. npcs.yaml - Characters with personalities
4. items.yaml - Key items and puzzles

Ensure all references between files are consistent.
Output valid YAML for each file.
"""
```

## Image Generation

GAIME uses Google's Gemini native image generation capabilities to create immersive scene images for game locations.

### Configuration

Image generation uses the same `GEMINI_API_KEY` as text generation. No additional configuration is required.

### Supported Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `gemini-2.0-flash-exp` | Native image generation | Primary image generator |
| `imagen-3.0-generate-002` | Dedicated image model | Fallback for complex scenes |

### How It Works

1. **Prompt Generation**: The system creates a detailed art prompt from:
   - Location name
   - Atmospheric description from YAML
   - World theme and tone
   - Style requirements (painterly, first-person, 16:9)

2. **Image Generation**: Calls Gemini's native image generation API

3. **Storage**: Images are saved to `worlds/{world_id}/images/{location_id}.png`

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/builder/{world_id}/images/generate` | POST | Generate images for all/selected locations |
| `/api/builder/{world_id}/images/{location_id}/generate` | POST | Generate/regenerate single image |
| `/api/builder/{world_id}/images/{location_id}` | GET | Retrieve generated image |
| `/api/builder/{world_id}/images` | GET | List all available images |

### Usage Example

```python
# Generate all images for a world
from app.llm.image_generator import generate_world_images

results = await generate_world_images(
    world_id="cursed-manor",
    worlds_dir=Path("worlds")
)

# Generate single image
from app.llm.image_generator import generate_location_image

image_path = await generate_location_image(
    location_id="entrance_hall",
    location_name="Entrance Hall",
    atmosphere="A grand but decayed entrance hall...",
    theme="Victorian gothic horror",
    tone="atmospheric, mysterious",
    output_dir=Path("worlds/cursed-manor/images")
)
```

### Image Prompt Template

```python
prompt = f"""Create a dramatic, atmospheric scene illustration for a text adventure game.

Location: {location_name}
Theme: {theme}
Tone: {tone}

Scene Description:
{atmosphere}

Style Requirements:
- Digital painting style with rich colors and dramatic lighting
- Painterly, evocative atmosphere suitable for a text adventure game
- First-person perspective as if the player is viewing the scene
- Moody, immersive lighting that matches the tone
- No text, UI elements, or characters in frame
- 16:9 widescreen composition
- Detailed environment with depth and atmospheric effects
"""
```

### Best Practices

1. **Rich Atmosphere**: More detailed atmosphere text = better images
2. **Consistent Theme**: Theme and tone affect image style
3. **Regenerate As Needed**: Use the single-image endpoint to refine specific locations
4. **Rate Limiting**: Generation includes delays to avoid API rate limits

