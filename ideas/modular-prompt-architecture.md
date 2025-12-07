# Modular Prompt Architecture (MPA) for Stylistically Coherent Game Asset Generation

## I. Executive Summary: Validation of the Layered Approach

### 1.1 The Imperative for Structured Prompting in Game Engines

The objective of generating high-fidelity, stylistically consistent visual assets for a text adventure game engine necessitates a systematic and structured approach to prompt engineering. In a development pipeline where asset quality and coherence across multiple locations are critical, relying on simple, unstructured text descriptions often results in keyword dilution and visually inconsistent outputs, a common pitfall in generative AI models. [1]

The proposed multi-layered methodology is robust and entirely consistent with advanced practices in prompt engineering, which advocates for segmenting instructions into distinct logical components such as Context, Focus, and Constraints. [2, 3, 4] For image generation, this segregation is paramount because the model must rigorously manage scene content against strict artistic constraints. The analysis confirms that segmenting the prompt into logical components—Meta-Context (L0), Content (L1), Context (L2), Aesthetic (L3/L4), Technical Constraints (L5), and Quality Control (L6)—is the most effective method for achieving repeatable, high-quality results. [5, 6]

A key system architectural benefit of this approach is the successful decoupling of **narrative elements** (L1 and L2) from **aesthetic control elements** (L3 and L4). Layers 1 and 2 function as dynamic *input variables* derived from the current game state (e.g., location details and descriptive environment), while Layers 3 and 4 serve as *fixed aesthetic templates* or reusable visual style sheets. This modularity allows the game engine to dramatically alter the visual identity of an entire game instance (e.g., swapping a "Victorian" theme for a "Cyberpunk" theme) by changing the L2, L3, and L4 strings, without requiring any alteration to the core generation logic for the L1 scene content. This separation is vital for system scalability, ensuring that specific details of a location, such as the lighting inside a "Library," do not interfere with or unintentionally override the consistent artistic style applied globally to the game world.

### 1.2 Introduction of the Refined Seven-Layer Model (MPA)

The initial five-layer framework is functionally sound. However, a production-level generative asset pipeline demands explicit layers for both meta-configuration and quality control. The analysis validates the descriptive layers and integrates mandatory control layers, resulting in the comprehensive **Modular Prompt Architecture (MPA)**, a seven-layer system optimized for **Nano Banana Pro** (the primary reference model for this specification):

0.  **L0: Meta-Context (Generation Parameters):** Model configuration, quality tier, and safety parameters.
1.  **L1: Content (Subject and Scene Focus):** The variable definition of the immediate scene and subjects.
2.  **L2: Context (World Definition and Environment):** Fixed, persistent narrative and material context for the entire world.
3.  **L3: Mood (Affective Tone and Lighting/Color):** The emotional and atmospheric filter, influencing light quality and color tone.
4.  **L4: Style (Artistic Medium and Rendering Technique):** The dominant aesthetic definition enforced through natural language emphasis.
5.  **L5: Technical (Composition, Camera, and Parameters):** Framing, perspective, and output format specifications.
6.  **L6: Negative Constraints (Quality Assurance and Artifact Removal):** The mandatory layer for negating technical flaws and enforcing L4 stylistic constraints, implemented as embedded instructions for API-based models.

> **Model Reference:** This specification is optimized for **Nano Banana Pro** (also known as Gemini 3 Pro Image Preview), which uses natural language understanding rather than explicit weighting syntax. Alternative models (Stable Diffusion, Midjourney, DALL-E) are referenced where syntax differs significantly.

---

## II. The Foundational Layered Prompting Architecture (MPA) in Detail

### 2.0 Layer 0: Meta-Context (Generation Parameters)

Layer 0 establishes the foundational generation context before any content is described. This layer sets expectations for the AI model about the type of output required and any global constraints.

Components of L0 include:

*   **Task Definition:** The overall generation task (e.g., "Create a dramatic, atmospheric scene illustration for a text adventure game").
*   **Quality Tier:** Production quality specification (e.g., "high-resolution production asset," "8K resolution").
*   **Output Format:** Aspect ratio and format requirements (e.g., "16:9 widescreen composition").
*   **Safety/Content Parameters:** Any content restrictions or guidelines for the generation.

For Nano Banana Pro, L0 is expressed as a clear opening statement that frames the entire prompt:

```
Create a dramatic, atmospheric scene illustration for a text adventure game.
This is a high-resolution production asset in 16:9 widescreen format.
```

> **GAIME Integration Note:** L0 parameters could be stored in `world.yaml` under a new `image_config` field, allowing per-world customization of generation parameters without code changes.

### 2.1 Layer 1: Content and Subject Definition (The Variable Core)

Layer 1 is the primary instruction defining the main visual elements of the location, such as objects, spatial arrangements, and subjects. For optimal fidelity, the generative prompt should always begin with this content (after L0), ensuring the main subject receives priority attention from the model. [6, 7] This layer contains the information that is dynamically changed for every location the player enters.

The example, "Library room, walls lined with book shelves, desk in the middle," provides clear nouns and essential visual details that establish the scene's geometry.

For Nano Banana Pro, L1 benefits from specific, concrete nouns and spatial relationships rather than abstract descriptions. The model's strong language understanding allows for natural, descriptive prose. [29]

### 2.2 Layer 2: World Context and Environment (The Narrative Anchor)

Layer 2 ensures structural and thematic cohesion across the entire game world. [8] This persistent, high-level context guarantees that regardless of the specific location, the material reality of the world remains constant.

