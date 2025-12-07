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
