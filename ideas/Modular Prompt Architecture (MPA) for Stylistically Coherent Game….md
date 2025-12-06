# Modular Prompt Architecture (MPA) for Stylistically Coherent Game Asset Generation

## I. Executive Summary: Validation of the Layered Approach

### 1.1 The Imperative for Structured Prompting in Game Engines

The objective of generating high-fidelity, stylistically consistent visual assets for a text adventure game engine necessitates a systematic and structured approach to prompt engineering. In a development pipeline where asset quality and coherence across multiple locations are critical, relying on simple, unstructured text descriptions often results in keyword dilution and visually inconsistent outputs, a common pitfall in generative AI models. [1]

The proposed multi-layered methodology is robust and entirely consistent with advanced practices in prompt engineering, which advocates for segmenting instructions into distinct logical components such as Context, Focus, and Constraints. [2, 3, 4] For image generation, this segregation is paramount because the model must rigorously manage scene content against strict artistic constraints. The analysis confirms that segmenting the prompt into logical components—Content (L1), Context (L2), Aesthetic (L3/L4), and Technical Constraints (L5/L6)—is the most effective method for achieving repeatable, high-quality results. [5, 6]

A key system architectural benefit of this approach is the successful decoupling of **narrative elements** (L1 and L2) from **aesthetic control elements** (L3 and L4). Layers 1 and 2 function as dynamic *input variables* derived from the current game state (e.g., location details and descriptive environment), while Layers 3 and 4 serve as *fixed aesthetic templates* or reusable visual style sheets. This modularity allows the game engine to dramatically alter the visual identity of an entire game instance (e.g., swapping a "Victorian" theme for a "Cyberpunk" theme) by changing the L2, L3, and L4 strings, without requiring any alteration to the core generation logic for the L1 scene content. This separation is vital for system scalability, ensuring that specific details of a location, such as the lighting inside a "Library," do not interfere with or unintentionally override the consistent artistic style applied globally to the game world.

### 1.2 Introduction of the Refined Six-Layer Model (MPA)

The user's initial five-layer framework is functionally sound. However, a production-level generative asset pipeline demands an explicit, technical layer for quality control and constraint enforcement. The analysis validates the descriptive layers and integrates mandatory control layers, resulting in the comprehensive **Modular Prompt Architecture (MPA)**, a six-layer system:

1.  **L1: Content (Subject and Scene Focus):** The variable definition of the immediate scene and subjects.
2.  **L2: Context (World Definition and Environment):** Fixed, persistent narrative and material context for the entire world.
3.  **L3: Mood (Affective Tone and Lighting/Color):** The emotional and atmospheric filter, influencing light quality and color tone.
4.  **L4: Style (Artistic Medium and Rendering Technique):** The dominant, highly weighted aesthetic definition.
5.  **L5: Technical (Composition, Camera, and Parameters):** Framing, perspective, and output format specifications.
6.  **L6: Negative Prompting (Quality Assurance and Artifact Removal):** The mandatory layer for negating technical flaws and enforcing L4 stylistic constraints.

## II. The Foundational Layered Prompting Architecture (MPA) in Detail

### 2.1 Layer 1: Content and Subject Definition (The Variable Core)

Layer 1 is the primary instruction defining the main visual elements of the location, such as objects, spatial arrangements, and subjects. For optimal fidelity, the generative prompt should always begin with this content, ensuring the main subject receives priority attention from the model. [6, 7] This layer contains the information that is dynamically changed for every location the player enters.

The user's example, "Library room, walls lined with book shelves, desk in the middle," provides clear nouns and essential visual details that establish the scene's geometry.

### 2.2 Layer 2: World Context and Environment (The Narrative Anchor)

Layer 2 ensures structural and thematic cohesion across the entire game world. [8] This persistent, high-level context guarantees that regardless of the specific location, the material reality of the world remains constant.