Components of L2 include the Time Period (e.g., *Victorian era*), Dominant Materiality (e.g., *old wood, brass components*), Environmental State (e.g., *dusty and crooked but not broken*, *sleek and sterile*), and Persistent Light Source characteristics (e.g., *lit by candles*, *lit by buzzing neon*). The text string for L2 should be *fixed* and reused across every location prompt within a single game world instance. This creates a reusable 'Context Block' that anchors the world's persistent feel, reinforcing the necessary semantic information for the AI to maintain consistency. [5] The prompt segment, "Victorian era, old wood, dusty and crooked but not broken, lit by candles," is an exemplary Context Block.

> **GAIME Integration Note:** L2 maps directly to the existing `theme` and `tone` fields in `world.yaml`. Consider adding a dedicated `context_block` field for richer environmental specification.

### 2.3 Layer 3: Visual Mood and Affective Tone (The Emotional Filter)

Layer 3 governs the emotional atmosphere, light quality, and overall color scheme, translating narrative tension into visual atmosphere. [7, 9] It primarily employs evocative adjectives to instruct the generative model on the desired emotional response. [10]

This layer is composed of:

*   **Mood Adjectives:** Terms like *spooky, wistful, convivial, melancholic*. [7, 10, 11]
*   **Lighting Modifiers:** Specific descriptive terms that define shadow and depth, such as *dramatic chiaroscuro, volumetric fog*, or *soft golden hour lighting with long shadows*. [5, 7, 12]
*   **Color Palette:** Instructions like *cool tones* (to convey tranquility) or *vibrant, saturated tones* (to convey energy). [7, 9]

For **Nano Banana Pro**, mood emphasis is achieved through natural language reinforcement rather than numeric weighting. Instead of `(ominous:1.3)`, use phrases like "The atmosphere is deeply ominous" or "The most striking quality is the ominous mood that pervades every shadow." The model responds well to explicit prioritization language. [29, 30]

> **GAIME Integration Note:** L3 could be dynamically modified based on `game_state` flags (e.g., `in_danger`, `victory_near`) to shift mood without changing the base location description.

### 2.4 Layer 4: Stylistic Rendering and Medium (The Aesthetic Overdrive)

Layer 4 defines the entire artistic execution—the medium, artistic movement, or digital aesthetic (e.g., "Pixel Art," "Baroque Painting," "Cinematic Photorealism"). [15, 16] To ensure non-negotiable visual consistency, this layer must be fixed per game world and receive strong emphasis in the prompt.

Key components include:

*   **Medium:** (e.g., illustration, photo, oil on canvas, watercolor [7, 9]).
*   **Artistic Movement:** (e.g., Psychedelic, Art Deco, Impressionist [11, 15]).
*   **Digital Aesthetic:** (e.g., Digital painting, concept art, 16bit retro aesthetic, cinematic [16, 17, 18]).
*   **Rendering Engine Keywords:** For Nano Banana Pro, terms like *C4D rendering, occlusion render, V-Ray render* can influence the visual quality. [29]

To establish **style dominance** in Nano Banana Pro, use explicit priority language:

```
The artistic style is the most important aspect of this image: digital painting 
with rich textures and painterly brushstrokes. This style must be maintained 
consistently throughout the entire image.
```

> **Alternative Syntax (Stable Diffusion):** For SD-based models, use token weighting: `((Digital painting):1.4)`. For Midjourney, use `::2` suffix for emphasis.

### 2.5 Layer 5: Technical Parameters and Composition (The System Constraints)

Layer 5 dictates the technical constraints and narrative framing, effectively controlling the image composition and presentation. [18, 19]

Core components are:

*   **Format and Quality:** Aspect Ratio (16:9 [16]) and quality tags (8K resolution, high-quality).
*   **Camera Mechanics:** Specifies the shot composition (e.g., *cinematic wide shot, Establishing Shot, Close-Up* [19, 20]), camera angles (e.g., *Low Angle Shot, Birds-Eye-View* [19, 20]), and lens specifications (e.g., *24mm wide-angle lens* for breadth or *85mm telephoto lens* for portrait focus). [21]

This layer serves as a powerful instrument for visual storytelling. The engine can map compositional terms to narrative intention: utilizing a "Wide-Angle Establishing Shot" (24mm lens) for scene introductions (L2 context) and employing a "Close-Up" (85mm lens) with "Shallow Depth of Field" to draw attention to interactive or key L1 content elements. [20, 21]

For **Nano Banana Pro**, camera and lens specifications are understood naturally:

```
Shot composition: Medium wide shot from eye level, as if viewing the scene 
through a 35mm lens. Shallow depth of field with the foreground object in 
sharp focus.
```

### 2.6 Layer 6: Negative Constraints (Quality Assurance and Artifact Removal)

Layer 6 is a critical, mandatory component for production-ready asset generation. It provides explicit instructions to the AI regarding what features or artifacts *must* be excluded, ensuring quality assurance and preventing stylistic conflict. [22, 23]

This layer comprises standard boilerplate terms (to mitigate common technical flaws like blurring and artifacts) and dynamically injected anti-style terms (to actively deny aesthetics that conflict with L4).

#### 2.6.1 Implementation for Nano Banana Pro (Embedded Negatives)

Nano Banana Pro and similar API-based models (DALL-E, Gemini) do not have a separate negative prompt field. Instead, negative constraints must be **embedded within the main prompt** using explicit denial language. [29]

**Pattern for embedded negatives:**

```
Critical constraints - the image must NOT include:
- Any photorealistic or hyperrealistic rendering
- 3D CGI or Unreal Engine aesthetics  
- Watermarks, signatures, or text overlays
- Blurry or low-quality artifacts
- Distorted anatomy or architectural proportions
```

This approach is validated by the Nano Banana Pro community, which uses structured `negative_prompt` fields embedded in JSON-like prompt formats. [29]

