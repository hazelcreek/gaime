# World Builder Agent: In-Editor Refactor Concept

## Executive Summary

This document proposes refactoring the World Builder from a UI-based React component to an **in-editor agent experience** within Cursor. The agent would specialize in world building through an interactive, conversational workflow—asking the world developer questions to iteratively create and enhance game worlds.

This approach offers significant advantages:
- **Interactive dialogue** instead of one-shot generation
- **Deeper customization** through iterative refinement
- **Better world enhancement** for existing worlds
- **Direct file editing** with full version control
- **Richer context** from the codebase and existing worlds

---

## Current State Analysis

### How the World Builder Works Today

The current world builder is a **React component** (`WorldBuilder.tsx`) with a backend API (`world_builder.py`):

1. User fills out a form (description, theme, location count, NPC count)
2. Single API call generates all YAML files at once
3. User can preview and save the generated content
4. Limited ability to refine—essentially regenerate from scratch

**Limitations of the current approach:**

| Issue | Impact |
|-------|--------|
| **One-shot generation** | No iterative refinement; regeneration discards all progress |
| **Limited context** | User can't easily reference existing worlds for inspiration |
| **No dialogue** | Can't ask clarifying questions or explore alternatives |
| **UI bottleneck** | Web UI limits input richness (no file references, code snippets) |
| **Post-creation editing** | Requires manual YAML editing with no AI assistance |
| **Validation gaps** | Issues found after generation require manual fixing |

---

## Proposed Architecture: World Builder Agent

### Core Concept

Replace the UI-based builder with a **specialized Cursor agent** that works through conversation directly in the code editor. The agent has deep knowledge of:

- GAIME's YAML schema and conventions
- World authoring best practices
- Existing worlds in the repository
- Validation rules and common pitfalls

### User Experience Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CURSOR EDITOR                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  User: "I want to create a new world set in a 1920s speakeasy        │
│         during Prohibition. Think noir mystery."                      │
│                                                                       │
│  Agent: "Great concept! Let me ask a few questions to shape this:    │
│                                                                       │
│          1. **Protagonist**: Who is the player? A detective, a       │
│             bootlegger, a journalist investigating corruption?       │
│                                                                       │
│          2. **Starting situation**: What event triggers the          │
│             adventure? A murder? A missing person? A debt to pay?    │
│                                                                       │
│          3. **Tone**: Hard-boiled noir, campy fun, or somewhere      │
│             in between?                                               │
│                                                                       │
│          4. **Scope**: How many locations feel right? A focused      │
│             speakeasy (4-6) or the whole neighborhood (8-12)?        │
│                                                                       │
│          I noticed you have a 'cursed-manor' world with good         │
│          NPC personality examples. Want similar depth here?"          │
│                                                                       │
│  User: "Detective investigating a singer's disappearance.            │
│         Hard-boiled. Let's do 8 locations. Yes, deep NPCs please."   │
│                                                                       │
│  Agent: "Perfect. I'll create the initial structure. Let me start   │
│          with the world.yaml..."                                      │
│                                                                       │
│  [Agent creates worlds/midnight-jazz-club/world.yaml]                │
│  [Agent asks about key NPCs before creating npcs.yaml]               │
│  [Agent iterates through locations with user input]                  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Interactive Question Categories

The agent asks questions in phases, building understanding progressively:

#### Phase 1: Core Concept
- **Theme & Genre**: What's the setting? What genre conventions apply?
- **Protagonist**: Who is the player? What's their motivation?
- **Starting Situation**: What event enables the adventure to begin NOW?
- **Victory Condition**: How does the player win? What's the payoff?

#### Phase 2: World Structure
- **Location Count & Connectivity**: How many areas? Linear, hub-and-spoke, or maze?
- **Key Locations**: Which places are essential to the story?
- **Locked Areas**: What gates progression? Keys, knowledge, trust?
- **Secret Areas**: What rewards exploration?

#### Phase 3: Characters
- **Major NPCs**: Who are the important characters?
- **Personality Depth**: Speech patterns, quirks, secrets?
- **Knowledge Distribution**: What does each NPC know? (Critical for preventing hallucination)
- **Dynamic Behavior**: Do NPCs move? Appear conditionally?