Components of L2 include the Time Period (e.g., *Victorian era*), Dominant Materiality (e.g., *old wood, brass components*), Environmental State (e.g., *dusty and crooked but not broken*, *sleek and sterile*), and Persistent Light Source characteristics (e.g., *lit by candles*, *lit by buzzing neon*). The text string for L2 should be *fixed* and reused across every location prompt within a single game world instance. This creates a reusable 'Context Block' that anchors the world's persistent feel, reinforcing the necessary semantic information for the AI to maintain consistency. [5] The prompt segment, "Victorian era, old wood, dusty and crooked but not broken, lit by candles," is an exemplary Context Block.

### 2.3 Layer 3: Visual Mood and Affective Tone (The Emotional Filter)

Layer 3 governs the emotional atmosphere, light quality, and overall color scheme, translating narrative tension into visual atmosphere. [7, 9] It primarily employs evocative adjectives to instruct the generative model on the desired emotional response. [10]

This layer is composed of:

*   **Mood Adjectives:** Terms like *spooky, wistful, convivial, melancholic*. [7, 10, 11]
*   **Lighting Modifiers:** Specific descriptive terms that define shadow and depth, such as *contrasty, dramatic chiaroscuro, volumetric fog*, or *soft golden hour lighting with long shadows*. [5, 7, 12]
*   **Color Palette:** Instructions like *cool tones* (to convey tranquility) or *vibrant, saturated tones* (to convey energy). [7, 9]

Although Layer 4 sets the overall style, Layer 3 provides essential narrative modulation. The game engine can dynamically adjust the affective tone by increasing the prompt weight of L3 keywords when generating a scene tied to a specific emotional beat (e.g., changing "quiet" to `(ominous:1.3)`). [13] This process forces an immediate, localized shift in lighting and color tone, ensuring the image matches the narrative moment without violating the fundamental L4 style definition. [14] The user’s L3 segment, "contrasty, hyper-detailed, inspiring, but slightly spooky," is effective for establishing a complex atmosphere.

### 2.4 Layer 4: Stylistic Rendering and Medium (The Aesthetic Overdrive)

Layer 4 defines the entire artistic execution—the medium, artistic movement, or digital aesthetic (e.g., "Pixel Art," "Baroque Painting," "Cinematic Photorealism"). [15, 16] To ensure non-negotiable visual consistency, this layer must be fixed per game world and intentionally receive the highest prompt weighting. [5, 6]

Key components include:

*   **Medium:** (e.g., illustration, photo, oil on canvas, watercolor [7, 9]).
*   **Artistic Movement:** (e.g., Psychedelic, Art Deco, Impressionist [11, 15]).
*   **Digital Aesthetic:** (e.g., Digital painting, concept art, 16bit retro aesthetic, cinematic [16, 17, 18]).

To establish **style dominance**, L4 keywords must be explicitly weighted higher than the descriptive L1 or L2 content. [13, 14] This technical enforcement mechanism is necessary to prevent the AI from generating photorealistic images when faced with unweighted descriptive subject matter, ensuring the "Library room" consistently adheres to the selected artistic style, such as "Digital painting."

### 2.5 Layer 5: Technical Parameters and Composition (The System Constraints)

Layer 5 dictates the technical constraints and narrative framing, effectively controlling the image composition and presentation. [18, 19]

Core components are:

*   **Format and Quality:** Aspect Ratio (16:9 [16]) and quality tags (8K resolution, high-quality).
*   **Camera Mechanics:** Specifies the shot composition (e.g., *cinematic wide shot, Establishing Shot, Close-Up* [19, 20]), camera angles (e.g., *Low Angle Shot, Birds-Eye-View* [19, 20]), and lens specifications (e.g., *24mm wide-angle lens* for breadth or *85mm telephoto lens* for portrait focus). [21]