> **Alternative Syntax (Stable Diffusion):** SD models accept a separate negative prompt parameter. Use the L6 content directly in that field.

---

## III. Achieving Inter-Location Consistency and Scalability

Generating consistent assets across a diverse game world requires technical enforcement beyond simple keyword inclusion.

### 3.1 Model-Specific Syntax Adaptation

Different image generation models require different approaches to achieve layer emphasis and style dominance.

**Table 1: Model-Specific Emphasis Techniques**

| Model | Weighting Syntax | Negative Prompt | Best Practice |
| :--- | :--- | :--- | :--- |
| **Nano Banana Pro** | Natural language emphasis ("The most important aspect is...") | Embedded in main prompt ("Must NOT include...") | Use structured prose; leverage real-world knowledge [29, 30] |
| **Stable Diffusion** | `(keyword:1.X)` or `keyword+++` | Separate negative prompt field | Explicit numeric weights; comprehensive negative list |
| **Midjourney** | `keyword::2` suffix | `--no keyword` parameter | Concise prompts; style references via `--sref` |
| **DALL-E 3** | Natural language emphasis | Embedded in main prompt | Detailed descriptions; avoid technical jargon |

For **Nano Banana Pro**, the recommended approach is to use **explicit priority statements** rather than symbolic weighting:

```
# Instead of: ((Digital painting):1.4), spooky, (dramatic lighting:1.2)

# Use:
The artistic style is paramount: this must be a digital painting with 
visible brushstrokes and rich textures. The mood is deeply spooky with 
dramatic, high-contrast lighting that creates long shadows.
```

> **GAIME Integration Note:** The `get_image_prompt()` function in `image_generator.py` could accept a `model_type` parameter to automatically adapt the prompt assembly strategy.

### 3.2 Style Emphasis Techniques for Nano Banana Pro

To achieve style dominance without numeric weighting, employ these natural language patterns:

1. **Priority Declarations:** "The most important aspect of this image is [L4 style]."
2. **Reinforcement Through Repetition:** Mention the style at both the beginning and end of the prompt.
3. **Explicit Constraints:** "This must be [style], not [anti-styles]."
4. **Transformation Language:** "Render this scene as if it were [style]." [29]

**Example priority declaration:**

```
Create a scene illustration. The artistic style is the defining characteristic: 
this is a digital painting in the style of detailed concept art, with visible 
brushwork, rich color saturation, and painterly atmosphere. Every element 
must adhere to this digital painting aesthetic.
```

### 3.3 Reference Image Techniques for Visual Consistency

Traditional seed management (using fixed seed values for reproducible outputs) is not available in most commercial API-based models including Nano Banana Pro. Instead, visual consistency across multiple generations is achieved through **reference image techniques**.

**Available approaches:**

1. **Image Editing Mode:** Generate a base image, then use image-to-image editing to add variations (e.g., adding NPCs to a scene while preserving the background). This maintains lighting, perspective, and style consistency.

2. **Style Reference Images:** Some models support style transfer from reference images. For Nano Banana Pro, this can be approximated by providing a reference image alongside the text prompt.

3. **Identity Preservation:** For character consistency across scenes, the Nano Banana Pro community uses `facelock_identity` patterns that explicitly request facial feature preservation. [29]

> **GAIME Integration Note:** The existing `generate_location_variants()` function in `image_generator.py` already implements the image editing approach for NPC variants. This pattern should be extended for any future consistency requirements.

**Example (NPC variant generation):**

```
Edit this image to add the following character while preserving the scene exactly:
[NPC description with appearance details]

Critical Requirements:
- PRESERVE the original scene's composition, lighting, colors, and atmosphere
- MATCH the artistic style and perspective of the original image
- Position the character naturally within the existing space
```

### 3.4 Fixed Style Blocks and World Configuration

Visual continuity is dependent on the consistent application of input variables. The combined strings of L2, L3, and L4 should be maintained as immutable 'Style Blocks' for every prompt within that specific game world instance. [5, 26]

Furthermore, the system must architecturally prevent the selection of contradictory L4 terms (e.g., combining "photorealism" with "cartoon"). [14] Contradictory constraints lead to significant dilution of the model's focus and unpredictable output.

**Recommended Style Block structure:**

```yaml
# world.yaml - Style Block configuration
style_block:
  l2_context: "Victorian era, old wood, dusty and crooked but not broken, lit by candles"
  l3_mood: "atmospheric, mysterious, unsettling yet compelling"
  l4_style: "digital painting, detailed concept art, painterly brushstrokes, rich textures"
  l6_anti_styles: 
    - "photorealistic"
    - "3D CGI"
    - "anime"
    - "cartoon"
```

### 3.5 Programmatic Layer Assembly

For game engines with dynamic state, layers can be programmatically assembled based on runtime conditions.

**Pseudocode for dynamic prompt assembly:**