#### Phase 4: Items & Puzzles
- **Key Items**: What objects drive the narrative?
- **Puzzle Design**: How do items, locations, and NPCs connect?
- **Hidden Content**: What rewards careful exploration?
- **Artifacts/MacGuffins**: Any special objects to collect?

#### Phase 5: Refinement
- **Atmosphere Details**: Sensory details for AI narration
- **Exit Descriptions**: Narrative context for navigation
- **Item Placements**: Where objects appear in scenes
- **Constraints**: Rules the Game Master must follow

---

## Implementation Approach

### Option A: Cursor Rules + Custom Instructions

**Minimal implementation** using Cursor's existing agent capabilities:

1. Create a `.cursor/agents/world-builder.md` file with:
   - Complete schema documentation
   - Question flowchart
   - Best practices from `WORLD_AUTHORING.md`
   - Examples from existing worlds

2. User invokes: "Use the world builder agent to help me create a new world"

3. Agent follows instructions to ask questions and create files

**Pros**:
- No code changes required
- Leverages existing Cursor agent capabilities
- Easy to iterate on prompts

**Cons**:
- No programmatic validation
- Can't run the validator automatically
- Limited tool access

---

### Option B: MCP (Model Context Protocol) Server

**Full-featured implementation** with custom tools:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP World Builder Server                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Tools:                                                          │
│  ├── create_world_scaffold(world_id, name, theme)               │
│  ├── add_location(world_id, location_data)                      │
│  ├── add_npc(world_id, npc_data)                                │
│  ├── add_item(world_id, item_data)                              │
│  ├── validate_world(world_id) → errors, warnings                │
│  ├── list_worlds() → existing worlds                            │
│  ├── get_world_details(world_id) → full world data              │
│  ├── suggest_exits(world_id) → bidirectional exit suggestions   │
│  └── check_references(world_id) → dangling references           │
│                                                                  │
│  Resources:                                                      │
│  ├── world://{world_id}/world.yaml                              │
│  ├── world://{world_id}/locations.yaml                          │
│  ├── world://{world_id}/npcs.yaml                               │
│  └── world://{world_id}/items.yaml                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Sample MCP Tool: `validate_world`**

```python
@mcp.tool()
async def validate_world(world_id: str) -> dict:
    """
    Validate a world's YAML files for consistency.
    Returns errors that must be fixed and warnings for improvement.
    """
    validator = WorldValidator(worlds_dir)
    result = validator.validate(world_id)

    return {
        "valid": len(result.errors) == 0,
        "errors": result.errors,
        "warnings": result.warnings,
        "suggestions": result.suggestions
    }
```

**Sample MCP Tool: `suggest_exits`**

```python
@mcp.tool()
async def suggest_exits(world_id: str) -> dict:
    """
    Analyze location exits and suggest bidirectional connections.
    Finds one-way exits that should probably be two-way.
    """
    # Parse locations.yaml
    # Find exits that don't have matching reverse exits
    # Return suggestions
    return {
        "missing_reverse_exits": [
            {
                "from": "library",
                "to": "entrance_hall",
                "direction": "south",
                "suggested_reverse": "north"
            }
        ],
        "orphan_locations": ["secret_room"]  # No exits lead here
    }
```

**Pros**:
- Programmatic validation during creation
- Rich tool capabilities
- Can leverage existing Python backend code
- Proper error handling

**Cons**:
- Requires MCP server setup
- More complex implementation
- Need to maintain server alongside game

---

### Option C: Hybrid Approach (Recommended)

Combine both approaches for maximum flexibility:

1. **Agent Instructions File** (`.cursor/agents/world-builder.md`)
   - Comprehensive question flow
   - Schema documentation
   - Best practices

2. **Lightweight MCP Server** (`backend/mcp/world_builder_server.py`)
   - Validation tool (reuses existing validator)
   - Reference checking tool
   - World listing tool

3. **CLI Validation** (already exists)
   - `python -m app.engine.validator world-id`
   - Agent can invoke via shell