This layer serves as a powerful instrument for visual storytelling. The engine can map compositional terms to narrative intention: utilizing a "Wide-Angle Establishing Shot" (24mm lens) for scene introductions (L2 context) and employing a "Close-Up" (85mm lens) with "Shallow Depth of Field" to draw attention to interactive or key L1 content elements. [20, 21] Maintaining this consistent visual grammar enhances the immersive experience by guiding the player's focus.

### 2.6 Layer 6: Negative Prompting (The Artifact Filter)

Layer 6 is a critical, mandatory component for production-ready asset generation. It provides explicit instructions to the AI regarding what features or artifacts *must* be excluded, ensuring quality assurance and preventing stylistic conflict. [22, 23]

This layer comprises standard boilerplate terms (to mitigate common technical flaws like blurring and artifacts) and dynamically injected anti-style terms (to actively deny aesthetics that conflict with L4). For example, if L4 mandates "Pixel Art," L6 must contain terms like *photorealistic, 3D, CGI*. [24, 25] This active denial, alongside Layer 4 weighting, is a dual-factor technical strategy for absolute style enforcement.

## III. Achieving Inter-Location Consistency and Scalability

Generating consistent assets across a diverse game world requires technical enforcement beyond simple keyword inclusion.

### 3.1 Prompt Weighting Mechanisms for Style Dominance

To counteract keyword dilution, Layer 4 (Style) must be explicitly emphasized using model-specific syntax. [13, 14] Token weighting, such as `(keyword:1.X)` or `keyword+++`, directs the model to prioritize certain concepts. [6, 13]

The recommended weighting range is 1.1 (moderate emphasis) to 1.8 (aggressive enforcement). While aggressive weighting carries a risk of image distortion, it is often necessary for non-photorealistic or highly stylized aesthetics like retro Pixel Art. [13]

The standard prompt string is formulated by concatenating weighted layers: **L1, L2, (L3:1.1), ((L4):1.4), L5**.

The tuning of these weights is essential during the initial world-building phase. If the model prioritizes a complex L1 subject (e.g., "intricate clockwork mechanism") over the L4 style (e.g., "Impressionist painting"), the L4 weight must be increased until the style dominates the subject's complexity. This finely tuned weighting parameter must be stored and reused as part of the fixed L4 configuration for the game world.

**Table 1: MPA Layer Weighting Priority Matrix**

| Layer | Function | Priority | Recommended Weight (Range) | Justification |
| :--- | :--- | :--- | :--- | :--- |
| **L4: Style** | Aesthetic Dominance | Highest | 1.3 - 1.6 | Guarantees global consistency across all assets; overrides content details. [14] |
| **L3: Mood** | Affective Tone | High | 1.1 - 1.3 | Controls lighting and emotion; crucial for dynamic narrative shifts. [5] |
| **L1: Content** | Scene Subject | Medium | Default (1.0) | Defines the scene; weighting should be neutral to allow L4/L3 dominance. |
| **L2: Context** | World Definition | Medium | Default (1.0) | Provides foundational texture; consistency relies on fixed string reuse. |
| **L5: Technical** | Composition | Medium | 1.0 - 1.2 | Controls framing and quality; weighting can enforce specific camera moves (e.g., `(Close-Up:1.2)`). [19] |

### 3.2 Fixed Style Blocks and Seed Management

Visual continuity is dependent on the consistent application of input variables. The combined strings of L2, L3, and L4 should be maintained as immutable 'Style Blocks' for every prompt within that specific game world instance. [5, 26]

The strategic use of **Seed Management** allows for controlled variation. A seed value acts as the starting point for the generation process. [14] By identifying and reusing a successful seed that yields a favorable composition and structure, the engine can generate multiple variations of the L1 content while preserving the overall aesthetic established by L2, L3, and L4. This is essential for generating multiple angles of the same room without introducing visual inconsistencies.

Furthermore, the system must architecturally prevent the selection of contradictory L4 terms (e.g., combining "photorealism" with "cartoon"). [14] Contradictory constraints lead to significant dilution of the model's focus and unpredictable output.