```python
def build_mpa_prompt(
    location: Location,
    world: World,
    game_state: GameState
) -> str:
    """
    Assemble a complete MPA prompt from game state.
    
    GAIME Integration: This function could replace the current 
    get_image_prompt() implementation in image_generator.py
    """
    
    # L0: Meta-Context (fixed per world)
    l0 = f"Create a dramatic, atmospheric scene illustration for a text adventure game. "
    l0 += f"High-resolution production asset in 16:9 widescreen format."
    
    # L1: Content (dynamic per location)
    l1 = f"Location: {location.name}. {location.atmosphere}"
    
    # L2: Context (fixed per world)
    l2 = f"World context: {world.style_block.l2_context}"
    
    # L3: Mood (can be dynamic based on game state)
    base_mood = world.style_block.l3_mood
    if game_state.flags.get("in_danger"):
        l3 = f"Mood: intensely {base_mood}, with heightened tension and urgency"
    elif game_state.flags.get("victory_near"):
        l3 = f"Mood: {base_mood}, with a subtle sense of hope emerging"
    else:
        l3 = f"Mood: {base_mood}"
    
    # L4: Style (fixed per world, with emphasis)
    l4 = f"Artistic style (most important): {world.style_block.l4_style}. "
    l4 += "This style must be maintained consistently throughout the image."
    
    # L5: Technical (mostly fixed)
    l5 = "First-person perspective, medium wide shot, 8K resolution."
    
    # L6: Negative constraints (embedded)
    anti_styles = ", ".join(world.style_block.l6_anti_styles)
    l6 = f"Critical: The image must NOT include {anti_styles}, "
    l6 += "watermarks, text, blurry artifacts, or distorted proportions."
    
    # Assemble in optimal order for Nano Banana Pro
    return f"{l0}\n\n{l1}\n\n{l2}\n\n{l3}\n\n{l4}\n\n{l5}\n\n{l6}"
```

---

## IV. Prompt Taxonomy and Keyword Catalogs

### 4.1 Layer 3 Keyword Index: Affect and Mood Modifiers

These terms provide precise control over the emotional and visual filter of the scene:

*   **Lighting Modifiers:** Effective lighting keywords define shadow, volume, and atmosphere. Examples include: *dramatic chiaroscuro, volumetric light, rim lighting, god rays, soft ambient light*, and specific time references like *golden hour* or *overcast*. [5, 7, 12]
*   **Color Palette Terms:** These control the image's emotional temperature and intensity. Terms include: *saturated, vibrant, muted, pastel, monochromatic*. [7, 9] Specifying *cool tones* or *warm tones* is an efficient method for influencing the overall feeling of tranquility or energy. [9]

**Nano Banana Pro Specific Terms:** The model responds well to photography-inspired lighting terms: *soft flash lighting, studio lighting, natural window light, neon glow, cinematic lighting*. [29]

### 4.2 Layer 4 Style Reference Library (Aesthetic Taxonomy)

This taxonomy provides the vocabulary necessary to define the artistic engine and ensure consistency.

**Table 2: Style Reference and Negative Constraint Catalog**

| Target Style | L4 Keywords (Nano Banana Pro) | L4 Qualifiers | Mandatory L6 Anti-Style Terms |
| :--- | :--- | :--- | :--- |
| **Cinematic Photorealism** | cinematic still, photorealistic, film photography | 8K, ultra-detailed, 35mm lens, shallow depth of field | cartoon, illustration, drawing, pixel art, sketch, painterly, anime |
| **Digital Painting** | digital painting, concept art, painterly | artistic, rich textures, visible brushstrokes | photorealistic, 3D, CGI, unreal engine, hyperrealism |
| **Retro Pixel Art** | low-resolution pixel art, 8bit aesthetic | 16bit, dithering, sprite art, retro RPG | 3D, CGI, realistic, high resolution, smooth shading |
| **Fine Art (Oil)** | masterpiece oil painting, classical fine art | heavy brushstrokes, chiaroscuro, baroque | digital art, cartoon, modern, minimalist |
| **3D Stylized** | C4D rendering, 3D illustration, occlusion render | soft studio lighting, pastel colors, toy-like | photorealistic, gritty, dark, hand-drawn |
| **Vintage Photography** | low-quality disposable camera, film grain | nostalgic, candid snapshot, slight blur | digital, clean, modern, HDR |

### 4.3 Layer 5 Compositional Toolkit (Cinematic Control)

Layer 5 allows for the sophisticated framing of game assets, simulating a professional camera operator. [19]

*   **Camera Shot Size:** Defines the scope: *Extreme Wide Shot* (landscapes), *Establishing Shot* (rooms), *Medium Shot, Close-Up* (key objects). [20]
*   **Camera Angle:** Controls narrative perspective: *Eye Level Shot* (neutral), *Low Angle Shot* (imposing), *High Angle Shot* (vulnerability), *Birds-Eye-View* (map/overview). [19, 20]
*   **Lens and Focus:** Direct control over depth and field: use *24mm wide-angle lens* for capturing the breadth of a scene and *85mm telephoto lens* for portraiture or emphasizing objects. [21] Focus techniques such as *Shallow Depth of Field* or *Deep Focus* guide the visual hierarchy. [19, 20]

**Nano Banana Pro Camera Keywords:** [29, 30]
- Lens types: *35mm lens, 50mm lens, 85mm telephoto, wide-angle, fisheye*
- Focus: *shallow depth of field, deep focus, soft focus on [subject]*
- Film effects: *35mm film grain, cinematic color grading, lens flare*

---

## V. Advanced Quality Control: The Negative Prompting Strategy (Layer 6)

The Negative Constraints layer (L6) serves as the primary mechanism for quality control, instructing the model to avoid generating specific technical flaws and stylistic elements. [23, 27]

### 5.1 Standard Quality and Artifact Removal (Boilerplate)

Every prompt must incorporate a boilerplate list of technical flaws to ensure crisp, clean, professional assets. [22, 23]

**Table 3: Boilerplate Negative Constraint List (Quality Assurance)**

| Flaw Category | Targeted Terms | Reasoning |
| :--- | :--- | :--- |
| **Technical Quality** | worst quality, low quality, lowres, blurry, jpeg artifacts, compression artifacts, noisy, grainy, out of focus | Removes common technical output imperfections. [22, 23] |
| **Unwanted Annotations** | watermark, signature, text, logo, cropped, simple background | Ensures clean, professional assets ready for production use. [22, 28] |
| **Structural/Anatomy** | bad anatomy, poorly drawn hands, deformed, disfigured, extra limbs, distorted proportions | Prevents model errors in rendering of characters and architecture. [25, 28] |
| **Style Interference** | amateur, poorly drawn, generic, bad art | General terms to enforce artistic competence. [23] |

