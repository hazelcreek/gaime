# Style Authoring Guide

This guide explains how to create and use visual style presets for GAIME's image generation system.

## Overview

GAIME uses the **Modular Prompt Architecture (MPA)** for generating stylistically consistent images across game worlds. The MPA separates **world content** from **visual style**, allowing the same Victorian mansion to be rendered in anime style, noir style, or photorealistic style.

## The Seven-Layer Architecture

Image generation prompts are built from seven distinct layers:

| Layer | Name | Source | Description |
|-------|------|--------|-------------|
| L0 | Meta-Context | Engine | Task definition, quality tier, aspect ratio |
| L1 | Content | Location data | Scene description, items, NPCs, exits |
| L2 | Context | World data | Era, materials, environmental state, light sources |
| L3 | Mood | **Style preset** | Emotional tone, lighting quality, color palette |
| L4 | Style | **Style preset** | Artistic medium, rendering technique |
| L5 | Technical | **Style preset** | Composition, camera, perspective |
| L6 | Negative | **Style preset** | Anti-styles, quality constraints |

### Key Insight: Content vs. Style Separation

**L2 (Context)** describes *what* the world is made of:
- "Victorian era, wood paneling, lit by candles"
- "Futuristic space station, metal and glass, holographic displays"

**L3-L6 (Style)** describes *how* to render it:
- "Anime illustration with cel-shading"
- "Film noir with high contrast shadows"

This separation means a Victorian gothic world can use `anime` style OR `noir` style - they're independent choices.

## Using Styles in Worlds

### Option 1: Reference a Preset

```yaml
# world.yaml
name: "The Cursed Manor"
theme: "Victorian gothic horror"
tone: "atmospheric, mysterious"

style: dark-fantasy  # Just the preset name
```

### Option 2: Preset with Overrides

```yaml
# world.yaml
style:
  preset: dark-fantasy
  overrides:
    mood:
      color_palette: "sepia and amber tones instead of cool shadows"
```

### Option 3: Fully Custom Style Block

```yaml
# world.yaml
style_block:
  mood:
    tone: "unique mood description"
    lighting: "specific lighting"
    color_palette: "custom colors"
  style: |
    Complete custom style description...
  technical:
    perspective: "first-person"
    shot: "medium wide"
    camera: "eye level"
  anti_styles:
    - "conflicting style 1"
    - "conflicting style 2"
```

## Creating Style Presets

Style presets are YAML files in `/gaime_builder/core/prompts/image_generator/presets/`.

### File Structure

Each preset file contains:

```yaml
# preset-name.yaml
name: "Human Readable Name"
description: "When and why to use this style"

mood:        # L3
  tone: "..."
  lighting: "..."
  color_palette: "..."

style: |     # L4
  ...

technical:   # L5
  perspective: "..."
  shot: "..."
  camera: "..."
  effects: "..."

anti_styles: # L6
  - "..."

quality_constraints:  # L6
  - "..."
```

### Layer Details

#### L3: Mood

Defines the emotional atmosphere through three components:

| Field | Purpose | Examples |
|-------|---------|----------|
| `tone` | Emotional keywords | "gritty, tense", "whimsical, dreamy", "epic, adventurous" |
| `lighting` | Light quality | "harsh shadows", "soft diffused", "neon glow", "candlelit" |
| `color_palette` | Color guidance | "desaturated with red accents", "warm earth tones", "vibrant saturated" |

**Example:**
```yaml
mood:
  tone: "gritty, tense, morally ambiguous"
  lighting: "high contrast, harsh shadows, pools of light from neon signs"
  color_palette: "desaturated with selective color accents, mostly black and white"
```

#### L4: Style (Most Important)

Defines the artistic rendering technique. This is the most critical layer for visual consistency.

**Best Practices:**
1. Be specific about the artistic medium
2. Reference real-world art styles or artists when helpful
3. Include emphasis language: "The visual style is paramount"
4. Describe texture, brushwork, or rendering qualities

**Example:**
```yaml
style: |
  Film noir cinematography. High contrast black and white aesthetic with
  selective color accents. Dramatic shadows, chiaroscuro lighting, rain-slicked
  surfaces reflecting neon signs. The visual style is paramount and must
  be maintained consistently throughout the entire image.
```

#### L5: Technical

Defines camera and composition defaults:

| Field | Options | Notes |
|-------|---------|-------|
| `perspective` | first-person, third-person, top-down, isometric | Usually "first-person" for adventure games |
| `shot` | wide shot, medium wide, medium, close-up | Usually "medium wide shot" for scene context |
| `camera` | eye level, low angle, high angle, dutch angle | "eye level" is standard; others for drama |
| `effects` | film grain, vignette, glow, particles, etc. | Style-specific visual effects |

**Example:**
```yaml
technical:
  perspective: "first-person"
  shot: "medium wide shot"
  camera: "eye level or dramatic low angle"
  effects: "film grain, slight vignette, wet reflections"
```

#### L6: Anti-Styles and Quality Constraints