## IV. Prompt Taxonomy and Keyword Catalogs

### 4.1 Layer 3 Keyword Index: Affect and Mood Modifiers

These terms provide precise control over the emotional and visual filter of the scene:

*   **Lighting Modifiers:** Effective lighting keywords define shadow, volume, and atmosphere. Examples include: *dramatic chiaroscuro, volumetric light, rim lighting, god rays, soft ambient light*, and specific time references like *golden hour* or *overcast*. [5, 7, 12]
*   **Color Palette Terms:** These control the image's emotional temperature and intensity. Terms include: *saturated, vibrant, muted, pastel, monochromatic*. [7, 9] Specifying *cool tones* or *warm tones* is an efficient method for influencing the overall feeling of tranquility or energy. [9]

### 4.2 Layer 4 Style Reference Library (Aesthetic Taxonomy)

This taxonomy provides the vocabulary necessary to define the artistic engine and ensure consistency.

**Table 2: Style Reference and Negative Constraint Catalog**

| Target Style | L4 Keywords (Core) | L4 Keywords (Qualifiers) | Mandatory L6 Anti-Style Negative Prompts |
| :--- | :--- | :--- | :--- |
| **Cinematic Photorealism** | cinematic still, photorealistic | 8K, ultra-detailed, 35mm lens, octane render | cartoon, illustration, drawing, pixel art, sketch, painterly, anime |
| **Digital Painting** | digital painting, concept art | artistic, highly detailed, trending on ArtStation | photorealistic, 3D, CGI, unreal engine, worst quality, blurry |
| **Retro Pixel Art** | low-resolution pixel art, 8bit | 16bit, top-down view, dithering, sprite art | 3D, CGI, realistic, high resolution, smooth shading, watercolor, hyperrealism [24] |
| **Fine Art (e.g., Oil)** | masterpiece, oil on canvas | detailed baroque painting, heavy brushstrokes, chiaroscuro | simplistic, digital art, cartoon, modern, drawing, sketch |

### 4.3 Layer 5 Compositional Toolkit (Cinematic Control)

Layer 5 allows for the sophisticated framing of game assets, simulating a professional camera operator. [19]

*   **Camera Shot Size:** Defines the scope: *Extreme Wide Shot* (landscapes), *Establishing Shot* (rooms), *Medium Shot, Close-Up* (key objects). [20]
*   **Camera Angle:** Controls narrative perspective: *Eye Level Shot* (neutral), *Low Angle Shot* (imposing), *High Angle Shot* (vulnerability), *Birds-Eye-View* (map/overview). [19, 20]
*   **Lens and Focus:** Direct control over depth and field: use *24mm wide-angle lens* for capturing the breadth of a scene and *85mm telephoto lens* for portraiture or emphasizing objects. [21] Focus techniques such as *Shallow Depth of Field* or *Deep Focus* guide the visual hierarchy. [19, 20]

## V. Advanced Quality Control: The Negative Prompting Strategy (Layer 6)

The Negative Prompt (L6) serves as the primary mechanism for quality control, instructing the model to avoid generating specific technical flaws and stylistic elements. [23, 27]

### 5.1 Standard Quality and Artifact Removal (Boilerplate)

Every prompt must incorporate a boilerplate list of technical flaws to ensure crisp, clean, professional assets. [22, 23]

**Table 3: Boilerplate Negative Prompt List (Quality Assurance)**

| Flaw Category | Targeted Keywords (Minimum Inclusion) | Reasoning |
| :--- | :--- | :--- |
| **Technical Quality** | worst quality, low quality, lowres, blurry, jpeg artifacts, compression artifacts, noisy, grainy, out of focus | Removes common technical output imperfections. [22, 23] |
| **Unwanted Annotations** | watermark, signature, text, logo, cropped, simple background, abstract background, collage, boring background | Ensures clean, professional assets ready for production use. [22, 28] |
| **Structural/Anatomy** | bad anatomy, poorly drawn hands, poorly drawn face, deformed, disfigured, extra limbs, mutated, gross proportions | Prevents model errors, even in rendering of architecture and detailed objects. [25, 28] |
| **Style Interference** | amateur, beginner, poorly drawn, generic, bad art | General terms to enforce competence and artistic skill. [23] |

