---
name: UI Rework Image Focus
overview: ""
todos:
  - id: create-branch
    content: Create experimental git branch for UI rework
    status: completed
  - id: layout-restructure
    content: Restructure App.tsx with 2/3 + 1/3 grid layout and updated header
    status: completed
  - id: scene-image-fullheight
    content: Update SceneImage to fill container, add inventory overlay badge
    status: completed
  - id: debug-overlay
    content: Move debug toggle to input area, make DebugPanel an overlay
    status: completed
  - id: delete-sidebar
    content: Remove Sidebar component and clean up imports
    status: completed
  - id: responsive-stack
    content: Add responsive breakpoints to stack layout on mobile
    status: completed
  - id: terminal-adjustments
    content: Adjust Terminal for narrower column width
    status: completed
---

# UI Rework: Image-First Layout

## Overview

Redesign the game UI to make scene images the hero element using a 2/3 image + 1/3 text side-by-side layout, eliminating the current sidebar and redistributing its elements.

## New Layout Structure

```
+----------------------------------------------------------------+
| GAIME    "The Cursed Manor"              [Back to Home] [New]  |
+--------------------------------------------+-------------------+
|                                            |                   |
|              SCENE IMAGE                   |    Terminal       |
|              (2/3 width)                   |    (scrolling     |
|                                            |     narrative)    |
|    [Location name overlay - bottom left]   |                   |
|    [Inventory badge - bottom right]        +-------------------+
|                                            | [🔧] [input....] ▶|
+--------------------------------------------+-------------------+
```

On mobile/narrow screens: stacks vertically (image on top, text below).

---

## Changes by Component

### 1. Header Redesign

**File:** [`frontend/src/App.tsx`](frontend/src/App.tsx)

- Remove "World Builder" link (accessible from start screen only)
- Add world name display (e.g., "The Cursed Manor") - fetch from `worldId` or game state
- Rename "Reset" to "Back to Home" with icon, navigates to start screen
- Add compact "New Game" button (currently in sidebar)

### 2. Delete Sidebar Component

**File:** [`frontend/src/components/Sidebar.tsx`](frontend/src/components/Sidebar.tsx)

- Remove entirely - redistribute elements elsewhere
- Location display: already on image, remove
- Turn count: remove (or optionally show in debug mode only)
- Inventory: move to floating overlay on image
- Debug toggle: move near input
- New Game button: move to header

### 3. Rework Main Layout (2/3 + 1/3 split)

**File:** [`frontend/src/App.tsx`](frontend/src/App.tsx)

- Use CSS Grid or Flexbox for `lg:grid-cols-[2fr_1fr]` layout
- Image section takes 2/3 on large screens
- Text column (Terminal + Input) takes 1/3
- On small screens (`<lg`): stack vertically with `flex-col`

### 4. SceneImage Updates

**File:** [`frontend/src/components/SceneImage.tsx`](frontend/src/components/SceneImage.tsx)

- Remove height restrictions (`h-72`, `h-[60vh]`), let it fill container naturally
- Remove click-to-expand behavior (image is now always prominent)
- Keep or simplify the full-screen overlay for zoom (optional)
- Add **Inventory overlay badge** (bottom-right corner):
  - Shows "🎒 3" when collapsed
  - Expands on click/hover to show item list
  - Semi-transparent background, doesn't obstruct image

### 5. Debug Mode Rework

**Files:** [`frontend/src/components/DebugPanel.tsx`](frontend/src/components/DebugPanel.tsx), [`frontend/src/components/CommandInput.tsx`](frontend/src/components/CommandInput.tsx)

- Add debug toggle (🔧 icon) to the left of the input field
- When debug mode is ON and user clicks the icon: show debug panel as **overlay on the image**
- Panel slides in from right or appears as modal over image area
- Doesn't consume space in the text column

### 6. Terminal Adjustments

**File:** [`frontend/src/components/Terminal.tsx`](frontend/src/components/Terminal.tsx)

- Fills available height in text column
- Welcome/start screen: may need layout adjustments for narrower column

---

## Responsive Breakpoints

| Screen Size | Behavior |

|-------------|----------|

| `lg` and up (1024px+) | Side-by-side: 2/3 image, 1/3 text |

| Below `lg` | Stacked: image on top, text/input below (similar to current) |

---

## Files to Modify

1. [`frontend/src/App.tsx`](frontend/src/App.tsx) - Layout restructure, header changes
2. [`frontend/src/components/SceneImage.tsx`](frontend/src/components/SceneImage.tsx) - Full-height, add inventory overlay
3. [`frontend/src/components/CommandInput.tsx`](frontend/src/components/CommandInput.tsx) - Add debug toggle icon
4. [`frontend/src/components/DebugPanel.tsx`](frontend/src/components/DebugPanel.tsx) - Overlay behavior

## Files to Delete

1. [`frontend/src/components/Sidebar.tsx`](frontend/src/components/Sidebar.tsx) - No longer needed

---

## Implementation Notes

- Inventory overlay component could be extracted as `InventoryBadge.tsx` or kept inline in `SceneImage.tsx`
- World name needs to come from game state or API - may need to extend `useGame` hook
- Consider adding subtle animations for inventory expand/collapse and debug panel slide-in
