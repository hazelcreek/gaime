# GAIME Audio Concept Document

This document outlines a comprehensive approach to adding music and sound effects to GAIME, starting with simple implementations and building toward a rich, dynamic audio experience.

## Table of Contents

1. [Overview & Goals](#overview--goals)
2. [Music System](#music-system)
   - [World-Based Background Music](#world-based-background-music)
   - [Dynamic Music Layers (Stems)](#dynamic-music-layers-stems)
   - [Production Methods](#production-methods)
3. [Sound Effects System](#sound-effects-system)
   - [Ambient Soundscapes](#ambient-soundscapes)
   - [Random Occurrence Sounds](#random-occurrence-sounds)
   - [Action-Triggered Sounds](#action-triggered-sounds)
4. [Technical Architecture](#technical-architecture)
   - [Frontend Audio Engine](#frontend-audio-engine)
   - [Backend Audio Metadata](#backend-audio-metadata)
   - [YAML Schema Extensions](#yaml-schema-extensions)
5. [Asset Creation & Sourcing](#asset-creation--sourcing)
   - [AI-Generated Audio](#ai-generated-audio)
   - [DAW Production](#daw-production)
   - [Royalty-Free Sources](#royalty-free-sources)
6. [Implementation Roadmap](#implementation-roadmap)
7. [File Organization](#file-organization)
8. [Text-to-SFX Prompt Generation](#text-to-sfx-prompt-generation)
   - [Prompt Anatomy](#prompt-anatomy)
   - [Deriving Prompts from World YAML](#deriving-prompts-from-world-yaml)
   - [Automated Prompt Generation System](#automated-prompt-generation-system)
   - [Prompt Quality Guidelines](#prompt-quality-guidelines)
9. [Music Creative Brief Generation](#music-creative-brief-generation)
   - [Creative Brief Structure](#creative-brief-structure)
   - [Automatic Brief Generation from World YAML](#automatic-brief-generation-from-world-yaml)
   - [Example Generated Brief](#example-generated-brief-cursed-manor)
10. [Seamless Looping: Deep Dive](#seamless-looping-deep-dive)
    - [What Makes a Loop Seamless](#what-makes-a-loop-seamless)
    - [Method 1: Crossfade Looping](#method-1-crossfade-looping-easiest)
    - [Method 2: Musical Composition for Looping](#method-2-musical-composition-for-looping-best-quality)
    - [Method 3: Zero-Crossing Editing](#method-3-zero-crossing-editing-for-sound-effects)
    - [Export Settings for Looping Audio](#export-settings-for-looping-audio)

---

## Overview & Goals

### Why Audio Matters

GAIME is a text adventure that relies heavily on atmosphere and immersion. While our AI-generated narratives and scene images create a strong visual foundation, **audio is the missing sensory dimension** that can transform a reading experience into a visceral, emotional journey.

### Design Principles

1. **Enhance, Don't Distract**: Audio should support the narrative, not compete with it
2. **Layered Complexity**: Start simple (single loop) and add layers over time
3. **Dynamic Responsiveness**: Audio should react to game state, location, and actions
4. **Performance First**: Audio must not impact game responsiveness
5. **Graceful Degradation**: Game works perfectly without audio; audio is enhancement

### Core Features

| Feature | Description | Priority |
|---------|-------------|----------|
| Main Menu Music | Atmospheric loop on title/world selection screen | Phase 1 |
| World Background Music | Unique music per world theme | Phase 1 |
| Location Ambience | Continuous environmental sounds per location | Phase 2 |
| Random Sounds | Occasional atmospheric events (thunder, creaks) | Phase 2 |
| Action Sounds | Feedback for player interactions | Phase 3 |
| Dynamic Stems | Music that evolves with game state | Phase 4 |

---

## Music System

### World-Based Background Music

Each world should have its own musical identity that reinforces its theme.

#### Example Themes

| World | Musical Style | Instruments | Mood |
|-------|---------------|-------------|------|
| `cursed-manor` | Victorian gothic | Piano, strings, choir | Eerie, melancholic |
| `detention_survival_high` | 80s synth horror | Synths, drum machines | Tense, nostalgic |
| `echoes_of_subjugation` | Industrial/prison | Metallic percussion, drones | Oppressive, cold |

#### Music Loop Requirements

- **Format**: MP3 (browser compatibility) + OGG (Firefox/quality)
- **Duration**: 2-5 minutes for seamless looping
- **Loop Point**: Clean fade or composition designed for seamless repetition
- **File Size**: Target < 3MB per track for reasonable loading
- **Bitrate**: 128-192 kbps (balance of quality and size)

### Dynamic Music Layers (Stems)

For richer immersion, music can be delivered as separate **stems** (layers) that mix dynamically based on game state.

#### Stem Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Dynamic Music Mixer                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│   │   BASE   │  │  TENSION │  │  MELODY  │  │  ACCENT  │   │
│   │  (Drone) │  │ (Strings)│  │  (Piano) │  │ (Choir)  │   │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│        │             │             │             │          │
│   Vol: 100%     Vol: 0-100%   Vol: 0-100%   Vol: 0-100%    │
│   Always on    Based on       Based on       Triggered     │
│                danger level   location       by events     │
└─────────────────────────────────────────────────────────────┘
```

#### Stem Definitions

| Stem | Purpose | When Active |
|------|---------|-------------|
| **Base/Drone** | Foundation layer | Always playing at full volume |
| **Tension** | Builds suspense | Increases based on danger or proximity to threats |
| **Melody** | Emotional hook | Varies by location (library = contemplative, ritual chamber = ominous) |
| **Accent** | Dramatic moments | Triggered by discoveries, NPC encounters, key events |

#### Stem File Naming

```
worlds/cursed-manor/audio/
├── music/
│   ├── cursed-manor-base.mp3      # Always playing
│   ├── cursed-manor-tension.mp3   # Danger layer
│   ├── cursed-manor-melody.mp3    # Location-specific
│   └── cursed-manor-accent.mp3    # Event triggers
```

#### Technical Requirements for Stems

- **Synchronized Length**: All stems MUST be exactly the same duration
- **Same BPM/Time Signature**: Essential for alignment
- **Common Loop Point**: All stems loop at the same timestamp
- **Phase Alignment**: Stems should be recorded/exported starting from the same beat

### Production Methods

#### Option 1: AI Music Generation

Modern AI tools can generate atmospheric music quickly:

| Tool | Strengths | Best For |
|------|-----------|----------|
| **Suno AI** | High quality, various styles | Full tracks, quick iteration |
| **Udio** | Excellent at specific genres | Genre-specific pieces |
| **Stable Audio** | Open model, customizable | Ambient/drone layers |
| **AIVA** | Classical/orchestral focus | Victorian/dramatic themes |
| **Mubert** | Real-time generation | Ambient backgrounds |

**AI Generation Workflow**:
1. Write detailed prompts describing mood, instruments, tempo
2. Generate multiple variations (5-10 per world)
3. Select best candidates
4. Edit in DAW for seamless looping
5. Export stems if possible (or recreate with similar parameters)

**Example Prompt for Cursed Manor**:
> "Dark Victorian piano piece, melancholic and eerie, minor key, slow tempo around 60 BPM, with subtle string drones and occasional distant choir. Suitable for a haunted mansion. Seamless loop, 3 minutes."

#### Option 2: DAW Production

For full control, produce music in a Digital Audio Workstation:

**Recommended DAWs**:
- **Reaper**: Affordable, powerful, excellent for game audio
- **Ableton Live**: Great for loops and layering
- **Logic Pro**: Mac only, excellent for orchestral
- **FL Studio**: Great for electronic/synth sounds

**Production Workflow**:
1. Establish BPM and time signature (e.g., 80 BPM, 4/4)
2. Create base drone/pad layer (2-4 bars looped)
3. Add tension elements (sparse, can be muted)
4. Compose melody variations
5. Design accent stings
6. Export each layer as separate stem
7. Test synchronization and loop points

**Technical Settings**:
- Sample Rate: 44.1kHz (standard for web)
- Export: WAV for editing, MP3/OGG for deployment
- Normalization: -6dB to -3dB peaks (leave headroom for mixing)

#### Option 3: Hybrid Approach (Recommended)

Combine AI generation with DAW refinement:

1. **AI generates base tracks** (quick, varied ideas)
2. **Import to DAW** for editing
3. **Adjust loop points** for seamless playback
4. **Layer AI tracks** to create stem-like structure
5. **Add custom elements** (specific sound effects, transitions)

---

## Sound Effects System

### Ambient Soundscapes

Each location should have a continuous ambient soundscape that runs beneath the music.

#### Location Ambience Examples

| Location | Primary Sounds | Secondary Sounds |
|----------|----------------|------------------|
| `entrance_hall` | Wind against windows | Clock ticking, distant thunder |
| `library` | Fire crackling | Pages rustling, wood settling |
| `basement` | Water dripping | Rats scurrying, chains clanking |
| `kitchen` | Embers in hearth | Cutlery rattling, floorboards |
| `ritual_chamber` | Low hum/drone | Ethereal whispers, candle flicker |
| `outside_garden` | Wind, rain | Crows, rustling leaves |

#### Ambient Loop Requirements

- **Seamless Looping**: Critical - no audible pop or gap
- **Duration**: 30-60 seconds minimum
- **Stereo**: Wider soundscape, panning elements
- **Format**: MP3 (128kbps sufficient for ambience)
- **File Size**: < 1MB per location

#### Layered Ambience

For rich environments, layer multiple ambient tracks:

```
Location: Library
├── library-base.mp3      # Fire crackling (always on)
├── library-weather.mp3   # Rain on windows (based on weather)
└── library-supernatural.mp3  # Whispers (when ghost nearby)
```

### Random Occurrence Sounds

Occasional sounds that play at random intervals to prevent monotony and add surprises.

#### Sound Types

| Type | Examples | Frequency |
|------|----------|-----------|
| **Weather** | Thunder crack, wind gust | Every 30-120 seconds |
| **Structural** | Wood creaking, settling | Every 20-60 seconds |
| **Supernatural** | Distant whisper, chill wind | Every 60-180 seconds |
| **Wildlife** | Owl hoot, rats | Every 45-90 seconds |

#### Configuration Schema

```yaml
random_sounds:
  thunder:
    file: "effects/thunder.mp3"
    min_interval: 30000   # ms
    max_interval: 120000  # ms
    volume: 0.6
    locations:            # Where this can play
      - entrance_hall
      - upper_landing
      - any_exterior
  
  wood_creak:
    file: "effects/wood-creak.mp3"
    min_interval: 20000
    max_interval: 60000
    volume: 0.4
    locations: all        # Plays anywhere
```

### Action-Triggered Sounds

Sounds that play in response to specific player actions or game events.

#### Interaction Sound Categories

| Category | Examples |
|----------|----------|
| **Movement** | Footsteps (varies by surface), door open/close |
| **Inventory** | Item pickup, item use, keys jangling |
| **Environment** | Piano playing, lever pulling, lock clicking |
| **Discovery** | Secret found, artifact revealed |
| **NPC** | Ghost appearance, character greeting |
| **Feedback** | Invalid action, game hint |

#### Sound Mapping in YAML

```yaml
# In locations.yaml - interaction sounds
interactions:
  play_piano:
    triggers: ["play piano", "use piano"]
    narrative_hint: "Haunting melody plays itself"
    sets_flag: played_piano
    sound: "effects/piano-melody.mp3"  # NEW: Sound effect

# In items.yaml - item sounds
iron_key:
  name: "Heavy Iron Key"
  take_sound: "effects/key-pickup.mp3"      # NEW
  use_sound: "effects/lock-unlock.mp3"      # NEW
```

#### Global Sound Events

Sounds triggered by game state changes:

```yaml
# In world.yaml or separate audio.yaml
global_sounds:
  game_start: "effects/thunder-dramatic.mp3"
  discovery: "effects/discovery-chime.mp3"
  ghost_appear: "effects/ghost-whoosh.mp3"
  victory: "effects/victory-crescendo.mp3"
  danger_near: "effects/heartbeat.mp3"
```

---

## Technical Architecture

### Frontend Audio Engine

The audio system lives entirely in the frontend, with the backend providing metadata about what audio to play.

#### React Audio Manager

```typescript
// src/audio/AudioManager.ts (proposed)

interface AudioConfig {
  masterVolume: number;
  musicVolume: number;
  ambienceVolume: number;
  effectsVolume: number;
  enabled: boolean;
}

interface AudioState {
  currentMusic: string | null;
  currentAmbience: string[];
  activeStemLayers: Record<string, number>; // stem name -> volume
}

class AudioManager {
  private config: AudioConfig;
  private state: AudioState;
  
  // Howler.js instances for each audio type
  private musicPlayer: Howl | null;
  private ambiencePool: Map<string, Howl>;
  private effectsPool: Map<string, Howl>;
  
  // Core methods
  playMusic(worldId: string): void;
  setMusicStem(stem: string, volume: number): void;
  playAmbience(locationId: string): void;
  playEffect(effectId: string): void;
  playRandomSound(config: RandomSoundConfig): void;
  
  // Transitions
  crossfadeMusic(from: string, to: string, duration: number): void;
  fadeOutAll(duration: number): void;
  
  // State management
  onLocationChange(locationId: string): void;
  onGameStateChange(state: GameState): void;
}
```

#### Recommended Library: Howler.js

[Howler.js](https://howlerjs.com/) is the ideal choice for web game audio:

- **Cross-browser**: Handles Web Audio API + HTML5 Audio fallback
- **Sprites**: Single file with multiple sounds (reduces HTTP requests)
- **Spatial Audio**: 3D positioning (for advanced effects)
- **Volume Control**: Per-sound and master volume
- **Fading**: Built-in crossfade support
- **Format Detection**: Automatically picks best format

```bash
npm install howler
npm install --save-dev @types/howler
```

#### Audio Hook for React

```typescript
// src/hooks/useAudio.tsx (proposed)

interface UseAudioReturn {
  // Playback controls
  playMusic: (worldId: string) => void;
  playAmbience: (locationId: string) => void;
  playEffect: (effectId: string) => void;
  
  // Volume controls
  setMasterVolume: (volume: number) => void;
  setMusicVolume: (volume: number) => void;
  toggleMute: () => void;
  
  // State
  isLoading: boolean;
  isMuted: boolean;
  currentTrack: string | null;
}

export function useAudio(): UseAudioReturn {
  // Implementation using AudioManager singleton
  // Responds to game state changes
  // Persists volume preferences to localStorage
}
```

#### Integration with Game State

```typescript
// In useGame.tsx - trigger audio on state changes

useEffect(() => {
  if (gameState?.current_location !== previousLocation) {
    audioManager.onLocationChange(gameState.current_location);
  }
}, [gameState?.current_location]);

useEffect(() => {
  if (response.narrative.includes('ghost')) {
    audioManager.playEffect('ghost_appear');
  }
}, [response]);
```

### Backend Audio Metadata

The backend provides audio configuration, but doesn't serve audio files directly.

#### API Response Extensions

```typescript
// Extended ActionResponse
interface ActionResponse {
  narrative: string;
  state: GameState;
  // ... existing fields ...
  
  // NEW: Audio hints
  audio_hints?: {
    play_effect?: string;       // Effect to play (e.g., "door_open")
    ambience_change?: string;   // New location ambience
    music_mood?: string;        // "tense", "calm", "danger"
    stem_volumes?: Record<string, number>; // Dynamic stem mixing
  };
}
```

#### Audio Metadata Endpoint

```
GET /api/game/audio-config/{world_id}
```

Returns audio configuration for a world:

```json
{
  "world_id": "cursed-manor",
  "music": {
    "main": "cursed-manor/music/main-theme.mp3",
    "stems": {
      "base": "cursed-manor/music/base.mp3",
      "tension": "cursed-manor/music/tension.mp3",
      "melody": "cursed-manor/music/melody.mp3"
    }
  },
  "locations": {
    "entrance_hall": {
      "ambience": ["entrance-ambience.mp3"],
      "random_sounds": [
        {"file": "thunder.mp3", "min_interval": 30, "max_interval": 120}
      ]
    },
    "library": {
      "ambience": ["fire-crackling.mp3", "rain-window.mp3"],
      "random_sounds": [
        {"file": "book-fall.mp3", "min_interval": 60, "max_interval": 180}
      ]
    }
  },
  "effects": {
    "door_open": "effects/door-creak.mp3",
    "item_pickup": "effects/pickup.mp3",
    "discovery": "effects/chime.mp3"
  }
}
```

### YAML Schema Extensions

#### world.yaml - Music Configuration

```yaml
name: "The Cursed Manor"
theme: "Victorian gothic horror"

# NEW: Audio configuration
audio:
  music:
    main: "music/cursed-manor-theme.mp3"
    # Optional: stem-based music
    stems:
      base: "music/stems/base-drone.mp3"
      tension: "music/stems/tension-strings.mp3"
      melody: "music/stems/melody-piano.mp3"
      accent: "music/stems/accent-choir.mp3"
  
  # Global sound effects
  effects:
    game_start: "effects/thunder-crash.mp3"
    discovery: "effects/discovery.mp3"
    victory: "effects/victory.mp3"
  
  # Default random sounds (can be overridden per-location)
  random_sounds:
    - id: thunder
      file: "effects/thunder.mp3"
      interval: [30, 120]  # seconds
      volume: 0.6
    - id: creak
      file: "effects/wood-creak.mp3"
      interval: [15, 45]
      volume: 0.4
```

#### locations.yaml - Location Audio

```yaml
entrance_hall:
  name: "Entrance Hall"
  atmosphere: |
    Grand but decayed entrance hall...
  
  # NEW: Location audio
  audio:
    ambience:
      - file: "ambience/wind-howl.mp3"
        volume: 0.5
      - file: "ambience/clock-tick.mp3"
        volume: 0.3
    
    # Override world random sounds
    random_sounds:
      - thunder      # Use world-defined thunder
      - id: door_rattle
        file: "effects/door-rattle.mp3"
        interval: [20, 60]
    
    # Music mood for dynamic mixing
    music_mood: "uneasy"    # affects stem volumes
  
  interactions:
    examine_portraits:
      triggers: ["examine portraits"]
      narrative_hint: "One portrait has been slashed"
      sets_flag: examined_portraits
      sound: "effects/dramatic-sting.mp3"  # NEW
```

#### items.yaml - Item Sounds

```yaml
iron_key:
  name: "Heavy Iron Key"
  portable: true
  examine: "An old iron key..."
  found_description: "A heavy key glints in the shadows"
  
  # NEW: Item sounds
  audio:
    take: "effects/key-jingle.mp3"
    examine: "effects/metal-clink.mp3"
    use: "effects/lock-mechanism.mp3"

piano:
  name: "Grand Piano"
  portable: false
  
  audio:
    interact: "effects/piano-haunting-melody.mp3"  # 5-10 second clip
```

#### npcs.yaml - NPC Sounds

```yaml
ghost_child:
  name: "The Whisper"
  
  # NEW: NPC sounds
  audio:
    appear: "effects/ghost-materialize.mp3"
    disappear: "effects/ghost-fade.mp3"
    interact: "effects/child-whisper.mp3"
    
butler_jenkins:
  name: "Jenkins"
  
  audio:
    greet: "effects/butler-greeting.mp3"
    reveal_secret: "effects/dramatic-revelation.mp3"
```

---

## Asset Creation & Sourcing

### AI-Generated Audio

#### Music Generation Tools

| Tool | URL | Best For | Cost |
|------|-----|----------|------|
| **Suno** | suno.ai | Full tracks, vocals | Free tier + paid |
| **Udio** | udio.com | Genre-specific | Free tier + paid |
| **Stable Audio** | stability.ai | Ambient, drones | API access |
| **AIVA** | aiva.ai | Orchestral | Free tier + paid |
| **Soundraw** | soundraw.io | Customizable loops | Subscription |

#### Sound Effect Generation

| Tool | URL | Best For | Notes |
|------|-----|----------|-------|
| **ElevenLabs SFX** | elevenlabs.io | Realistic effects | Text-to-SFX |
| **Stable Audio** | stability.ai | Ambient textures | Prompt-based |
| **AudioGen (Meta)** | Open source | Various effects | Self-hosted |

#### AI Generation Tips

1. **Be Specific**: "Creaky wooden door in old mansion" > "door sound"
2. **Specify Duration**: "15-second seamless loop" or "2-second one-shot"
3. **Describe Mood**: "Eerie, unsettling" helps AI match tone
4. **Iterate**: Generate 5-10 variations, pick the best
5. **Post-Process**: Almost all AI audio benefits from DAW editing

### DAW Production

#### Workflow for Game Audio

1. **Plan Audio Budget**
   - List all needed tracks/effects
   - Estimate production time
   - Prioritize by impact

2. **Create Template Project**
   - Consistent sample rate (44.1kHz)
   - Master bus with limiter
   - Organized track groups (music, ambience, SFX)

3. **Record/Synthesize Base Sounds**
   - Use virtual instruments for music
   - Record foley for realistic SFX
   - Layer synthesized elements

4. **Process for Game**
   - Normalize levels (-6dB to -3dB)
   - Apply subtle compression
   - Ensure clean loop points
   - Export in multiple formats

#### Essential VST Plugins (Free)

| Plugin | Type | Use Case |
|--------|------|----------|
| **Vital** | Synth | Pads, drones, textures |
| **TAL-Reverb** | Reverb | Room ambience |
| **Valhalla Supermassive** | Reverb | Huge spaces, ethereal |
| **TDR Kotelnikov** | Compressor | Dynamics control |
| **Spitfire LABS** | Instruments | Orchestral, piano, choir |

### Royalty-Free Sources

#### High-Quality Free Sources

| Source | URL | License | Best For |
|--------|-----|---------|----------|
| **Freesound.org** | freesound.org | CC0/CC-BY | Sound effects |
| **Free Music Archive** | freemusicarchive.org | Various CC | Background music |
| **BBC Sound Effects** | bbcsfx.acropolis.org.uk | Personal/edu | Realistic SFX |
| **Incompetech** | incompetech.com | CC-BY | Diverse music |
| **Pixabay** | pixabay.com/music | Pixabay License | Music & SFX |

#### Commercial Libraries (One-Time Purchase)

| Library | URL | Price Range | Best For |
|---------|-----|-------------|----------|
| **Sonniss GDC Bundle** | sonniss.com | Free annually | Game SFX |
| **Artlist** | artlist.io | Subscription | Music |
| **Epidemic Sound** | epidemicsound.com | Subscription | Music & SFX |

---

## Implementation Roadmap

### Phase 1: Main Menu Music (Week 1-2)

**Goal**: Simple music loop on the main/world selection screen.

**Tasks**:
1. Install Howler.js: `npm install howler`
2. Create `AudioManager` singleton class
3. Add mute/volume controls to UI header
4. Source/create one atmospheric track
5. Play music on app load, stop on game start

**Deliverables**:
- [ ] Howler.js integrated
- [ ] Basic `useAudio` hook
- [ ] Volume controls in header
- [ ] One main menu track
- [ ] localStorage for audio preferences

### Phase 2: World Music & Basic Ambience (Week 3-4)

**Goal**: Each world has unique music; locations have basic ambience.

**Tasks**:
1. Create/source music for each world
2. Add `audio` section to `world.yaml` schema
3. Implement music crossfade on world change
4. Add basic ambience files for key locations
5. Implement ambience switching on location change

**Deliverables**:
- [ ] 3 world music tracks (one per world)
- [ ] Schema for `world.yaml` audio
- [ ] Crossfade between tracks
- [ ] 5-10 ambient location sounds
- [ ] Automatic ambience switching

### Phase 3: Sound Effects (Week 5-6)

**Goal**: Player actions produce audio feedback.

**Tasks**:
1. Define sound effect schema for items/interactions
2. Create sound sprite file (single file, multiple sounds)
3. Implement effect triggering from game state changes
4. Add interaction sounds to `cursed-manor` world
5. Implement random occurrence sounds

**Deliverables**:
- [ ] Sound effect schema in YAML
- [ ] 15-20 basic sound effects
- [ ] Sound sprite for efficient loading
- [ ] Random sound scheduler
- [ ] Interaction sound triggers

### Phase 4: Dynamic Music System (Week 7-8)

**Goal**: Music responds to game state with stem mixing.

**Tasks**:
1. Create stem files for one world
2. Implement stem mixer in AudioManager
3. Add `music_mood` to location config
4. Connect game state (danger, discovery) to stem volumes
5. Test and balance levels

**Deliverables**:
- [ ] 4 stem tracks for `cursed-manor`
- [ ] Stem mixing controls
- [ ] Mood-based automatic mixing
- [ ] State-reactive music changes
- [ ] Audio debug panel (optional)

### Phase 5: Polish & World Expansion (Week 9+)

**Goal**: Full audio for all worlds, polish, optimization.

**Tasks**:
1. Create audio assets for remaining worlds
2. Optimize file sizes and loading
3. Add preloading for smooth playback
4. Implement audio for victory/game over
5. Document audio creation process

**Deliverables**:
- [ ] Complete audio for all worlds
- [ ] Asset optimization
- [ ] Audio preloader
- [ ] Game event sounds
- [ ] Audio creation guide

---

## File Organization

### Directory Structure

```
worlds/
└── cursed-manor/
    ├── world.yaml
    ├── locations.yaml
    ├── npcs.yaml
    ├── items.yaml
    ├── images/
    │   └── ...
    └── audio/                    # NEW
        ├── music/
        │   ├── main-theme.mp3    # Primary music loop
        │   ├── main-theme.ogg    # Firefox fallback
        │   └── stems/            # Optional stem files
        │       ├── base.mp3
        │       ├── tension.mp3
        │       ├── melody.mp3
        │       └── accent.mp3
        ├── ambience/
        │   ├── entrance-wind.mp3
        │   ├── library-fire.mp3
        │   ├── basement-drips.mp3
        │   └── ...
        └── effects/
            ├── door-creak.mp3
            ├── key-pickup.mp3
            ├── ghost-appear.mp3
            ├── thunder.mp3
            └── ...

frontend/
└── src/
    └── audio/                    # NEW
        ├── AudioManager.ts       # Core audio engine
        ├── hooks/
        │   └── useAudio.tsx      # React hook
        └── sprites/
            └── common-sfx.json   # Sound sprite definitions
```

### Naming Conventions

| Type | Format | Example |
|------|--------|---------|
| Music | `{world-id}-{type}.mp3` | `cursed-manor-main.mp3` |
| Stems | `{world-id}-{stem-name}.mp3` | `cursed-manor-tension.mp3` |
| Ambience | `{location-id}-{element}.mp3` | `library-fire-crackling.mp3` |
| Effects | `{action/object}.mp3` | `door-creak.mp3` |

### File Size Guidelines

| Type | Target Size | Notes |
|------|-------------|-------|
| Music tracks | < 3 MB | 3-5 min at 128-192 kbps |
| Ambient loops | < 1 MB | 30-60 sec at 128 kbps |
| Sound effects | < 100 KB | 1-5 sec at 128 kbps |
| Sound sprites | < 500 KB | Multiple short sounds |

---

## Quick Start: Adding Music to Main Screen

Here's the minimal implementation to get music playing on the main screen:

### 1. Install Dependencies

```bash
cd frontend
npm install howler
npm install --save-dev @types/howler
```

### 2. Create Audio Manager

```typescript
// src/audio/AudioManager.ts
import { Howl } from 'howler';

class AudioManager {
  private static instance: AudioManager;
  private menuMusic: Howl | null = null;
  private isMuted: boolean = false;
  private volume: number = 0.5;

  static getInstance(): AudioManager {
    if (!AudioManager.instance) {
      AudioManager.instance = new AudioManager();
    }
    return AudioManager.instance;
  }

  init() {
    // Load preferences
    const savedVolume = localStorage.getItem('audio_volume');
    const savedMuted = localStorage.getItem('audio_muted');
    
    if (savedVolume) this.volume = parseFloat(savedVolume);
    if (savedMuted) this.isMuted = savedMuted === 'true';
    
    // Initialize menu music
    this.menuMusic = new Howl({
      src: ['/audio/menu-theme.mp3', '/audio/menu-theme.ogg'],
      loop: true,
      volume: this.isMuted ? 0 : this.volume,
    });
  }

  playMenuMusic() {
    if (this.menuMusic && !this.menuMusic.playing()) {
      this.menuMusic.play();
    }
  }

  stopMenuMusic() {
    if (this.menuMusic) {
      this.menuMusic.fade(this.volume, 0, 1000);
      setTimeout(() => this.menuMusic?.stop(), 1000);
    }
  }

  setVolume(vol: number) {
    this.volume = vol;
    this.menuMusic?.volume(this.isMuted ? 0 : vol);
    localStorage.setItem('audio_volume', vol.toString());
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    this.menuMusic?.volume(this.isMuted ? 0 : this.volume);
    localStorage.setItem('audio_muted', this.isMuted.toString());
    return this.isMuted;
  }

  getVolume() { return this.volume; }
  getMuted() { return this.isMuted; }
}

export const audioManager = AudioManager.getInstance();
```

### 3. Create React Hook

```typescript
// src/hooks/useAudio.tsx
import { useState, useEffect } from 'react';
import { audioManager } from '../audio/AudioManager';

export function useAudio() {
  const [isMuted, setIsMuted] = useState(audioManager.getMuted());
  const [volume, setVolume] = useState(audioManager.getVolume());

  useEffect(() => {
    audioManager.init();
  }, []);

  const toggleMute = () => {
    const newMuted = audioManager.toggleMute();
    setIsMuted(newMuted);
  };

  const changeVolume = (vol: number) => {
    audioManager.setVolume(vol);
    setVolume(vol);
  };

  return {
    isMuted,
    volume,
    toggleMute,
    setVolume: changeVolume,
    playMenuMusic: () => audioManager.playMenuMusic(),
    stopMenuMusic: () => audioManager.stopMenuMusic(),
  };
}
```

### 4. Add Volume Control to Header

```tsx
// In App.tsx header section
import { useAudio } from './hooks/useAudio';

function GameContent({ setView }) {
  const { isMuted, toggleMute, playMenuMusic, stopMenuMusic } = useAudio();
  
  // Play menu music when no game active
  useEffect(() => {
    if (!sessionId) {
      playMenuMusic();
    } else {
      stopMenuMusic();
    }
  }, [sessionId]);

  return (
    <header>
      {/* ... existing header ... */}
      <button onClick={toggleMute}>
        {isMuted ? '🔇' : '🔊'}
      </button>
    </header>
  );
}
```

### 5. Add Audio File

Place a music file at:
```
frontend/public/audio/menu-theme.mp3
```

---

## Text-to-SFX Prompt Generation

Modern AI sound effect generators like ElevenLabs Sound Effects, Stable Audio, and AudioGen can create realistic sounds from text descriptions. The key to quality output is **well-crafted prompts**. This section describes how to systematically generate prompts from GAIME world data.

### Prompt Anatomy

An effective text-to-SFX prompt contains several components:

```
[SOUND TYPE] + [MATERIAL/SOURCE] + [ACTION/STATE] + [ENVIRONMENT] + [QUALITIES] + [DURATION]
```

**Example:**
> "Heavy wooden door creaking open slowly in a stone corridor, echoing, eerie, 3 seconds"

| Component | Purpose | Examples |
|-----------|---------|----------|
| Sound Type | What category of sound | door, footsteps, ambient, impact |
| Material/Source | Physical properties | wooden, metal, glass, fabric |
| Action/State | What's happening | opening, crackling, dripping, humming |
| Environment | Acoustic space | large hall, small room, outdoors, cave |
| Qualities | Mood/character | eerie, gentle, harsh, distant |
| Duration | Length needed | 2 seconds, 30-second loop |

### Deriving Prompts from World YAML

The world definition files contain rich descriptive text that can be parsed to generate SFX prompts.

#### Source Data Mapping

| YAML Source | Prompt Elements | Example Extraction |
|-------------|-----------------|-------------------|
| `world.theme` | Overall mood, era | "Victorian gothic" → "old, creaky, dusty" |
| `world.tone` | Emotional qualities | "atmospheric, mysterious" → "eerie, unsettling" |
| `location.atmosphere` | Environment, materials | "marble tiles, crystal chandelier" → materials |
| `location.details` | Specific objects | "grandfather clock" → "clock ticking mechanism" |
| `item.examine` | Object properties | "heavy iron key" → "metallic, weighty" |
| `npc.appearance` | Character sounds | "translucent figure" → "ethereal, whisper-like" |
| `interaction.narrative_hint` | Action sounds | "bookshelf swings open" → "mechanical click, wood sliding" |

#### Prompt Generation Templates

**For Location Ambience:**

```
Template: "[WEATHER/ATMOSPHERE] sounds in a [LOCATION TYPE] with [KEY FEATURES], 
          [MOOD from world.tone], seamless 45-second loop"

Example Input (from locations.yaml):
  entrance_hall:
    atmosphere: |
      Rain hammers against the windows, and occasional lightning 
      illuminates the decay. The air smells of old wood and dust.

Generated Prompt:
  "Heavy rain against old glass windows with distant thunder rumbles, 
   inside a grand Victorian entrance hall with high ceilings, 
   atmospheric and eerie, seamless 45-second loop"
```

**For Interaction Sounds:**

```
Template: "[OBJECT] [ACTION] in [ENVIRONMENT], [MATERIAL] texture, 
          [MOOD], [DURATION] one-shot"

Example Input (from locations.yaml):
  interactions:
    pull_red_book:
      narrative_hint: "A mechanical click. A section of bookshelf swings inward"

Generated Prompt:
  "Old book being pulled from wooden shelf triggering hidden mechanism, 
   followed by heavy bookcase section swinging open on rusty hinges, 
   dusty library environment, suspenseful, 4-second one-shot"
```

**For Item Sounds:**

```
Template: "[ITEM MATERIAL] [ITEM TYPE] being [ACTION], [QUALITIES from examine], 
          [DURATION]"

Example Input (from items.yaml):
  iron_key:
    name: "Heavy Iron Key"
    examine: "An old iron key, heavy and cold. The head is shaped like a serpent."

Generated Prompts:
  Take: "Heavy antique iron key picked up from stone surface, 
         metallic clinking and jingling, 1.5 seconds"
  Use:  "Old iron key inserted into rusty lock mechanism and turned with effort, 
         satisfying mechanical click at end, 3 seconds"
```

**For NPC Sounds:**

```
Template: "[NPC TYPE] [ACTION/STATE], [APPEARANCE QUALITIES], 
          [PERSONALITY TRAITS as audio qualities], [DURATION]"

Example Input (from npcs.yaml):
  ghost_child:
    appearance: "A translucent figure of a young girl, perhaps eight years old.
                 Her form flickers like candlelight."
    personality:
      traits: [innocent, helpful, sad]

Generated Prompts:
  Appear: "Ghostly child materializing with soft ethereal shimmer, 
           gentle and melancholic, slight reverb, 2 seconds"
  Ambient: "Faint child-like humming, distant and sad, 
            with subtle otherworldly reverb, 8-second loop"
```

### Automated Prompt Generation System

The World Builder could include an audio prompt generator that analyzes YAML files:

```python
# Conceptual implementation for backend/app/llm/audio_prompt_generator.py

class AudioPromptGenerator:
    """Generates text-to-SFX prompts from world definition data."""
    
    def __init__(self, world_data: WorldDefinition):
        self.world = world_data
        self.mood_keywords = self._extract_mood_keywords()
    
    def _extract_mood_keywords(self) -> list[str]:
        """Extract mood words from theme and tone."""
        # Parse world.theme and world.tone for audio-relevant adjectives
        # "Victorian gothic horror" → ["old", "dark", "creaky", "dusty"]
        # "atmospheric, mysterious" → ["eerie", "unsettling", "ambient"]
        pass
    
    def generate_location_ambience_prompt(self, location_id: str) -> str:
        """Generate ambient loop prompt for a location."""
        location = self.world.locations[location_id]
        
        # Extract key elements from atmosphere text
        elements = self._parse_atmosphere(location.atmosphere)
        
        prompt = f"{elements['weather']} sounds in a {elements['space_type']}"
        prompt += f" with {elements['features']}"
        prompt += f", {', '.join(self.mood_keywords[:2])}"
        prompt += ", seamless 45-second loop"
        
        return prompt
    
    def generate_interaction_prompt(
        self, 
        location_id: str, 
        interaction_id: str
    ) -> str:
        """Generate one-shot sound prompt for an interaction."""
        interaction = self.world.locations[location_id].interactions[interaction_id]
        
        # Parse the narrative_hint for action verbs and objects
        action_data = self._parse_narrative_hint(interaction.narrative_hint)
        
        prompt = f"{action_data['object']} {action_data['action']}"
        prompt += f" in {self._get_location_type(location_id)}"
        prompt += f", {action_data['material']} texture"
        prompt += f", {self.mood_keywords[0]}, {action_data['duration']}"
        
        return prompt
    
    def generate_item_prompts(self, item_id: str) -> dict[str, str]:
        """Generate prompts for item take/use/examine sounds."""
        item = self.world.items[item_id]
        
        # Extract material and qualities from examine text
        properties = self._parse_item_description(item.examine)
        
        return {
            "take": f"{properties['material']} {item.name} picked up, "
                   f"{properties['qualities']}, 1.5 seconds",
            "use": f"{item.name} being used, {properties['use_sound_hint']}, "
                   f"2-3 seconds",
            "examine": f"Handling {properties['material']} object, "
                      f"turning it over, subtle {properties['material']} sounds, "
                      f"2 seconds"
        }
    
    def generate_all_prompts(self) -> dict:
        """Generate complete audio prompt manifest for the world."""
        manifest = {
            "world_id": self.world.id,
            "ambience": {},
            "interactions": {},
            "items": {},
            "npcs": {},
            "random_sounds": []
        }
        
        # Generate for all locations
        for loc_id in self.world.locations:
            manifest["ambience"][loc_id] = self.generate_location_ambience_prompt(loc_id)
            
            for int_id in self.world.locations[loc_id].interactions:
                key = f"{loc_id}/{int_id}"
                manifest["interactions"][key] = self.generate_interaction_prompt(loc_id, int_id)
        
        # Generate for all items
        for item_id in self.world.items:
            manifest["items"][item_id] = self.generate_item_prompts(item_id)
        
        # Generate random sound prompts based on theme
        manifest["random_sounds"] = self._generate_thematic_random_sounds()
        
        return manifest
```

### Prompt Quality Guidelines

#### Be Specific About Materials

| Vague ❌ | Specific ✅ |
|---------|------------|
| "door sound" | "heavy oak door with iron hinges" |
| "footsteps" | "leather boots on wet cobblestones" |
| "key sound" | "large brass skeleton key in rusty lock" |

#### Include Acoustic Environment

| Missing Context ❌ | With Context ✅ |
|-------------------|----------------|
| "water dripping" | "water dripping in stone basement with echo" |
| "fire crackling" | "fireplace crackling in large carpeted room, muffled" |
| "clock ticking" | "grandfather clock ticking in silent hallway, resonant" |

#### Specify Emotional Quality

| Neutral ❌ | Emotionally Colored ✅ |
|-----------|----------------------|
| "wind blowing" | "mournful wind howling through broken windows" |
| "piano notes" | "melancholic piano notes, slightly out of tune, ghostly" |
| "child's voice" | "distant, ethereal child's whisper, sad and lonely" |

### Example: Complete Prompt Set for Cursed Manor

Generated from the `cursed-manor` world YAML files:

```yaml
# audio_prompts.yaml (generated output)

world: cursed-manor
mood_keywords: [eerie, gothic, Victorian, decayed, supernatural, melancholic]

ambience:
  entrance_hall: |
    Heavy rain against tall grimy windows with distant thunder, 
    inside a grand decayed Victorian entrance hall with marble floors 
    and dusty chandelier, wind whistling through gaps, 
    eerie and melancholic, seamless 60-second loop
  
  library: |
    Gentle fire crackling in stone fireplace, old pages occasionally 
    rustling in cold draft, distant wind outside, large room with 
    tall bookshelves absorbing sound, contemplative and unsettling, 
    seamless 45-second loop
  
  basement: |
    Slow water dripping onto stone, faint scratching of rats in walls,
    distant metallic groaning of old pipes, cold damp basement with 
    echo, oppressive and claustrophobic, seamless 40-second loop
  
  ritual_chamber: |
    Low ominous drone or hum, subtle otherworldly whispers at edge 
    of hearing, candle flames flickering, ancient underground stone 
    chamber, deeply unsettling and supernatural, seamless 50-second loop

interactions:
  library/pull_red_book: |
    Old leather-bound book being pulled from wooden shelf, 
    hidden mechanical click and grinding of stone mechanism, 
    heavy bookcase section slowly swinging open on ancient hinges,
    dusty library, suspenseful, 4-second one-shot
  
  sitting_room/play_piano: |
    Ghostly piano playing melancholic Victorian melody by itself,
    slightly out of tune, keys pressing without visible cause,
    grand piano in dusty parlor, haunting and sad, 8-second clip
  
  master_bedroom/examine_mirror: |
    Supernatural shimmer and distortion, brief ghostly whisper,
    cold wind from nowhere, unsettling revelation sound,
    2-second dramatic sting

items:
  iron_key:
    take: |
      Heavy antique iron key picked up from wooden surface,
      cold metallic jingle, weighty and solid, 1.5 seconds
    use: |
      Large iron key inserted into old lock, rusty mechanism 
      turning with resistance, satisfying heavy clunk as lock opens,
      3 seconds
  
  candlestick:
    take: |
      Tarnished silver candlestick lifted from mantelpiece,
      slight metallic scrape, cold hard surface, 1 second
    use_with_matches: |
      Match striking and flaring, candlewick catching flame,
      gentle whoosh of fire taking hold, warm crackling, 2.5 seconds
  
  grimoire:
    take: |
      Ancient leather tome lifted from stone pedestal,
      disturbing otherworldly whisper as it moves,
      heavy book with crackling spine, 2 seconds
    examine: |
      Old parchment pages turning, dry crackle of ancient paper,
      faint whispers emanating from text, 3 seconds

npcs:
  ghost_child:
    appear: |
      Ethereal materialization with soft shimmer and cold wind,
      faint child's sigh, supernatural but gentle, 2 seconds
    disappear: |
      Ghostly figure fading with melancholic whisper,
      sound of small footsteps retreating into nothing, 2 seconds
    interact: |
      Soft childlike whisper at edge of hearing, words unclear,
      accompanied by slight temperature drop sound (subtle wind),
      3 seconds
  
  butler_jenkins:
    greet: |
      Formal throat clearing, old man's tired sigh,
      subtle creak of old joints, Victorian formality, 2 seconds
    reveal_secret: |
      Heavy emotional sigh, creaking as old man leans forward,
      low dramatic undertone, 3 seconds

random_sounds:
  - prompt: |
      Sudden crack of thunder, not too close, followed by 
      rumbling echo, Victorian manor during storm, 4 seconds
    suggested_name: thunder_rumble
    frequency: occasional
  
  - prompt: |
      Old wooden floorboards creaking under unseen weight,
      as if someone invisible walking slowly,
      old house settling but unsettling, 2 seconds
    suggested_name: phantom_footsteps
    frequency: rare
  
  - prompt: |
      Clock striking single chime, deep resonant grandfather clock,
      with metallic reverberations fading, 3 seconds
    suggested_name: clock_chime
    frequency: regular
  
  - prompt: |
      Sudden cold wind gust from nowhere indoors,
      papers or curtains rustling, supernatural presence hint,
      2 seconds
    suggested_name: supernatural_gust
    frequency: rare
```

### Integration with Text-to-SFX APIs

Once prompts are generated, they can be fed to AI sound generation APIs:

```typescript
// Conceptual frontend integration

interface SFXGenerationRequest {
  prompt: string;
  duration_seconds: number;
  output_format: 'mp3' | 'wav';
}

async function generateSoundEffect(prompt: string): Promise<Blob> {
  // ElevenLabs Sound Effects API example
  const response = await fetch('https://api.elevenlabs.io/v1/sound-generation', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${ELEVENLABS_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: prompt,
      duration_seconds: 3,
      prompt_influence: 0.5
    })
  });
  
  return response.blob();
}

// Batch generation from manifest
async function generateAllSFX(manifest: AudioPromptManifest) {
  for (const [id, prompt] of Object.entries(manifest.interactions)) {
    const audio = await generateSoundEffect(prompt);
    await saveAudioFile(audio, `effects/${id}.mp3`);
  }
}
```

---

## Music Creative Brief Generation

When using AI composers or human musicians, a well-structured **creative brief** ensures the delivered music matches the world's atmosphere. The World Builder can automatically generate these briefs from world data.

### Creative Brief Structure

A complete music creative brief should include:

```
┌─────────────────────────────────────────────────────────────┐
│                    MUSIC CREATIVE BRIEF                      │
├─────────────────────────────────────────────────────────────┤
│  1. Project Overview                                         │
│     - Game name, world name, target audience                │
│                                                              │
│  2. Emotional Journey                                        │
│     - How should players FEEL throughout the game?          │
│     - Key emotional beats and transitions                   │
│                                                              │
│  3. Musical Style & References                              │
│     - Genre, era, instrumentation                           │
│     - Reference tracks (existing music that evokes mood)    │
│                                                              │
│  4. Technical Requirements                                   │
│     - Format, duration, loop points                         │
│     - Stem breakdown (if applicable)                        │
│                                                              │
│  5. Location/State Variations                               │
│     - How music should differ by area or game state         │
│                                                              │
│  6. Do's and Don'ts                                         │
│     - Specific guidance on what to include/avoid            │
└─────────────────────────────────────────────────────────────┘
```

### Automatic Brief Generation from World YAML

```python
# Conceptual: backend/app/llm/music_brief_generator.py

class MusicBriefGenerator:
    """Generates music creative briefs from world definition."""
    
    # Mapping from theme keywords to musical suggestions
    THEME_TO_MUSIC = {
        "gothic": {
            "genres": ["dark classical", "chamber music", "dark ambient"],
            "instruments": ["piano", "strings", "choir", "pipe organ"],
            "qualities": ["minor key", "slow tempo", "sparse", "reverberant"],
            "references": ["Nox Arcana", "Midnight Syndicate", "Akira Yamaoka"]
        },
        "horror": {
            "genres": ["dark ambient", "industrial", "tension underscore"],
            "instruments": ["synthesizers", "prepared piano", "drones", "dissonant strings"],
            "qualities": ["unsettling", "unpredictable", "building tension"],
            "references": ["Silent Hill OST", "Resident Evil OST", "Amnesia OST"]
        },
        "victorian": {
            "genres": ["romantic classical", "chamber music", "parlor music"],
            "instruments": ["piano", "violin", "cello", "harpsichord"],
            "qualities": ["elegant", "melancholic", "refined", "period-accurate"],
            "references": ["Chopin Nocturnes", "Brahms", "Victorian parlor music"]
        },
        "sci-fi": {
            "genres": ["synthwave", "electronic", "ambient"],
            "instruments": ["synthesizers", "electronic drums", "bass"],
            "qualities": ["futuristic", "cold", "mechanical", "spacious"],
            "references": ["Blade Runner OST", "Deus Ex OST", "Mass Effect OST"]
        },
        "prison": {
            "genres": ["industrial", "dark ambient", "minimal"],
            "instruments": ["metallic percussion", "drones", "processed sounds"],
            "qualities": ["oppressive", "cold", "claustrophobic", "rhythmic"],
            "references": ["The Shawshank Redemption OST", "Escape from Butcher Bay OST"]
        }
    }
    
    def generate_brief(self, world: WorldDefinition) -> str:
        """Generate complete creative brief as formatted text."""
        
        # Analyze world for musical direction
        themes = self._extract_themes(world.theme)
        musical_style = self._derive_musical_style(themes)
        locations_analysis = self._analyze_locations(world.locations)
        emotional_arc = self._map_emotional_journey(world)
        
        brief = self._format_brief(
            world=world,
            style=musical_style,
            locations=locations_analysis,
            emotions=emotional_arc
        )
        
        return brief
```

### Example Generated Brief: Cursed Manor

```markdown
# MUSIC CREATIVE BRIEF
## The Cursed Manor - GAIME Audio

### Project Overview

**Game**: GAIME (AI-Powered Text Adventure)
**World**: The Cursed Manor
**Genre**: Victorian Gothic Horror
**Target Audience**: Players seeking atmospheric, narrative-driven horror experiences
**Platform**: Web browser (audio will be streamed/downloaded)

---

### Emotional Journey

The player progresses through distinct emotional phases:

| Phase | Locations | Emotional State | Musical Approach |
|-------|-----------|-----------------|------------------|
| **1. Arrival** | Entrance Hall | Unease, curiosity | Subtle, ambient, establishing dread |
| **2. Exploration** | Library, Dining Room, Kitchen | Growing tension, mystery | Building layers, melodic hints |
| **3. Discovery** | Nursery, Master Bedroom | Sadness, horror | Emotional melody, dissonance |
| **4. Confrontation** | Basement, Secret Passage | Fear, determination | Intense, driving undertones |
| **5. Resolution** | Ritual Chamber | Climax, then release | Full arrangement → peaceful resolution |

**Key Emotional Beats**:
- First ghost encounter: sudden emotional weight, melancholy
- Finding each artifact: sense of dark importance, ritual significance
- Final ritual: cathartic crescendo, release of tension

---

### Musical Style & References

**Primary Genre**: Dark Victorian Chamber Music meets Gothic Horror Ambient

**Era/Period**: Late Victorian (1880s-1900s) with supernatural undertones

**Instrumentation** (in order of prominence):
1. **Piano** - Primary melodic instrument, slightly detuned for unease
2. **String Quartet** - Tension, swells, emotional weight
3. **Low Choir/Voices** - Supernatural moments, whispered textures
4. **Music Box** - Childhood/nursery themes, innocence corrupted
5. **Pipe Organ** - Ritual chamber, religious/occult grandeur
6. **Subtle Electronics** - Modern production only, no synth leads

**Tempo Range**: 50-80 BPM (slow, deliberate, never rushed)

**Key**: Primarily minor keys (A minor, D minor), occasional Phrygian mode for ritual elements

**Reference Tracks** (for mood, not imitation):
- "Theme of Laura" - Silent Hill 2 (melancholic piano, emotional weight)
- Nox Arcana - "Transylvania" album (Victorian gothic atmosphere)
- "Bloodborne Main Theme" - opening restraint building to intensity
- Chopin - Nocturne Op. 9 No. 2 (elegant sadness, Victorian piano style)
- "Old Blood" - The Order 1886 OST (period-appropriate orchestration)

---

### Technical Requirements

**Deliverables**:

| Track | Duration | Format | Notes |
|-------|----------|--------|-------|
| Main Theme (Full Mix) | 3-4 minutes | Seamless loop | Must loop without audible gap |
| Base Stem (Drone/Pad) | 3-4 minutes | Seamless loop | Always plays, foundation |
| Tension Stem (Strings) | 3-4 minutes | Seamless loop | Fades in for danger/discovery |
| Melody Stem (Piano) | 3-4 minutes | Seamless loop | Location-dependent intensity |
| Accent Stem (Choir/Hits) | 3-4 minutes | Seamless loop | Triggered by events |

**All stems must be**:
- Exactly the same duration (to the sample)
- Same BPM (locked to grid)
- Same time signature (4/4 recommended)
- Able to play together as full mix OR independently
- Loop-ready (seamless at loop point)

**File Format**: 
- WAV 44.1kHz 24-bit (for editing)
- MP3 192kbps + OGG Vorbis (for game delivery)

**Loudness**: -14 LUFS integrated, peaks no higher than -1dB

---

### Location/State Variations

The stems should be designed so different combinations evoke different spaces:

| Location | Base | Tension | Melody | Accent | Mood |
|----------|:----:|:-------:|:------:|:------:|------|
| Entrance Hall | 100% | 20% | 30% | - | Unsettling first impression |
| Library | 100% | 10% | 60% | - | Contemplative, mysterious |
| Dining Room | 100% | 40% | 20% | - | Something watching |
| Kitchen | 100% | 30% | 10% | - | Mundane but wrong |
| Nursery | 100% | 20% | 80%* | - | Sad, music box variation |
| Basement | 100% | 70% | 10% | - | Danger, oppressive |
| Ritual Chamber | 100% | 50% | 40% | 60% | Supernatural climax |

*Nursery could use music box sound replacing piano melody

**State-Based Modulation**:
- Ghost present: +30% Tension, +20% Accent
- Holding artifact: +10% Accent (subtle power hum)
- Low trust with Jenkins: +20% Tension
- Near victory: Full crescendo build

---

### Stem Design Guidance

**BASE STEM (Drone/Pad)**:
- Low sustained strings or synth pad
- Very slow movement, almost static
- Root note focus (A2-A3 range)
- Should feel like "the house breathing"
- Subtle filtering/movement to prevent ear fatigue

**TENSION STEM (Strings)**:
- Tremolo strings, col legno, sul ponticello techniques
- Dissonant intervals (minor 2nds, tritones)
- Swells and retreats, never constant
- Should raise heartrate when prominent
- High register (A4-A6 range) for unease

**MELODY STEM (Piano)**:
- Victorian-style melodic fragments
- Melancholic, Chopin-esque phrasing
- Occasional "wrong notes" or hesitation
- Should carry emotional narrative
- Mid register (C3-C5 range)

**ACCENT STEM (Choir/Hits)**:
- Wordless choir "oohs" and "aahs"
- Occasional orchestral hits (not overused)
- Supernatural shimmer sounds
- Should punctuate moments of significance
- Very sparse - silence is powerful

---

### Do's and Don'ts

**DO**:
✅ Embrace silence and space - horror lives in anticipation
✅ Use period-appropriate sounds (no modern synth leads)
✅ Create emotional contrast (beauty amid horror)
✅ Make the piano slightly imperfect (tuning, timing)
✅ Reference the storm occasionally (low thunder rolls in base)
✅ Build tension gradually, release rarely
✅ Make loops genuinely seamless - players will hear them for hours

**DON'T**:
❌ Use jump-scare stingers (we're not a movie)
❌ Make it constantly intense - players will tune out
❌ Use recognizable samples or phrases
❌ Include vocals with words (whispers only, unintelligible)
❌ Add percussion/beats (no drums except in climax)
❌ Over-produce - rawness adds to unease
❌ Make stems that sound "incomplete" alone - each must work solo

---

### Additional Notes

**For the Nursery**: Consider a separate music box motif that can replace or supplement the piano melody. A simple, innocent tune played by music box, slightly slowed/distorted, would powerfully evoke the children's tragedy.

**For Victory**: After the climax in the ritual chamber, music should transition to a peaceful, major-key resolution. The storm passes, dawn breaks. The final 30 seconds should feel like relief and earned peace.

**Silence**: Consider providing 30-60 seconds of near-silence with just the base drone for moments of pure exploration. Sometimes the absence of music is most effective.

---

### Delivery

Please provide:
1. Full mix (all stems combined) as single looping track
2. Individual stems (4 files), same duration
3. Session files (if possible) for future editing
4. Brief notes on suggested loop point (though should be start=end)

**Questions?** Contact [composer liaison] for clarification on any creative points.
```

### World Builder Integration

The World Builder UI could include a "Generate Music Brief" button:

```typescript
// Conceptual API endpoint
POST /api/builder/{world_id}/generate-music-brief

Response:
{
  "brief_markdown": "# MUSIC CREATIVE BRIEF\n## The Cursed Manor...",
  "brief_pdf_url": "/api/builder/cursed-manor/music-brief.pdf",
  "key_attributes": {
    "primary_genre": "Dark Victorian Chamber",
    "tempo_range": "50-80 BPM",
    "key_instruments": ["piano", "strings", "choir"],
    "mood_keywords": ["melancholic", "eerie", "Victorian", "supernatural"],
    "reference_tracks": [...]
  }
}
```

---

## Seamless Looping: Deep Dive

Seamless looping is **critical** for game audio. A noticeable gap, pop, or discontinuity breaks immersion and becomes annoying over extended play. This section explains the theory and practice of creating perfect loops.

### What Makes a Loop Seamless?

A seamless loop has **no audible discontinuity** when playback reaches the end and returns to the beginning. This requires:

1. **Amplitude Continuity**: The volume at the end matches the volume at the start
2. **Phase Continuity**: The waveform at the end connects smoothly to the waveform at the start
3. **Harmonic Continuity**: The musical content (chords, melody) makes sense wrapping around
4. **Reverb/Decay Continuity**: Tails of sounds don't get cut off or double up

```
Perfect Loop:
                                                    
   Start                                      End → Start
     │                                             │
     ▼                                             ▼
    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲ ─→╱╲    ╱╲
   ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲   ╱  ╲  ╱  ╲
  ╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲─╱    ╲╱    ╲
     │                                             │
     └─────────────── Seamless Transition ─────────┘

Bad Loop (amplitude discontinuity):
                                                    
     ╱╲    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲  ╲     ╱╲
    ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╲   ╱  ╲
   ╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲  ───╱    ╲
                                             ▲
                                        CLICK! (discontinuity)
```

### Loop Types

| Loop Type | Description | Use Case |
|-----------|-------------|----------|
| **Hard Loop** | Audio simply repeats from start | Short ambient, SFX |
| **Crossfade Loop** | End fades out while start fades in | Music, long ambient |
| **Musical Loop** | Composed to resolve at start | Best for music |

### Method 1: Crossfade Looping (Easiest)

Crossfading overlaps the end and beginning, creating a smooth transition even if the original audio doesn't perfectly match.

#### DAW Steps (General)

1. **Import/Create your audio** (e.g., 60 seconds of ambience)

2. **Determine overlap region** (typically 2-5 seconds)
   ```
   |◄──────────── Original Audio (60 sec) ────────────►|
   |◄─── Keep (55 sec) ────►|◄── Overlap (5 sec) ───►|
   ```

3. **Duplicate and position**
   ```
   Track 1: |████████████████████████████████████░░░░░| (fade out)
   Track 2: |░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█████| (fade in, copied from start)
   
   Timeline: |─────────────────────────────────────────|
             0                                        60 sec
   ```

4. **Apply fades**
   - Track 1: Linear or exponential fade OUT over last 5 seconds
   - Track 2: Linear or exponential fade IN over same 5 seconds
   - Combined, the volume stays constant

5. **Bounce/Export the combined region**
   - Export only the region that will loop (55 seconds in this example)
   - The "tail" from Track 1 and "head" from Track 2 are baked in

#### Reaper Specific Steps

```
1. Import audio file onto track
2. Split item at 55 seconds (shortcut: S)
3. Select the last 5-second segment, copy (Ctrl+C)
4. Create new track below
5. Paste at project start (Ctrl+V)
6. Select end segment on Track 1: right-click → Item Properties → Fade Out → 5000ms
7. Select start segment on Track 2: right-click → Item Properties → Fade In → 5000ms
8. Set time selection from 0 to 55 seconds
9. File → Render → "Time selection" → Render
```

#### Ableton Live Specific Steps

```
1. Drop audio clip onto arrangement
2. Enable "Loop" on the clip
3. In Clip View, adjust Loop End to desired point
4. Enable "Crossfade" in Warp settings
5. Set crossfade length (2-5 seconds)
6. Export: File → Export Audio/Video → select region
```

### Method 2: Musical Composition for Looping (Best Quality)

For music, the ideal approach is composing with looping in mind from the start.

#### Composition Guidelines

1. **Choose a loop-friendly structure**
   ```
   |: Intro → A → B → A :| (returns to Intro)
   
   NOT:
   Intro → A → B → C → Outro (nowhere to return)
   ```

2. **End on the same chord as the beginning**
   ```
   Measure 1 (Start): Am chord
   Measure 64 (End):  Am chord (or leading tone → Am)
   ```

3. **Maintain rhythmic continuity**
   ```
   If the piece starts on beat 1 of a measure,
   it should end on beat 4 of the previous measure.
   
   |1   2   3   4  |1   2   3   4  |  ...  |1   2   3   4  |1
    ▲ Start                                              ▲ End returns here
   ```

4. **Handle reverb/delay tails**
   - Either: Compose with reverb as part of the music (tails blend)
   - Or: Leave 1-2 seconds of silence at start for tails to decay
   - Or: Use sidechain to duck reverb before loop point

#### Stem Synchronization

When creating stems that must loop together:

1. **Lock all stems to the same tempo grid**
   - Set explicit BPM (e.g., 72.000 BPM, not 72.1)
   - Ensure all MIDI/audio is quantized to grid

2. **Use the same start and end points**
   ```
   All stems: Bar 1, Beat 1 → Bar 33, Beat 1
   Duration: Exactly 32 bars
   ```

3. **Export all stems from the same session**
   - Don't export stems from different projects
   - Use batch export if available

4. **Include count-in if needed**
   - If music doesn't start immediately, include silent bars
   - All stems must include the same silence

### Method 3: Zero-Crossing Editing (For Sound Effects)

For short sound effects or ambient textures, find "zero crossings" where the waveform crosses the center line.

#### Theory

```
Waveform:
                    Zero Crossings
                          ↓
     ╱╲      ╱╲      ╱╲──────── Good cut points
    ╱  ╲    ╱  ╲    ╱  ╲
───╱────╲──╱────╲──╱────╲──── Zero line
   ╲    ╱  ╲    ╱  ╲    ╱
    ╲  ╱    ╲  ╱    ╲  ╱
     ╲╱      ╲╱      ╲╱

Cutting at zero crossing = no click
Cutting at peak = click/pop
```

#### DAW Steps

1. **Zoom in very close** to waveform (sample level)
2. **Find zero crossing near desired end point**
3. **Find zero crossing near desired start point**
4. **Ensure both crossings are going the same direction** (both ascending or both descending)
5. **Trim to these exact points**

Most DAWs have "Snap to Zero Crossing" options:
- **Reaper**: Options → Snap/Grid → Snap to zero crossings
- **Ableton**: Not built-in, zoom and edit manually
- **Logic Pro**: Edit → Snap Regions to Zero Crossings
- **Pro Tools**: Edit → Separate Region → At Zero Crossings

### Export Settings for Looping Audio

#### Recommended Export Settings

| Setting | Value | Reason |
|---------|-------|--------|
| Format (working) | WAV | Lossless, preserves loop points |
| Format (game) | MP3 + OGG | Browser compatibility |
| Bit Depth | 24-bit (working), 16-bit (final) | Quality vs. size |
| Sample Rate | 44.1 kHz | Web standard |
| Dithering | ON when reducing bit depth | Prevents quantization noise |
| Normalize | OFF | Preserve dynamics, normalize in mixer |
| MP3 Bitrate | 192 kbps | Good quality/size balance |
| MP3 Mode | CBR (Constant Bit Rate) | More predictable loop points |

#### MP3 Looping Caveat

⚠️ **MP3 files add silence at the start and end** due to encoder padding. This can cause gaps in loops.

**Solutions**:
1. Use OGG Vorbis instead (better loop support)
2. Use WAV in Howler.js (larger files, perfect loops)
3. Trim silence in post with tools like `mp3trim`
4. Encode with `--nogap` flag in LAME encoder
5. Use Howler.js sprites to define exact loop regions

#### Howler.js Loop Configuration

```typescript
// Standard loop (may have MP3 gap)
const music = new Howl({
  src: ['music.mp3', 'music.ogg'],
  loop: true
});

// Precise loop using sprite (recommended for MP3)
const music = new Howl({
  src: ['music.mp3'],
  sprite: {
    // [offset_ms, duration_ms, loop]
    main: [50, 180000, true]  // Skip 50ms padding, 3 min duration
  }
});

music.play('main');
```

### Testing Your Loops

#### Manual Testing

1. Export your loop
2. Import into a fresh DAW project
3. Duplicate the clip end-to-end: `[loop][loop][loop]`
4. Play across the boundaries at high volume
5. Listen for: clicks, pops, volume dips, musical awkwardness

#### Automated Testing

```python
# Simple loop continuity test
import numpy as np
from scipy.io import wavfile

def test_loop_continuity(wav_path, boundary_samples=100):
    """Check if a WAV file loops seamlessly."""
    rate, data = wavfile.read(wav_path)
    
    # Handle stereo
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    
    # Get boundary regions
    start = data[:boundary_samples]
    end = data[-boundary_samples:]
    
    # Check amplitude match
    start_rms = np.sqrt(np.mean(start**2))
    end_rms = np.sqrt(np.mean(end**2))
    amplitude_diff = abs(start_rms - end_rms) / max(start_rms, end_rms)
    
    # Check zero-crossing alignment
    start_crosses_up = start[0] < 0 and start[1] >= 0
    end_crosses_up = end[-2] < 0 and end[-1] >= 0
    crossing_match = start_crosses_up == end_crosses_up
    
    return {
        'amplitude_difference': f"{amplitude_diff:.2%}",
        'amplitude_ok': amplitude_diff < 0.1,  # <10% difference
        'zero_crossing_match': crossing_match,
        'overall_ok': amplitude_diff < 0.1 and crossing_match
    }
```

### Common Looping Problems & Solutions

| Problem | Symptom | Solution |
|---------|---------|----------|
| **Click/pop** | Sharp transient at loop point | Edit at zero crossings; apply tiny fade |
| **Volume dip** | Quiet moment at loop | Crossfade overlap; adjust fade curves |
| **Volume spike** | Loud moment at loop | Reduce crossfade region; check for phase |
| **Musical awkwardness** | Melody doesn't connect | Recompose ending; use transitional phrase |
| **Reverb tail cut** | Abrupt end of echoes | Extend audio; pre-render reverb; crossfade |
| **Rhythm break** | Beat doesn't continue | Align to bar boundaries; check tempo |
| **MP3 gap** | Brief silence in loop | Use OGG; use sprite definitions; trim padding |

### Looping Checklist

Before delivering a looped audio file:

- [ ] Played loop 10+ times continuously - no artifacts heard
- [ ] Tested at high volume - subtle issues more audible
- [ ] Checked visually in waveform editor for discontinuities
- [ ] Verified file duration is exactly as intended
- [ ] Tested in actual game context (Howler.js in browser)
- [ ] Tested both MP3 and OGG versions
- [ ] Loop works with game's audio engine crossfade (if applicable)

---

## Summary

This document provides a comprehensive roadmap for adding audio to GAIME, from simple background music to a sophisticated dynamic stem-based system. The key is to **start simple** with Phase 1 (main menu music) and **iterate** based on what enhances the player experience most.

Audio should always serve the narrative and atmosphere—it's the invisible layer that makes a haunted manor feel truly haunted.

### Next Steps

1. Review this document with the team
2. Source/create initial menu music track
3. Implement Phase 1 (main menu music)
4. Evaluate and plan subsequent phases

### Resources

- [Howler.js Documentation](https://howlerjs.com/)
- [Web Audio API Guide](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [Game Audio Design Principles](https://www.gamedeveloper.com/audio/game-audio-design)
- [Freesound.org](https://freesound.org/) - CC Sound Effects