### 5.2 Anatomical and Structural Flaw Mitigation

Specific terms are required to prevent structural inconsistencies, even in inanimate architectural elements: *bad proportions, deformed structures, malformed limbs, asymmetrical, inverted*. [25, 28] This ensures the background architecture and objects maintain high fidelity.

### 5.3 Style-Specific Negative Prompting (The Anti-Style List)

The critical function of L6 is to enforce L4 style choices by actively denying conflicting aesthetics. For example, if the L4 specification is "Digital Painting," the L6 list must include: *photorealistic, realistic, 3D, CGI, uncanny, hyperrealism*. [24, 25] Conversely, if L4 is "Cinematic Photorealism," L6 must contain terms that forbid artistic interpretation, such as *cartoon, sketch, illustration, pixelated, amateur*. [25] This deliberate denial is necessary for maintaining the game world's defined visual language.

## VI. Case Studies and Implementation Formulas

The following examples demonstrate the full application of the MPA structure, including mandatory weighting and the complete L6 negative prompt string, suitable for direct testing with a model like Nano Banana Pro.

### 6.1 Case Study 1: The Victorian Library (Digital Painting Style)

**Goal:** High detail, spooky mood, enforced digital painting aesthetic.

*   **L1 (Content):** Library room, walls lined with book shelves, heavy oak desk in the middle, open book with a faint glow
*   **L2 (Context):** Victorian era, old wood, dusty and crooked but not broken, lit by candles, dim
*   **L3 (Mood):** (High contrast, dramatic chiaroscuro:1.2), spooky, hyper-detailed, melancholic atmosphere
*   **L4 (Style):** ((Digital painting):1.4), detailed concept art, artistic, rich textures
*   **L5 (Technical):** Medium wide shot, soft focus on the open book, 8K resolution, 16:9 aspect ratio
*   **L6 (Negative Prompt String):** worst quality, low quality, lowres, blurry, jpeg artifacts, distortion, watermark, signature, text, 3D, CGI, photorealistic, hyperrealism, unreal engine, amateur, poorly drawn hands

### 6.2 Case Study 2: Cyberpunk Alley (Neon Noir Cinematic Style)

**Goal:** Gritty, ultra-realistic look with strong light/shadow play, demanding maximum anti-style negative enforcement.

*   **L1 (Content):** Narrow, wet alleyway, neon signs flickering in the rain, discarded data chips on the ground
*   **L2 (Context):** Futuristic street, rainy night, steam rising from grates, high-tech urban sprawl
*   **L3 (Mood):** (Neon glow, ultra-vibrant:1.3), gritty, cinematic atmosphere, deep shadows
*   **L4 (Style):** ((Cinematic photorealism):1.4), film still, 35mm film grain effect, V-Ray render
*   **L5 (Technical):** Low angle shot, taken with a 35mm lens, (detailed reflections:1.4), shallow depth of field, 21:9 aspect ratio
*   **L6 (Negative Prompt String):** worst quality, lowres, blurry, distortion, watermark, text, cartoon, illustration, drawing, painting, sketch, pixelated, anime, watercolor, amateur, low contrast, ugly

### 6.3 Case Study 3: Fantasy Dungeon (Top-Down Pixel Art)

**Goal:** Highly stylized, low-fidelity 16bit retro aesthetic, requiring maximum L4 weighting and specific compositional framing (Birds-Eye-View).

