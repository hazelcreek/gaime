# Style Presets - Quick Reference for AI Authoring

This folder contains visual style presets for GAIME's image generation system. Each preset defines how locations should be rendered visually.

> **Full Documentation**: See `/docs/STYLE_AUTHORING.md` for complete MPA architecture details.

## Creating a New Preset

Create a new YAML file in this folder (e.g., `spaghetti-western.yaml`).

### Required Template

```yaml
# {preset-name}.yaml - {Style Name} style preset
# Brief description of the aesthetic

name: "{Human-Readable Style Name}"
description: "{1-2 sentence description of the aesthetic and when to use it}"

# L3: Mood - Emotional and atmospheric qualities
mood:
  tone: "{emotional keywords: e.g., gritty, whimsical, tense, dreamy}"
  lighting: "{lighting description: e.g., harsh shadows, soft diffused, neon glow}"
  color_palette: "{color guidance: e.g., desaturated with red accents, warm earth tones}"

# L4: Style - Artistic medium (MOST IMPORTANT LAYER)
style: |
  {Detailed description of the artistic style. This is the most critical section.
  Be specific about the rendering technique, artistic influences, and visual
  qualities. Include a statement like "The artistic style is paramount" to
  emphasize consistency. 3-5 sentences.}

# L5: Technical - Composition and camera
technical:
  perspective: "{first-person | third-person | top-down | isometric}"
  shot: "{wide shot | medium wide | medium | close-up}"
  camera: "{eye level | low angle | high angle | dutch angle}"
  effects: "{optional effects: film grain, vignette, glow, etc.}"

# L6: Anti-styles - What to AVOID (prevents style drift)
anti_styles:
  - "{conflicting style 1: e.g., photorealistic}"
  - "{conflicting style 2: e.g., cartoon}"
  - "{conflicting style 3: e.g., anime}"
  # Add 5-8 anti-styles that would conflict with your target aesthetic

# L6: Quality constraints - Technical flaws to prevent
quality_constraints:
  - "watermarks or signatures"
  - "blurry or low-quality artifacts"
  - "distorted proportions"
  - "{any style-specific quality issues}"
```

## Layer Explanations

| Layer | Purpose | Tips |
|-------|---------|------|
| **L3: Mood** | Emotional atmosphere | Use evocative adjectives; describe lighting and color feel |
| **L4: Style** | Artistic rendering | Most important! Be very specific about the visual technique |
| **L5: Technical** | Camera/composition | Usually `first-person` and `medium wide shot` for games |
| **L6: Anti-styles** | What to exclude | Critical for consistency - list styles that would clash |

## Anti-Style Strategy

Anti-styles prevent the AI from drifting to conflicting aesthetics. For each preset:

1. **Identify opposite aesthetics**: If your style is "painterly," add "photorealistic"
2. **Block adjacent styles that could blend**: If "noir," block "anime" and "fantasy"
3. **Include 5-8 anti-styles** for robust style enforcement

## Naming Conventions

- **Filename**: lowercase with hyphens (e.g., `spaghetti-western.yaml`)
- **name field**: Human-readable title (e.g., `"Spaghetti Western"`)
- **Keep names descriptive** but concise

## Example: Creating "Spaghetti Western" Style

```yaml
# spaghetti-western.yaml - Spaghetti Western style preset
# 1960s Italian Western film aesthetic with dust, sun, and moral ambiguity

name: "Spaghetti Western"
description: "1960s Italian Western film aesthetic inspired by Sergio Leone. Dusty landscapes, extreme close-ups, and moral ambiguity under harsh sunlight."

mood:
  tone: "tense, sun-baked, morally ambiguous, dramatic"
  lighting: "harsh midday sun, deep shadows under hats and in doorways, golden dust in the air"
  color_palette: "sun-bleached earth tones, dusty yellows, burnt oranges, deep shadows, occasional blood red"

style: |
  Cinematic style inspired by 1960s Spaghetti Western films, particularly
  Sergio Leone's work. Harsh desert lighting with strong shadows. Dust
  particles visible in sunbeams. Weathered textures on everything - wood,
  leather, skin. The composition should feel like a widescreen film frame.
  The artistic style is paramount and must evoke classic Italian Westerns.

technical:
  perspective: "first-person"
  shot: "wide establishing shots or dramatic medium close-ups"
  camera: "eye level or low angle for dramatic effect"
  effects: "film grain, dust particles, heat haze, lens flare from sun"

anti_styles:
  - "modern or contemporary"
  - "lush green landscapes"
  - "anime or cartoon"
  - "dark or gothic"
  - "futuristic or sci-fi"
  - "clean or polished"
  - "rainy or wet"

quality_constraints:
  - "watermarks or signatures"
  - "blurry or low-quality artifacts"
  - "modern elements (cars, electricity)"
  - "green lush vegetation"
  - "cold blue lighting"
```

## Testing Your Preset

After creating a preset:

1. Reference it in a world's `world.yaml`: `style: your-preset-name`
2. Generate images for that world's locations
3. Verify visual consistency across multiple locations
4. Adjust anti-styles if you see style drift

## Existing Presets

| Preset | Best For |
|--------|----------|
| `classic-fantasy` | Traditional fantasy adventures (DEFAULT) |
| `dark-fantasy` | Gothic, horror-tinged fantasy |
| `noir` | Detective mysteries, 1940s settings |
| `cyberpunk` | Sci-fi dystopia, neon-lit futures |
| `anime` | Japanese animation style adventures |
| `watercolor` | Dreamy, whimsical, gentle stories |
| `childrens-book` | Age-appropriate, friendly adventures |
| `horror` | Mature horror, psychological dread |
| `steampunk` | Victorian-era industrial fantasy |
| `pixel-art` | Retro gaming, 16-bit nostalgia |
| `photorealistic` | Grounded, realistic settings |
| `comic-book` | Action-packed graphic novel style |
| `spaghetti-western` | 1960s Italian Western films, Sergio Leone style |
| `teen-comedy` | High school comedy, 80s-90s teen movies |
| `simpsons` | Simpsons-style cartoon aesthetic |
