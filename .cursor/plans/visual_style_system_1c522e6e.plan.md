---
name: Visual Style System
overview: Implement the Modular Prompt Architecture (MPA) for stylistically consistent image generation, with individual preset files and documentation that enables AI-assisted style authoring.
todos:
  - id: create-preset-files
    content: Create 12 individual preset YAML files in presets/ folder
    status: completed
  - id: create-presets-readme
    content: Create presets/README.md with quick template for AI authoring
    status: completed
  - id: create-style-docs
    content: Create docs/STYLE_AUTHORING.md with full MPA documentation
    status: completed
  - id: create-mpa-template
    content: Create mpa_template.txt for base image generation
    status: completed
  - id: create-edit-template
    content: Create mpa_edit_template.txt for NPC variant generation
    status: completed
  - id: create-style-loader
    content: Create style_loader.py with preset scanning, loading, and prompt building
    status: completed
  - id: integrate-generator
    content: Update image_generator.py to use style_loader
    status: completed
  - id: update-cursorrules
    content: Add style authoring references to .cursorrules
    status: completed
---

# Visual Style System (MPA-Based)

## Goal

Implement the Modular Prompt Architecture (MPA) for stylistically consistent image generation, optimized for Nano Banana Pro. Clear separation between **world content** and **style**, with an AI-authorable preset system.

---

## Layer Ownership

| Layer | Name | Source | Owned By |

|-------|------|--------|----------|

| L0 | Meta-Context | Hardcoded + aspect ratio | Engine |

| L1 | Content | Location name, atmosphere, items, NPCs | World (locations.yaml) |

| L2 | Context | Era, materials, environmental state, light source | World (world.yaml: theme/tone) |

| L3 | Mood | Emotional tone, lighting quality, color palette | **Style preset** |

| L4 | Style | Artistic medium, rendering technique | **Style preset** |

| L5 | Technical | Composition, camera, perspective | **Style preset** |

| L6 | Negative | Anti-styles, quality constraints | **Style preset** |

**Key insight**: L2 (Context) is world content, NOT style. A Victorian world can use `anime` or `noir` style.

---

## File Structure

```
backend/
  app/
    llm/
      prompts/
        image_generator/
          presets/                     # NEW: One file per preset
            README.md                  # Quick reference for AI authoring
            classic-fantasy.yaml
            dark-fantasy.yaml
            noir.yaml
            cyberpunk.yaml
            anime.yaml
            watercolor.yaml
            childrens-book.yaml
            horror.yaml
            steampunk.yaml
            pixel-art.yaml
            photorealistic.yaml
            comic-book.yaml
          mpa_template.txt             # Base image generation
          mpa_edit_template.txt        # NPC variant editing
      style_loader.py                  # Style loading utilities
docs/
  STYLE_AUTHORING.md                   # Full MPA documentation
```

---

## Style Preset File Format

Each preset is a standalone YAML file (e.g., `noir.yaml`):

```yaml
# noir.yaml - Film Noir style preset
name: "Film Noir"
description: "Classic detective fiction aesthetic with dramatic shadows and moral ambiguity"

# L3: Mood
mood:
  tone: "gritty, tense, morally ambiguous"
  lighting: "high contrast, harsh shadows, pools of light, venetian blind patterns"
  color_palette: "desaturated with selective color accents, mostly black and white"

# L4: Style (MOST IMPORTANT)
style: |
  Film noir cinematography. High contrast black and white aesthetic with
  selective color accents. Dramatic shadows, chiaroscuro lighting, rain-slicked
  surfaces reflecting neon signs. The artistic style is paramount.

# L5: Technical
technical:
  perspective: "first-person"
  shot: "medium shot or medium close-up"
  camera: "eye level or dramatic low angle"
  effects: "film grain, slight vignette, wet reflections"

# L6: Anti-styles (prevents style drift)
anti_styles:
  - "colorful"
  - "bright and cheerful"
  - "anime or manga"
  - "cartoon"
  - "fantasy illustration"
  - "watercolor"
  - "children's book"

# L6: Quality constraints (can use defaults or override)
quality_constraints:
  - "watermarks or signatures"
  - "blurry or low-quality artifacts"
  - "distorted proportions"
  - "modern elements unless specified"
```

---

## AI Authoring Support

### presets/README.md (Quick Reference)

Concise guide for AI agents creating new presets:

- Template with all required fields
- Field descriptions and examples
- Common pitfalls to avoid
- Cross-references to full docs

### docs/STYLE_AUTHORING.md (Full Documentation)

Comprehensive guide explaining:

- MPA layer architecture and purpose
- How each layer affects image generation
- Nano Banana Pro emphasis techniques
- Anti-style strategy (why it matters)
- Example presets with annotations
- Testing guidelines

### .cursorrules Update

Add reference to style authoring docs:

```
- **`/docs/STYLE_AUTHORING.md`** - How to create visual style presets
- **`/backend/app/llm/prompts/image_generator/presets/README.md`** - Quick preset template
```

---

## World Integration

```yaml
# world.yaml

theme: "Victorian gothic horror"
tone: "atmospheric, mysterious"

# Style reference - just the preset name
style: dark-fantasy

# OR with overrides:
style:
  preset: dark-fantasy
  overrides:
    mood:
      color_palette: "sepia and amber tones"
```

---

## NPC Variant Compatibility

`mpa_edit_template.txt` preserves style when adding NPCs:

```
Edit this image to add the following character while preserving the scene:

{npc_description}

Critical Requirements:
- PRESERVE the original scene's composition, lighting, and colors
- MATCH the artistic style: {l4_style_summary}
- Position the character naturally: {npc_placement}

Must NOT include: {l6_anti_styles_brief}
```

---

## Implementation

### 1. Create preset files (12 initial)

Individual YAML files in `presets/` folder.

### 2. Create presets/README.md

Quick reference template for AI authoring.

### 3. Create docs/STYLE_AUTHORING.md

Full MPA documentation with examples.

### 4. Create mpa_template.txt

Base generation template with 7-layer structure.

### 5. Create mpa_edit_template.txt

NPC variant template preserving style.

### 6. Create style_loader.py

- Scan and load all preset files from folder
- `resolve_style()` - merge preset + overrides
- `build_mpa_prompt()` - assemble layers
- `build_mpa_edit_prompt()` - for NPC variants

### 7. Update image_generator.py

- Use style_loader for prompt building
- Backward compatible: no style = classic-fantasy

### 8. Update .cursorrules

Reference STYLE_AUTHORING.md in folder guidance.

---

## Key Files

| File | Action |

|------|--------|

| `backend/app/llm/prompts/image_generator/presets/*.yaml` | CREATE (12 files) |

| `backend/app/llm/prompts/image_generator/presets/README.md` | CREATE |

| `backend/app/llm/prompts/image_generator/mpa_template.txt` | CREATE |

| `backend/app/llm/prompts/image_generator/mpa_edit_template.txt` | CREATE |

| `backend/app/llm/style_loader.py` | CREATE |

| `backend/app/llm/image_generator.py` | MODIFY |

| `docs/STYLE_AUTHORING.md` | CREATE |

| `docs/index.md` | MODIFY (add to table) |

| `.cursorrules` | MODIFY |

---

## Migration

- Worlds without `style` → `classic-fantasy` preset
- L2 derived from existing `theme` + `tone` fields