---

## Agent Capabilities for World Enhancement

Beyond initial creation, the agent excels at **enhancing existing worlds**:

### Enhancement Scenarios

| Scenario | Agent Approach |
|----------|----------------|
| **Add new location** | Reads existing locations, suggests connections, creates with proper exits |
| **Deepen an NPC** | Reviews current personality, suggests knowledge expansion, adds dialogue rules |
| **Add puzzle chain** | Analyzes existing items/flags, designs multi-step puzzle, updates locations |
| **Improve atmosphere** | Reads locations, rewrites atmosphere with richer sensory details |
| **Fix validation errors** | Runs validator, explains issues, makes corrections |
| **Add item found_descriptions** | Scans items.yaml, adds missing descriptions |
| **Balance difficulty** | Reviews constraints and puzzle logic, suggests adjustments |

### Example Enhancement Session

```
User: "The ghost_child NPC feels flat. Can you make them more compelling?"

Agent: "Let me review the current ghost_child definition..."

[Reads worlds/cursed-manor/npcs.yaml]

"I see the ghost_child has basic traits but limited personality depth.
Here are some enhancement ideas:

1. **Backstory hints**: Add knowledge about HOW they died (without
   revealing too much). This informs their behavior.

2. **Communication style**: They can't speak—but what gestures do they
   use? Pointing? Writing in dust? Rearranging objects?

3. **Emotional triggers**: What makes them appear? What makes them
   vanish in fear? What comforts them?

4. **Connection to victory**: How does helping the ghost relate to
   breaking the curse?

Want me to expand the ghost_child with these elements? I'll also need
to update their `appears_when` conditions if we add new triggers."

User: "Yes! They died in a fire trying to save their sister. They
       communicate by manipulating candle flames."

Agent: "Beautiful—that ties into the mansion's candles naturally.
       I'll update npcs.yaml and add new details to the nursery
       location where the fire started..."

[Edits npcs.yaml with expanded personality]
[Adds fire-related details to nursery in locations.yaml]
[Creates burnt_doll item with found_description]
[Runs validator to ensure consistency]
```

---

## Agent Instruction Structure

The agent instructions file would include:

### 1. Role Definition

```markdown
You are a World Builder Agent specializing in creating and enhancing
game worlds for GAIME. You work interactively with world developers
through dialogue—asking questions to understand their vision before
making changes.
```

### 2. Schema Knowledge

```markdown
## YAML Schema Reference

### world.yaml
- name: (required) Display name
- theme: Setting/genre
- tone: Emotional style for narration
- premise: Opening story hook
- starting_situation: (critical) WHY the player can act NOW
- victory: Win condition with location/flag/item/narrative
...
```

### 3. Question Framework

```markdown
## Interactive Questioning Flow

When creating a NEW world, gather information in this order:
1. Core concept (theme, protagonist, starting situation)
2. Victory condition (how does the player win?)
3. Key locations (must-have places)
4. Major NPCs (who inhabits this world?)
5. Critical items (what drives puzzles/story?)

When ENHANCING an existing world, first:
1. Read all YAML files to understand current state
2. Ask what the developer wants to improve
3. Propose specific changes before making them
```

### 4. Best Practices

```markdown
## Critical Rules

1. Every item MUST have a `found_description`
2. Every exit direction MUST have a detail entry
3. NPCs with location knowledge MUST include actual location IDs
4. Bidirectional exits should match (north/south, etc.)
5. Run validation before considering work complete
```

### 5. Example Dialogues

Include full sample conversations for:
- Creating a new world from scratch
- Adding a location to an existing world
- Deepening an NPC's personality
- Designing a multi-step puzzle
- Fixing validation errors

---

## Migration Path

### Phase 1: Agent Instructions (Week 1)
- Create `.cursor/agents/world-builder.md`
- Document complete question flow
- Test with 2-3 world creation sessions
- Iterate on prompts based on results

### Phase 2: CLI Integration (Week 2)
- Ensure validator works from command line
- Agent invokes validator after changes
- Add missing validation checks

