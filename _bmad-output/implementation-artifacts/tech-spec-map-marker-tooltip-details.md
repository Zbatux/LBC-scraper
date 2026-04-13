---
title: 'Map Marker Tooltip with Full Details'
slug: 'map-marker-tooltip-details'
created: '2026-04-13'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Leaflet.js 1.9.4', 'Vanilla JS']
files_to_modify: ['templates/map.html']
code_patterns: ['L.marker.bindTooltip', 'L.marker.on click']
test_patterns: []
---

# Tech-Spec: Map Marker Tooltip with Full Details

**Created:** 2026-04-13

## Overview

### Problem Statement

Map markers currently show a Leaflet popup (click) with only titre and prix. No information is shown on hover. Popup is redundant since click already opens LBC directly.

### Solution

Replace `marker.bindPopup(...)` with `marker.bindTooltip(...)` containing titre, prix, superficie, and trajet. Keep `marker.on('click', () => window.open(lien, '_blank'))` unchanged. Remove the popup entirely.

### Scope

**In Scope:**
- Replace `bindPopup` → `bindTooltip` on each marker in `map.html`
- Tooltip content: titre, prix, superficie (if not null), trajet (if not null)
- Click behavior unchanged: opens LBC link in new tab

**Out of Scope:**
- Styling the tooltip beyond Leaflet defaults
- Any other file changes

## Context for Development

### Codebase Patterns

- `map.html` line 132–136: marker creation block
- `marker.bindPopup(...)` at line 134 — replace with `bindTooltip`
- `marker.on('click', ...)` at line 135 — keep as-is
- `a.superficie` and `a.trajet` already present in `/api/annonces` response
- Leaflet `bindTooltip(content, options)` — use `{ sticky: true }` option so tooltip follows cursor
- Format helpers already defined in file: use same `a.prix.toLocaleString('fr-FR')` pattern for superficie

### Files to Reference

| File | Purpose |
| ---- | ------- |
| [templates/map.html](templates/map.html) | Only file to change — marker block at lines 132–136 |

### Technical Decisions

- Use `L.marker.bindTooltip(html, { sticky: true })` — tooltip follows cursor, more natural UX than fixed-position
- Superficie and trajet shown only if not null (same null-guard pattern as prix)
- No popup — remove `bindPopup` call entirely

## Implementation Plan

### Tasks

- [x] Task 1: Replace popup with tooltip in `map.html`
  - File: `templates/map.html`
  - Action: Replace lines 133–135 (the `prix` variable + `bindPopup` + `on click`) with:
    ```js
    const prix   = a.prix       != null ? a.prix.toLocaleString('fr-FR') + ' €'  : null;
    const surf   = a.superficie != null ? a.superficie.toLocaleString('fr-FR') + ' m²' : null;
    const trajet = a.trajet     || null;
    const lines  = [`<strong>${a.titre || 'Annonce'}</strong>`];
    if (prix)   lines.push(prix);
    if (surf)   lines.push(surf);
    if (trajet) lines.push(trajet);
    marker.bindTooltip(lines.join('<br>'), { sticky: true });
    marker.on('click', () => { if (a.lien) window.open(a.lien, '_blank'); });
    ```
  - Notes: `sticky: true` makes the tooltip follow the cursor. Null guard added on `a.lien` (bonus fix from adversarial finding F4).

### Acceptance Criteria

- [x] AC1: Given a marker with all fields set, when hovering it, then a tooltip appears showing titre, prix (formatted), superficie (formatted), and trajet — all on separate lines
- [x] AC2: Given a marker where `superficie` is null, when hovering, then the tooltip shows titre + prix + trajet (no blank line for superficie)
- [x] AC3: Given a marker where `trajet` is null, when hovering, then the tooltip shows titre + prix + superficie (no blank line for trajet)
- [x] AC4: Given any marker, when clicking it, then LBC listing opens in a new tab — no popup appears
- [x] AC5: Given the page loads, then no Leaflet popup is bound to any marker

## Additional Context

### Dependencies

- None (Leaflet already loaded)

### Testing Strategy

- **Manual**:
  1. Start Flask, navigate to `/map`
  2. Hover a marker → verify tooltip shows titre, prix, superficie, trajet
  3. Hover a marker with missing superficie/trajet → verify those lines absent
  4. Click a marker → verify LBC opens, no popup appears

### Notes

- Also fixes adversarial finding F4 (lien null guard) as a bonus — `if (a.lien) window.open(...)`.

## Review Notes

- Adversarial review completed
- Findings: 10 total, 5 fixed, 5 skipped
- Resolution approach: auto-fix
- Fixed: F1 (XSS escaping), F2 (trajet null consistency), F3 (Prix N/A fallback restored), F4 (tooltip max-width 300), F5 (direction: top)
- Skipped: F6 (superficie 0 — data quality, out of scope), F7/F9/F10 (noise)