### 5.2 Anatomical and Structural Flaw Mitigation

Specific terms are required to prevent structural inconsistencies, even in inanimate architectural elements: *bad proportions, deformed structures, asymmetrical, inverted, impossible geometry*. [25, 28] This ensures the background architecture and objects maintain high fidelity.

### 5.3 Style-Specific Negative Constraints (The Anti-Style List)

The critical function of L6 is to enforce L4 style choices by actively denying conflicting aesthetics. For example, if the L4 specification is "Digital Painting," the L6 list must include: *photorealistic, realistic, 3D, CGI, hyperrealism*. [24, 25] Conversely, if L4 is "Cinematic Photorealism," L6 must contain terms that forbid artistic interpretation, such as *cartoon, sketch, illustration, pixelated*. [25]

### 5.4 Embedded Negatives for API Models (Nano Banana Pro Pattern)

For models without a dedicated negative prompt field, L6 constraints must be embedded in the main prompt. The Nano Banana Pro community has established effective patterns: [29]

**Pattern 1: Explicit Constraint Block**
```
Critical constraints - the image must NOT include:
- Any photorealistic or hyperrealistic elements
- 3D CGI or game engine rendering
- Watermarks, signatures, or text overlays
- Blurry, grainy, or low-quality artifacts
- Distorted anatomy or impossible architecture
```

**Pattern 2: JSON-Style Structured Format**
```json
{
  "negative_prompt": "no photorealism, no 3D CGI, no blurry face, 
    no distorted hands, no extra limbs, no watermark, no low resolution, 
    no muted colors, no AI artifacts"
}
```

**Pattern 3: Inline Denial**
```
Style: Digital painting (NOT photorealistic, NOT 3D rendered, NOT cartoon)
```

> **GAIME Integration Note:** The embedded negative pattern should be added to `get_image_prompt()` in `image_generator.py`. Consider making the anti-style list configurable per world in `world.yaml`.

---

## VI. Case Studies and Implementation Formulas

The following examples demonstrate the full application of the MPA structure, optimized for **Nano Banana Pro** with natural language emphasis and embedded negative constraints.

### 6.1 Case Study 1: The Victorian Library (Digital Painting Style)

**Goal:** High detail, spooky mood, enforced digital painting aesthetic.

**Complete Nano Banana Pro Prompt:**

```
Create a dramatic, atmospheric scene illustration for a text adventure game.
High-resolution production asset in 16:9 widescreen format.

Location: Library room with floor-to-ceiling bookshelves lining every wall. 
A heavy oak desk dominates the center of the room, with an open book that 
seems to emit a faint, otherworldly glow. Ancient tomes are packed tightly 
on the shelves, their leather spines cracked with age.

World context: Victorian era, old wood paneling, dusty and crooked but not 
broken, lit by flickering candles that cast dancing shadows.

Mood: The atmosphere is deeply spooky and melancholic. High contrast lighting 
creates dramatic chiaroscuro effects, with pools of candlelight surrounded by 
oppressive darkness. The mood is hyper-detailed and unsettling.

Artistic style (most important): This must be a digital painting in the style 
of detailed concept art. Rich textures, visible painterly brushstrokes, and 
artistic color saturation. The digital painting aesthetic is paramount and 
must be maintained throughout the entire image.

Composition: Medium wide shot from eye level, first-person perspective as if 
the viewer has just entered the room. Soft focus draws attention to the 
glowing book on the desk. 8K resolution quality.

Critical constraints - the image must NOT include:
- Any photorealistic or hyperrealistic rendering
- 3D CGI or Unreal Engine aesthetics
- Watermarks, signatures, or text overlays
- Blurry or low-quality artifacts
- Modern elements that break the Victorian setting
```

> **Alternative Syntax (Stable Diffusion):**
> - Positive: `Library room, bookshelves, oak desk, glowing book, Victorian era, candlelit, (dramatic chiaroscuro:1.2), spooky, ((digital painting):1.4), concept art, rich textures, medium wide shot, 8K`
> - Negative: `photorealistic, 3D, CGI, hyperrealism, watermark, blurry, modern`

### 6.2 Case Study 2: Cyberpunk Alley (Neon Noir Cinematic Style)

**Goal:** Gritty, ultra-realistic look with strong light/shadow play.

**Complete Nano Banana Pro Prompt:**

```
Create a dramatic, atmospheric scene illustration for a text adventure game.
High-resolution production asset in 21:9 ultra-widescreen cinematic format.

Location: A narrow, rain-slicked alleyway between towering megastructures. 
Neon signs flicker erratically, their reflections fragmenting across wet 
pavement. Discarded data chips and tech debris litter the ground. Steam 
rises from grates, diffusing the harsh neon glow.

World context: Near-future cyberpunk metropolis, rainy night, high-tech 
urban sprawl with visible decay. Chrome and rust coexist. The air feels 
thick with humidity and the buzz of electronics.

Mood: The atmosphere is gritty and intensely cinematic. Ultra-vibrant neon 
colors—magenta, cyan, electric blue—cut through deep, inky shadows. The 
mood is noir-inspired with palpable tension and urban alienation.

Artistic style (most important): This must be cinematic photorealism with 
the quality of a high-budget film still. 35mm film grain effect, V-Ray 
render quality, detailed reflections on wet surfaces. The photorealistic 
cinematic quality is the defining characteristic of this image.

Composition: Low angle shot emphasizing the towering buildings, taken with 
a 35mm wide-angle lens. Shallow depth of field with rain droplets in soft 
focus in the foreground. Detailed reflections on every wet surface.

Critical constraints - the image must NOT include:
- Cartoon, illustration, or painterly styles
- Anime or stylized aesthetics
- Watermarks or text overlays
- Clean or dry surfaces (everything should be wet)
- Bright daylight or cheerful elements
```