**Anti-styles** are critical for preventing style drift. They tell the AI what NOT to generate.

**Strategy for choosing anti-styles:**
1. **Opposite aesthetics**: If "painterly," add "photorealistic"
2. **Adjacent conflicting styles**: If "noir," add "anime" and "fantasy"
3. **Common AI defaults**: Add styles the AI might fall back to
4. **Include 5-8 anti-styles** for robust enforcement

**Example:**
```yaml
anti_styles:
  - "colorful and vibrant"
  - "bright and cheerful"
  - "anime or manga"
  - "cartoon or whimsical"
  - "fantasy illustration"
  - "watercolor or soft"

quality_constraints:
  - "watermarks or signatures"
  - "blurry or low-quality artifacts"
  - "distorted proportions"
```

## Nano Banana Pro Optimization

GAIME uses **Nano Banana Pro** (Gemini 3 Pro Image Preview) for image generation. This model uses natural language understanding rather than numeric weights.

### Emphasis Techniques

Instead of `(style:1.4)`, use natural language:

```yaml
# Good - natural language emphasis
style: |
  The visual style is the most important aspect of this image: digital
  painting with rich textures. This style must be maintained consistently
  throughout the entire image.

# Bad - numeric weights (won't work with Nano Banana Pro)
style: "((digital painting:1.4)), rich textures"
```

### Embedded Negatives

Anti-styles are embedded in the prompt as natural language:

```
Critical constraints - the image must NOT include:
- Photorealistic or hyperrealistic rendering
- 3D CGI or Unreal Engine aesthetics
- Anime or cartoon styling
```

## Available Presets

| Preset | Best For |
|--------|----------|
| `classic-fantasy` | Traditional fantasy adventures **(DEFAULT)** |
| `dark-fantasy` | Gothic, horror-tinged fantasy |
| `noir` | Detective mysteries, 1940s settings |
| `cyberpunk` | Sci-fi dystopia, neon-lit futures |
| `anime` | Japanese animation style |
| `watercolor` | Dreamy, whimsical stories |
| `childrens-book` | Age-appropriate adventures |
| `horror` | Mature psychological horror |
| `steampunk` | Victorian industrial fantasy |
| `pixel-art` | Retro 16-bit gaming |
| `photorealistic` | Grounded realistic settings |
| `comic-book` | Graphic novel action |
| `scandi-scottish-noir` | Nordic/Scottish noir hybrid, temperate coastal |
| `folk-noir` | Folklore-infused noir, rural unease, ritual dread |
| `80s-cartoon` | Classic Looney Tunes, Hanna-Barbera, Tom & Jerry |
| `claymation` | Wallace & Gromit, Aardman stop-motion |
| `muppets` | Jim Henson puppet theater aesthetic |
| `pixar` | Modern 3D animated movie (Pixar/Disney) |
| `asterix` | Franco-Belgian bande dessinée comics |
| `adult-animation` | Rick and Morty, BoJack, Archer style |

## How Layers Combine

When generating an image, layers are assembled in order:

```
L0: Create a dramatic scene illustration for a text adventure game.
    High-resolution production asset in 16:9 widescreen format.

L1: Location: {location_name}
    Scene Description: {atmosphere}
    {interactive_elements}

L2: World context: {theme}, {tone}

L3: Mood: The atmosphere is {mood.tone}. {mood.lighting}.
    Color palette: {mood.color_palette}.

L4: Visual style (most important): {style}
    This style must be maintained consistently throughout.

L5: Composition: {technical.perspective} perspective, {technical.shot},
    {technical.camera}. {technical.effects}

L6: Critical constraints - the image must NOT include:
    - {anti_styles joined}
    - {quality_constraints joined}
```

## NPC Variant Generation

When adding NPCs to existing base images, the style must be preserved. The edit prompt includes:

1. The NPC description and placement
2. A style preservation requirement referencing L4
3. A brief anti-style list from L6

This ensures NPC variants maintain visual consistency with the base image.

## Testing Style Presets

1. Create or select a world with your style: `style: your-preset`
2. Generate images for multiple locations
3. Check for:
   - **Style consistency**: Do all images feel like the same visual style?
   - **Style drift**: Are any images pulling toward anti-styles?
   - **Mood alignment**: Does the lighting/color match the mood specification?
4. Adjust anti-styles if drift occurs

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Style drifting to photorealism | Add more anti-styles: "photorealistic", "hyperrealistic", "3D CGI" |
| Colors too saturated/muted | Adjust `mood.color_palette` with specific guidance |
| Lighting doesn't match | Be more specific in `mood.lighting` |
| Style inconsistent across locations | Strengthen L4 emphasis language |
| Wrong artistic medium | Add the unwanted medium to anti-styles |

## Reference

- **Quick Template**: See the template in this document (Creating Style Presets section above)
- **MPA Research**: `/ideas/modular-prompt-architecture.md`
- **Image Generator**: `/gaime_builder/core/image_generator.py`