*   **L1 (Content):** Dungeon corridor, mossy stone walls, lit by a single torch, chest in the corner
*   **L2 (Context):** Medieval fantasy setting, damp atmosphere, carved runes on the walls
*   **L3 (Mood):** Dark ambient lighting, muted earth tones, mysterious, low saturation
*   **L4 (Style):** ((Low-resolution pixel art):1.6), 16bit retro RPG aesthetic, dithering, 2D sprite art
*   **L5 (Technical):** (Birds-Eye-View:1.3), top down perspective, 1:1 aspect ratio, (small scale:1.3)
*   **L6 (Negative Prompt String):** worst quality, blurry, 3D, CGI, realistic, high resolution, smooth shading, watercolor, hyperrealism, oil painting, photo, sketch, detailed textures, smooth gradients, large scale, bad proportions

---

## References

1.  Scenario - AI-Powered Content Generation Platform, [https://www.scenario.com/](https://www.scenario.com/)
2.  Beyond Best Practices: The Layered Prompt Structure That Adapts as It Works : r/PromptEngineering - Reddit, [https://www.reddit.com/r/PromptEngineering/comments/1mlnm73/beyond_best_practices_the_layered_prompt/](https://www.reddit.com/r/PromptEngineering/comments/1mlnm73/beyond_best_practices_the_layered_prompt/)
3.  How to Write Better Prompts: A Simple 3-Part Formula - DEV Community, [https://dev.to/rijultp/how-to-write-better-prompts-a-simple-3-part-formula-37cn](https://dev.to/rijultp/how-to-write-better-prompts-a-simple-3-part-formula-37cn)
4.  The 3-layer structure I use instead of “one big prompt” : r/PromptEngineering - Reddit, [https://www.reddit.com/r/PromptEngineering/comments/1oo6fb8/the_3layer_structure_i_use_instead_of_one_big/](https://www.reddit.com/r/PromptEngineering/comments/1oo6fb8/the_3layer_structure_i_use_instead_of_one_big/)
5.  How to write prompts for AI art (with examples) - Printful, [https://www.printful.com/blog/prompts-for-ai-art](https://www.printful.com/blog/prompts-for-ai-art)
6.  How to write AI image prompts like a pro [Oct 2025] - LetsEnhance, [https://letsenhance.io/blog/article/ai-text-prompt-guide/](https://letsenhance.io/blog/article/ai-text-prompt-guide/)
7.  Prompt Basics - Midjourney, [https://docs.midjourney.com/hc/en-us/articles/32023408776205-Prompt-Basics](https://docs.midjourney.com/hc/en-us/articles/32023408776205-Prompt-Basics)
8.  AI Illustration Prompting Mastery: 100+ Proven Formulas for Perfect Results 2025 - Lovart, [https://www.lovart.ai/blog/ai-illustration-prompts](https://www.lovart.ai/blog/ai-illustration-prompts)
9.  70+ AI art styles to use in your AI prompts - Zapier, [https://zapier.com/blog/ai-art-styles/](https://zapier.com/blog/ai-art-styles/)
10. Profound list of 1000 adjectives for AI Art, Mad-libs and more! - Student, Writers and Art, [https://studentandwriter.com/2023/04/01/list-of-1000-adjectives-no-repeats/](https://studentandwriter.com/2023/04/01/list-of-1000-adjectives-no-repeats/)
11. AI Image Generation Prompt Engineering — Are you applying proper prompt techniques when generating AI images? | by David Ocearn | Medium, [https://medium.com/@david-ocean/ai-image-generation-prompt-engineering-are-you-applying-proper-prompt-techniques-when-generating-0753d0ee3666](https://medium.com/@david-ocean/ai-image-generation-prompt-engineering-are-you-applying-proper-prompt-techniques-when-generating-0753d0ee3666)
12. Prompt Engineering - CinemaFlow AI, [https://www.cinemaflow.ai/prompt-engineering](https://www.cinemaflow.ai/prompt-engineering)
13. Guide to Stable Diffusion Prompt Weights - getimg.ai, [https://getimg.ai/guides/guide-to-stable-diffusion-prompt-weights](https://getimg.ai/guides/guide-to-stable-diffusion-prompt-weights)
14. Prompt Engineering for Stable Diffusion - Portkey, [https://portkey.ai/blog/prompt-engineering-for-stable-diffusion/](https://portkey.ai/blog/prompt-engineering-for-stable-diffusion/)
15. 7 art styles for AI prompts - Adobe Firefly, [https://www.adobe.com/products/firefly/discover/art-style-prompts-for-ai.html](https://www.adobe.com/products/firefly/discover/art-style-prompts-for-ai.html)
16. Text to image - Clipdrop, [https://clipdrop.co/text-to-image](https://clipdrop.co/text-to-image)
17. Pixel Art Adventure Landscape: A Stunning Game Level Selection | AI Art Generator, [https://easy-peasy.ai/ai-image-generator/images/pixel-art-adventure-landscape-game-level-selection](https://easy-peasy.ai/ai-image-generator/images/pixel-art-adventure-landscape-game-level-selection)
18. Ultimate Guide to Cinematic & Photorealistic Ai Image Prompts (for Midjourney) - YouTube, [https://www.youtube.com/watch?v=HWOLsh-7ZHQ](https://www.youtube.com/watch?v=HWOLsh-7ZHQ)
19. Ultimate prompting guide for Veo 3.1 | Google Cloud Blog, [https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1)
20. Prompt Style: Camera Shots and Angles - ARTSMART AI, [https://artsmart.ai/docs/camera-shots-and-angles/](https://artsmart.ai/docs/camera-shots-and-angles/)
21. The Impact of Prompting Different Camera Lenses In AI Product Image Generation, [https://www.ecomtent.ai/blog-page/the-impact-of-prompting-different-camera-lenses-in-ai-image-generation](https://www.ecomtent.ai/blog-page/the-impact-of-prompting-different-camera-lenses-in-ai-image-generation)
22. 200+ Best Stable Diffusion Negative Prompts with Examples - Aiarty Image Enhancer, [https://www.aiarty.com/stable-diffusion-prompts/stable-diffusion-negative-prompt.htm](https://www.aiarty.com/stable-diffusion-prompts/stable-diffusion-negative-prompt.htm)
23. How to use negative prompts? - Stable Diffusion Art, [https://stable-diffusion-art.com/how-to-use-negative-prompts/](https://stable-diffusion-art.com/how-to-use-negative-prompts/)
24. 120+ Stable Diffusion Negative Prompts to Improve AI Art in 2025 - ClickUp, [https://clickup.com/blog/stable-diffusion-negative-prompts/](https://clickup.com/blog/stable-diffusion-negative-prompts/)
25. Best Negative Prompts for Stable Diffusion - Segmind Blog, [https://blog.segmind.com/best-negative-prompts-in-stable-diffusion/](https://blog.segmind.com/best-negative-prompts-in-stable-diffusion/)
26. How to Design Consistent AI Characters with Prompts, Diffusion & Reference Control (2025), [https://medium.com/design-bootcamp/how-to-design-consistent-ai-characters-with-prompts-diffusion-reference-control-2025-a1bf1757655d](https://medium.com/design-bootcamp/how-to-design-consistent-ai-characters-with-prompts-diffusion-reference-control-2025-a1bf1757655d)
27. Guide to Negative Prompts in Stable Diffusion - getimg.ai, [https://getimg.ai/guides/guide-to-negative-prompts-in-stable-diffusion](https://getimg.ai/guides/guide-to-negative-prompts-in-stable-diffusion)
28. Negative Prompts for Perfect AI Image Generation | Medium, [https://medium.com/@johnnythedeveloper/negative-prompts-for-perfect-ai-image-generation-4b45744363c7](https://medium.com/@johnnythedeveloper/negative-prompts-for-perfect-ai-image-generation-4b45744363c7)