### 6.3 Case Study 3: Fantasy Dungeon (Top-Down Pixel Art)

**Goal:** Highly stylized, low-fidelity 16bit retro aesthetic.

**Complete Nano Banana Pro Prompt:**

```
Create a retro video game scene for a classic RPG dungeon crawler.
Output in 1:1 square format, optimized for pixel art rendering.

Location: A stone dungeon corridor with mossy walls carved with ancient 
runes. A single torch mounted on the wall provides the only light source. 
A wooden treasure chest sits in a shadowy corner, its iron bands rusted.

World context: Medieval fantasy setting with a damp, underground atmosphere. 
The dungeon feels ancient and forgotten, with water seeping through cracks 
in the stonework.

Mood: Dark ambient lighting with warm torch glow against cool stone. Muted 
earth tones—browns, grays, mossy greens—create a mysterious and slightly 
ominous atmosphere. Low color saturation maintains the retro aesthetic.

Artistic style (most important): This MUST be low-resolution pixel art in 
the authentic 16-bit retro RPG aesthetic. Visible pixels, limited color 
palette, dithering techniques for shading, 2D sprite art style. The pixel 
art aesthetic is absolutely essential—this should look like a scene from 
a classic SNES or Genesis RPG. No smooth gradients or high-resolution details.

Composition: Birds-eye-view, top-down perspective typical of classic RPGs. 
Small scale showing the dungeon tile grid. The composition should feel like 
a game screenshot.

Critical constraints - the image must NOT include:
- 3D rendering or CGI of any kind
- Realistic or photorealistic elements
- High resolution or smooth shading
- Watercolor, oil painting, or traditional art styles
- Modern UI elements or photographic quality
- Smooth gradients (use dithering instead)
```

### 6.4 Case Study 4: High School Comedy (Stylized Digital Art)

**Goal:** Light-hearted, nostalgic aesthetic for a comedy game setting.

**Complete Nano Banana Pro Prompt:**

```
Create an atmospheric scene illustration for a comedic text adventure game.
High-resolution production asset in 16:9 widescreen format.

Location: A high school cafeteria with folding tables pushed against the 
walls. The serving counter gleams under fluorescent lights. Dust motes 
dance in sunbeams hitting the stainless steel surfaces. The lingering 
scent of mystery meat seems almost visible in the air.

World context: 1990s American high school, nostalgic and slightly absurd. 
Everything has that institutional quality—linoleum floors, plastic chairs, 
bulletin boards with outdated posters. The atmosphere balances mundane 
reality with comedic exaggeration.

Mood: The atmosphere is awkward, rebellious, and deeply nostalgic. Warm, 
slightly overexposed lighting suggests memory or daydream. Colors are 
saturated but not garish—the palette of a coming-of-age film.

Artistic style (most important): Stylized digital illustration with a 
warm, inviting quality. Slightly exaggerated proportions for comedic effect. 
Rich, saturated colors with soft lighting. The style should evoke indie 
animation or graphic novel aesthetics—expressive and character-driven.

Composition: Medium shot at eye level, first-person perspective of someone 
entering the cafeteria. Natural lighting from large windows mixing with 
harsh fluorescents. 8K resolution.

Critical constraints - the image must NOT include:
- Dark, horror, or thriller aesthetics
- Photorealistic or gritty rendering
- Modern smartphones or post-2000s technology
- Violent or disturbing elements
- Anime or manga style
```

---

## VII. Evaluation Metrics for Generated Assets

Consistent asset quality requires systematic evaluation. The following metrics should be applied to generated images before acceptance into the production pipeline.

### 7.1 Style Adherence Score

Evaluate how faithfully the generated image matches the L4 style specification:

| Score | Criteria |
| :--- | :--- |
| **5 - Excellent** | Style is immediately recognizable and consistent throughout; no conflicting elements |
| **4 - Good** | Style is dominant with minor inconsistencies in details |
| **3 - Acceptable** | Style is present but some elements drift toward other aesthetics |
| **2 - Poor** | Mixed styles create visual confusion; regeneration recommended |
| **1 - Failed** | Wrong style entirely; prompt revision required |

### 7.2 Content Accuracy Checklist

Verify that L1 content elements are present and correctly rendered:

- [ ] Primary subject/location is clearly depicted
- [ ] Key objects mentioned in prompt are visible
- [ ] Spatial relationships match description
- [ ] No hallucinated elements that contradict the prompt
- [ ] Interactive elements (exits, items) are naturally integrated

### 7.3 Compositional Coherence

Assess L5 technical execution:

- [ ] Correct aspect ratio (16:9, 1:1, etc.)
- [ ] Appropriate camera angle and shot size
- [ ] Proper depth of field as specified
- [ ] No cropping of important elements
- [ ] Visual hierarchy guides viewer attention correctly

### 7.4 Cross-Generation Consistency

For worlds with multiple location images, evaluate consistency across the set:

- [ ] Color palette remains consistent with L2/L3 specification
- [ ] Lighting quality matches across all locations
- [ ] Artistic style (L4) is uniform
- [ ] Material rendering (wood, stone, metal) is consistent
- [ ] No jarring stylistic shifts between adjacent locations

> **GAIME Integration Note:** Consider implementing an automated evaluation pipeline that flags images for human review based on these criteria. This could be integrated into the world builder workflow.

---

## VIII. GAIME Integration Roadmap

This section outlines how the MPA framework can be integrated into the GAIME text adventure engine for future development.

### 8.1 World.yaml Schema Extensions