### Phase 3: MCP Tools (Week 3-4)
- Build MCP server with core tools
- Integrate with Cursor
- Add advanced tools (exit suggestions, reference checking)

### Phase 4: Deprecate UI Builder (Future)
- Keep UI for image generation (still valuable)
- Remove world generation from React component
- Update documentation

---

## UI Image Generator Retention

The **image generation** functionality should remain in the UI because:

1. **Visual feedback** is better in a graphical interface
2. **Batch operations** with progress indicators
3. **Image preview** and regeneration controls
4. **Variant management** for conditional NPCs

The agent could still help with image prompts:
```
User: "The library image doesn't capture the creepiness I want."

Agent: "Let me review the library's atmosphere description..."

"The current atmosphere focuses on 'dusty tomes' and 'moonlight'—
fairly generic. Try this enhanced version:

```yaml
atmosphere: |
  Floor-to-ceiling shelves groan under centuries of forbidden
  knowledge. A cold draft carries whispers from between the
  stacks. Moonlight streams through a cracked window,
  illuminating dust motes that drift like wandering souls.
  Something moved in the shadows near the reading alcove.
```

This adds motion, sound, and unease. Want me to update it?
Then you can regenerate the image in the UI."
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| World creation time | Faster than UI (measured by user feedback) |
| Validation errors at creation | Zero (agent validates before completion) |
| User satisfaction | Higher engagement through dialogue |
| World complexity | Deeper NPCs, better puzzles through questioning |
| Enhancement sessions | New capability not possible in UI |

---

## Open Questions

1. **Image generation integration**: Should the agent trigger image generation, or keep that in the UI?

2. **Template worlds**: Should we provide "starter templates" the agent can customize?

3. **Playtesting integration**: Could the agent help playtest worlds by simulating player actions?

4. **Multi-file atomicity**: How do we handle partial failures when creating multiple YAML files?

5. **Version control**: Should the agent create commits, or leave that to the developer?

---

## Appendix: Sample Agent Instructions Excerpt

```markdown
# World Builder Agent

You are an expert game world designer for GAIME, a text adventure engine.
Your role is to help developers create rich, consistent game worlds through
interactive dialogue.

## Your Approach

1. **Ask before assuming**: Gather requirements through questions
2. **Show before doing**: Propose changes and explain reasoning
3. **Validate always**: Run validation after every file change
4. **Reference existing work**: Use other worlds as inspiration
5. **Explain constraints**: Help developers understand schema rules

## When Creating a New World

Start by understanding the developer's vision:

"I'd love to help you build this world! Before I start creating files,
let me ask a few questions to make sure I capture your vision:

1. **Who is the player?** What's their role and motivation?
2. **What triggers the adventure?** Why can the player act NOW?
3. **How does it end?** What's the victory condition?
4. **What's the tone?** Serious horror, campy fun, noir mystery?
5. **What scope feels right?** Intimate (4-6 locations) or expansive (10+)?"

After gathering answers, create files incrementally:
1. world.yaml first (establishes foundation)
2. locations.yaml (get developer input on key locations)
3. npcs.yaml (discuss major characters)
4. items.yaml (design puzzles together)

## When Enhancing an Existing World

First, read all YAML files to understand the current state:

"Let me review your world to understand what exists..."

Then ask targeted questions:

"I see you have 8 locations and 3 NPCs. What would you like to improve?
- Add new locations or deepen existing ones?
- Make NPCs more interesting?
- Add new items or puzzles?
- Fix any specific issues?"

## Validation

After every change, run:
```bash
python -m app.engine.validator {world_id}
```

If errors exist, fix them before proceeding. Explain warnings and
ask if the developer wants to address them.
```

---

## Conclusion

Moving the World Builder from UI to an in-editor agent transforms world creation from a **form-filling exercise** into a **collaborative design session**. The agent's ability to ask questions, reference existing work, and validate continuously will produce higher-quality worlds with less friction.

The interactive nature also opens new capabilities—enhancing existing worlds, fixing issues through dialogue, and learning from the developer's preferences over time.

Recommended next step: Create the agent instructions file and test with a pilot world creation session.