Extend the existing `world.yaml` schema to support MPA layer configuration:

```yaml
# Proposed additions to world.yaml

# L0: Meta-Context configuration
image_config:
  model: "nano-banana-pro"  # or "stable-diffusion", "midjourney"
  quality_tier: "production"  # or "draft", "concept"
  aspect_ratio: "16:9"
  
# Style Block (L2 + L3 + L4 + L6 combined)
style_block:
  # L2: World Context (reused for every location)
  context: |
    Victorian era, old wood paneling, dusty and crooked but not broken,
    lit by flickering candles that cast dancing shadows.
  
  # L3: Base Mood (can be modified by game state)
  mood:
    base: "atmospheric, mysterious, unsettling yet compelling"
    danger_modifier: "intensely threatening, urgent"
    victory_modifier: "hopeful, with light breaking through"
  
  # L4: Style Definition
  style: |
    Digital painting in the style of detailed concept art. Rich textures,
    visible painterly brushstrokes, and artistic color saturation.
  
  # L6: Anti-Style List
  anti_styles:
    - "photorealistic"
    - "3D CGI"
    - "anime"
    - "cartoon"
    - "hyperrealism"
  
  # L6: Quality Constraints (boilerplate)
  quality_constraints:
    - "watermarks"
    - "signatures"
    - "text overlays"
    - "blurry artifacts"
    - "distorted proportions"
```

### 8.2 image_generator.py Refactoring Outline

The current `get_image_prompt()` function can be refactored to use MPA layers:

```python
# Proposed refactoring for backend/app/llm/image_generator.py

def build_mpa_prompt(
    location_name: str,
    atmosphere: str,
    world_config: WorldConfig,  # Contains style_block from world.yaml
    game_state: Optional[GameState] = None,
    context: Optional[LocationContext] = None
) -> str:
    """
    Build a complete MPA-structured prompt for image generation.
    
    This replaces the current get_image_prompt() function with a more
    modular, configurable approach based on the MPA framework.
    """
    layers = []
    
    # L0: Meta-Context
    layers.append(build_l0_meta(world_config.image_config))
    
    # L1: Content (dynamic per location)
    layers.append(build_l1_content(location_name, atmosphere, context))
    
    # L2: World Context (fixed per world)
    layers.append(f"World context: {world_config.style_block.context}")
    
    # L3: Mood (can be dynamic)
    layers.append(build_l3_mood(world_config.style_block.mood, game_state))
    
    # L4: Style (fixed per world, with emphasis)
    layers.append(build_l4_style(world_config.style_block.style))
    
    # L5: Technical (from image_config)
    layers.append(build_l5_technical(world_config.image_config))
    
    # L6: Negative Constraints (embedded for Nano Banana Pro)
    layers.append(build_l6_negatives(
        world_config.style_block.anti_styles,
        world_config.style_block.quality_constraints
    ))
    
    return "\n\n".join(layers)
```

### 8.3 Variant Generation Strategy

The existing `generate_location_variants()` function aligns well with MPA principles. For NPC variants:

1. **Base Image:** Generate using full L0-L6 prompt (no conditional NPCs)
2. **Variant Images:** Use image editing mode with simplified prompt:
   - Reference the base image
   - Specify only the NPC to add (partial L1 update)
   - Emphasize preservation of L2/L3/L4 style

This approach is already implemented in `get_edit_prompt()` and should be maintained.

### 8.4 Future Enhancements

1. **Dynamic L3 Modulation:** Implement game state hooks that automatically adjust mood based on flags
2. **Style Library:** Create a library of pre-defined style blocks for common game genres
3. **Evaluation Pipeline:** Implement automated quality checks based on Section VII metrics
4. **Multi-Model Support:** Abstract the prompt assembly to support SD, Midjourney, and DALL-E syntax

---

## References

### Primary Sources (Nano Banana Pro)

29. ZeroLu, "Awesome Nano Banana Pro - Curated prompts and examples," GitHub Repository, 2025. [https://github.com/ZeroLu/awesome-nanobanana-pro](https://github.com/ZeroLu/awesome-nanobanana-pro)

30. Google, "Prompting tips for Nano Banana Pro," Google Blog, 2025. [https://blog.google/products/gemini/prompting-tips-nano-banana-pro/](https://blog.google/products/gemini/prompting-tips-nano-banana-pro/)

31. fofr, "Nano Banana Pro Guide - Practical prompting techniques," 2025. [https://www.fofr.ai/nano-banana-pro-guide](https://www.fofr.ai/nano-banana-pro-guide)

### General Prompt Engineering

1. Scenario, "AI-Powered Content Generation Platform," [https://www.scenario.com/](https://www.scenario.com/)

2. Reddit r/PromptEngineering, "Beyond Best Practices: The Layered Prompt Structure That Adapts as It Works," 2025. [https://www.reddit.com/r/PromptEngineering/comments/1mlnm73/](https://www.reddit.com/r/PromptEngineering/comments/1mlnm73/)

3. DEV Community, "How to Write Better Prompts: A Simple 3-Part Formula," [https://dev.to/rijultp/how-to-write-better-prompts-a-simple-3-part-formula-37cn](https://dev.to/rijultp/how-to-write-better-prompts-a-simple-3-part-formula-37cn)

4. Reddit r/PromptEngineering, "The 3-layer structure I use instead of one big prompt," [https://www.reddit.com/r/PromptEngineering/comments/1oo6fb8/](https://www.reddit.com/r/PromptEngineering/comments/1oo6fb8/)

5. Printful Blog, "How to write prompts for AI art (with examples)," [https://www.printful.com/blog/prompts-for-ai-art](https://www.printful.com/blog/prompts-for-ai-art)

6. LetsEnhance, "How to write AI image prompts like a pro," Oct 2025. [https://letsenhance.io/blog/article/ai-text-prompt-guide/](https://letsenhance.io/blog/article/ai-text-prompt-guide/)

### Style and Aesthetics

7. Midjourney Documentation, "Prompt Basics," [https://docs.midjourney.com/hc/en-us/articles/32023408776205-Prompt-Basics](https://docs.midjourney.com/hc/en-us/articles/32023408776205-Prompt-Basics)

8. Lovart, "AI Illustration Prompting Mastery: 100+ Proven Formulas," 2025. [https://www.lovart.ai/blog/ai-illustration-prompts](https://www.lovart.ai/blog/ai-illustration-prompts)

9. Zapier, "70+ AI art styles to use in your AI prompts," [https://zapier.com/blog/ai-art-styles/](https://zapier.com/blog/ai-art-styles/)

10. Student and Writer, "Profound list of 1000 adjectives for AI Art," [https://studentandwriter.com/2023/04/01/list-of-1000-adjectives-no-repeats/](https://studentandwriter.com/2023/04/01/list-of-1000-adjectives-no-repeats/)

11. David Ocean (Medium), "AI Image Generation Prompt Engineering," [https://medium.com/@david-ocean/ai-image-generation-prompt-engineering](https://medium.com/@david-ocean/ai-image-generation-prompt-engineering)

12. CinemaFlow AI, "Prompt Engineering," [https://www.cinemaflow.ai/prompt-engineering](https://www.cinemaflow.ai/prompt-engineering)

### Model-Specific Techniques (Stable Diffusion)

13. getimg.ai, "Guide to Stable Diffusion Prompt Weights," [https://getimg.ai/guides/guide-to-stable-diffusion-prompt-weights](https://getimg.ai/guides/guide-to-stable-diffusion-prompt-weights)

14. Portkey, "Prompt Engineering for Stable Diffusion," [https://portkey.ai/blog/prompt-engineering-for-stable-diffusion/](https://portkey.ai/blog/prompt-engineering-for-stable-diffusion/)

### Art Styles and Mediums

15. Adobe Firefly, "7 art styles for AI prompts," [https://www.adobe.com/products/firefly/discover/art-style-prompts-for-ai.html](https://www.adobe.com/products/firefly/discover/art-style-prompts-for-ai.html)

16. Clipdrop, "Text to image," [https://clipdrop.co/text-to-image](https://clipdrop.co/text-to-image)

17. Easy-Peasy AI, "Pixel Art Adventure Landscape," [https://easy-peasy.ai/ai-image-generator/images/pixel-art-adventure-landscape-game-level-selection](https://easy-peasy.ai/ai-image-generator/images/pixel-art-adventure-landscape-game-level-selection)

18. YouTube, "Ultimate Guide to Cinematic & Photorealistic AI Image Prompts," [https://www.youtube.com/watch?v=HWOLsh-7ZHQ](https://www.youtube.com/watch?v=HWOLsh-7ZHQ)

### Composition and Camera Techniques

19. Google Cloud Blog, "Ultimate prompting guide for Veo 3.1," [https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1)

20. ARTSMART AI, "Prompt Style: Camera Shots and Angles," [https://artsmart.ai/docs/camera-shots-and-angles/](https://artsmart.ai/docs/camera-shots-and-angles/)

21. Ecomtent, "The Impact of Prompting Different Camera Lenses," [https://www.ecomtent.ai/blog-page/the-impact-of-prompting-different-camera-lenses-in-ai-image-generation](https://www.ecomtent.ai/blog-page/the-impact-of-prompting-different-camera-lenses-in-ai-image-generation)

### Negative Prompting

22. Aiarty, "200+ Best Stable Diffusion Negative Prompts with Examples," [https://www.aiarty.com/stable-diffusion-prompts/stable-diffusion-negative-prompt.htm](https://www.aiarty.com/stable-diffusion-prompts/stable-diffusion-negative-prompt.htm)

23. Stable Diffusion Art, "How to use negative prompts?" [https://stable-diffusion-art.com/how-to-use-negative-prompts/](https://stable-diffusion-art.com/how-to-use-negative-prompts/)

24. ClickUp, "120+ Stable Diffusion Negative Prompts to Improve AI Art," 2025. [https://clickup.com/blog/stable-diffusion-negative-prompts/](https://clickup.com/blog/stable-diffusion-negative-prompts/)

25. Segmind Blog, "Best Negative Prompts for Stable Diffusion," [https://blog.segmind.com/best-negative-prompts-in-stable-diffusion/](https://blog.segmind.com/best-negative-prompts-in-stable-diffusion/)

### Consistency and Character Design

26. Medium (Design Bootcamp), "How to Design Consistent AI Characters with Prompts," 2025. [https://medium.com/design-bootcamp/how-to-design-consistent-ai-characters-with-prompts-diffusion-reference-control-2025](https://medium.com/design-bootcamp/how-to-design-consistent-ai-characters-with-prompts-diffusion-reference-control-2025)

27. getimg.ai, "Guide to Negative Prompts in Stable Diffusion," [https://getimg.ai/guides/guide-to-negative-prompts-in-stable-diffusion](https://getimg.ai/guides/guide-to-negative-prompts-in-stable-diffusion)

28. Johnny the Developer (Medium), "Negative Prompts for Perfect AI Image Generation," [https://medium.com/@johnnythedeveloper/negative-prompts-for-perfect-ai-image-generation](https://medium.com/@johnnythedeveloper/negative-prompts-for-perfect-ai-image-generation)

---

*Document revised: December 2025*
*Primary model reference: Nano Banana Pro (Gemini 3 Pro Image Preview)*
*Target integration: GAIME Text Adventure Engine*
