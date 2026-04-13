---
title: 'Interactive Map View for Filtered Listings'
slug: 'map-view-filtered-listings'
created: '2026-04-13'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3 / Flask', 'SQLite', 'Vanilla JS (no bundler)', 'Leaflet.js CDN']
files_to_modify: ['web.py', 'templates/index.html', 'templates/map.html (new)', 'tests/test_web_api.py']
code_patterns: ['render_template for page routes', 'URLSearchParams for filter state', 'fetch /api/annonces client-side']
test_patterns: ['pytest', 'web.app.test_client()', 'monkeypatch for DB_NAME']
---

# Tech-Spec: Interactive Map View for Filtered Listings

**Created:** 2026-04-13

## Overview

### Problem Statement

No geographic visualization of listings exists. After filtering listings in the main table, there is no way to see their distribution on a map.

### Solution

Add a dedicated `/map` Flask route serving a Leaflet.js-powered map page. A "Voir sur carte" button in `index.html` serializes the current filter state as URL query params and navigates to `/map?<params>`. The map page fetches `/api/annonces`, applies the same filter logic from URL params, and renders a marker per listing. Clicking a marker opens the LBC listing URL in a new tab. Listings without lat/lng are silently skipped.

### Scope

**In Scope:**
- New Flask route `GET /map` → renders `templates/map.html`
- "Voir sur carte" button in `index.html` filter bar → serializes filter state → navigates to `/map?<params>`
- `map.html`: fetches `/api/annonces`, applies filter logic mirroring `getFiltered()` from URL params, renders Leaflet.js map with markers
- Baseline exclusion always applied: `status === 'deleted'` and `nogo === 1` listings are never shown
- Listings with `lat === null` or `lng === null` are skipped (no marker)
- Marker click → `window.open(annonce.lien, '_blank')`

**Out of Scope:**
- New API endpoint (reuse existing `/api/annonces`)
- Marker color coding
- Marker clustering
- Sidebar or detail panel in map view
- Bi-directional sync between table and map

## Context for Development

### Codebase Patterns

- Flask app in `web.py`, single `DB_NAME = "lbc_data.db"`, page routes use `render_template(...)`, data routes use `jsonify(...)`
- All frontend: vanilla JS, no framework, no bundler — single `templates/index.html`
- Filter logic in `getFiltered()` (line 571) reads 14 DOM values: checkboxes (`hideNogo`, `hideDeleted`), number inputs (`fPrixMin`, `fPrixMax`, `fSurfMin`, `fSurfMax`, `fPm2Min`, `fPm2Max`, `fNoteMin`), text input (`fTrajetMax`), selects (`fViabilise`, `fConstruct`, `fAgricole`, `fStatus`)
- `parseBoolFilter(id)` and `matchBool(filterVal, colVal)` helpers used for select-based boolean filters
- `trajetToMin(str)` helper converts trajet string (e.g. "1h 30") to minutes — must be duplicated in `map.html` (no bundler/shared module)
- `/api/annonces` already returns `lat`, `lng`, `nogo`, `status`, `lien`, `titre`, `prix`, `superficie`, `prix_m2`, `trajet`
- Test pattern: `pytest`, fixture uses `web.app.test_client()` + `monkeypatch.setattr(web, "DB_NAME", db_path)`

### Files to Reference

| File | Purpose |
| ---- | ------- |
| [web.py](web.py) | Flask routes — add `GET /map` route here (line ~275, before `/plu`) |
| [templates/index.html](templates/index.html) | Main UI — add "Voir sur carte" button in filter bar (line ~406) + filter serializer |
| [tests/test_web_api.py](tests/test_web_api.py) | Test pattern to follow for new `/map` route test |

### Technical Decisions

- Leaflet.js loaded via CDN (consistent with no-bundler approach)
- Filter state serialized via `URLSearchParams` in `index.html` → passed as query string to `/map`
- `map.html` reads `URLSearchParams` on load, fetches `/api/annonces`, applies mirror of `getFiltered()` logic, renders markers
- `trajetToMin()` duplicated in `map.html` (no shared module mechanism)
- Map auto-fits bounds to all visible markers via `group.getBounds()` where `group` is the `L.featureGroup()` containing all markers
- Annonces with `lat === null` or `lng === null` silently skipped (no UI warning)
- Zero-results state: show centered text "Aucune annonce à afficher sur la carte"
- **F1 fix**: `parseBoolFilter` in `map.html` is NOT a copy of the `index.html` version (which reads from DOM). It must be rewritten as `parseBoolFilter(strVal)` accepting a string value directly (from `URLSearchParams.get()`): returns `null` if `strVal` is falsy, `"null"` if `strVal === "null"`, else `parseInt(strVal)` (0 or 1)
- **F2 fix**: Boolean filter type coercion — URL params are always strings, but JSON annonce fields (`nogo`, `viabilise`, `partiellement_constructible`, `partiellement_agricole`) are integers. `matchBool` receives the output of `parseBoolFilter(strVal)` which already returns `null`, `"null"`, or integer (0/1) — ensuring `matchBool`'s strict equality `colVal === filterVal` compares integer to integer correctly. Never pass the raw string from `URLSearchParams` directly to `matchBool`.

## Implementation Plan

### Tasks

- [x] Task 1: Add `GET /map` Flask route
  - File: `web.py`
  - Action: Insert before the `/plu` route (around line 275):
    ```python
    @app.route("/map")
    def map_view():
        return render_template("map.html")
    ```
  - Notes: No server-side query param processing needed — all filtering is client-side JS

- [x] Task 2: Create `templates/map.html`
  - File: `templates/map.html` (new file)
  - Action: Create a full-page Leaflet.js map template with:
    1. **Head**: Leaflet CSS CDN + Leaflet JS CDN + inline styles (full-viewport map, minimal header)
    2. **Body**: `<div id="map">` (100vh minus header), header with "← Annonces" link back to `/` and a marker count badge
    3. **Script**:
       - On `DOMContentLoaded`: read all filter params from `URLSearchParams` into local variables
       - Fetch `GET /api/annonces`
       - Define `trajetToMin(str)` — duplicate from `index.html`
       - Define `matchBool(filterVal, colVal)` — duplicate from `index.html` (unchanged: `null`→pass, `"null"`→colVal==null, else strict ===)
       - Define `parseBoolFilter(strVal)` — **ADAPTED** (not copied from `index.html`):
         ```js
         function parseBoolFilter(strVal) {
           if (!strVal) return null;          // absent param → no filter
           if (strVal === "null") return "null"; // "?" option
           return parseInt(strVal);            // "0" or "1" → integer
         }
         ```
         This ensures `matchBool` always receives `null | "null" | 0 | 1` (never a raw string), so `colVal === filterVal` compares integer to integer correctly.
       - Read boolean select params via adapted helper:
         ```js
         const fViab  = parseBoolFilter(params.get('fViabilise'));
         const fConst = parseBoolFilter(params.get('fConstruct'));
         const fAgri  = parseBoolFilter(params.get('fAgricole'));
         ```
       - Apply filter logic mirroring `getFiltered()` — `hideNogo` and `hideDeleted` applied only if URL param is `"1"` (not always-on baseline), then apply remaining 12 filter fields from URL params
       - For each passing annonce where `lat != null && lng != null`: add `L.marker([lat, lng])` to `group` (a `L.featureGroup()`), bind popup `titre + '<br>' + prix + ' €'`, and on click `window.open(lien, '_blank')`
       - After all markers: if `group.getLayers().length > 0` call `map.fitBounds(group.getBounds())`, else show "Aucune annonce à afficher sur la carte" overlay
       - Update counter badge: `group.getLayers().length + ' annonces affichées'`
  - Notes: Single `group = L.featureGroup().addTo(map)` — add all markers to it, use `group.getLayers().length` (not a separate array) for count and bounds check. Map initial center `[46.6, 2.3]` (France) zoom 6 as fallback if no markers.

- [x] Task 3: Add "Voir sur carte" button in `index.html`
  - File: `templates/index.html`
  - Action: Insert after `<button id="resetFilters">Réinitialiser</button>` (line 406):
    ```html
    <button id="btnMap" onclick="goToMap()">🗺 Carte</button>
    ```
    Add `goToMap()` JS function in the `<script>` block:
    ```js
    function goToMap() {
      const params = new URLSearchParams();
      if (document.getElementById('hideNogo').checked)    params.set('hideNogo', '1');
      if (document.getElementById('hideDeleted').checked) params.set('hideDeleted', '1');
      ['fPrixMin','fPrixMax','fSurfMin','fSurfMax','fPm2Min','fPm2Max',
       'fTrajetMax','fNoteMin','fViabilise','fConstruct','fAgricole','fStatus'
      ].forEach(id => {
        const v = document.getElementById(id).value;
        if (v) params.set(id, v);
      });
      window.location.href = '/map?' + params.toString();
    }
    ```
  - Notes: Style `#btnMap` same as `#resetFilters` (background `#f1f5f9`, border `1px solid #cbd5e1`, border-radius `4px`)

- [x] Task 4: Add test for `GET /map`
  - File: `tests/test_web_api.py`
  - Action: Append test function:
    ```python
    def test_map_route_returns_200(client):
        """GET /map returns 200 HTML page."""
        c, _ = client
        response = c.get("/map")
        assert response.status_code == 200
        assert b"map" in response.data.lower()
    ```
  - Notes: Uses the existing `client` fixture — no new setup needed

### Acceptance Criteria

- [x] AC1: Given the app is running, when `GET /map` is requested, then it returns HTTP 200 with HTML content containing a Leaflet map container
- [x] AC2: Given listings with `status='deleted'` or `nogo=1` exist in the DB, when the map page loads with no filter params, then those listings are never shown as markers (baseline exclusion always active)
- [x] AC3: Given listings with `lat=null` or `lng=null`, when the map page loads, then those listings are silently skipped — no JS error, no marker, no UI warning
- [x] AC4: Given filters are set in `index.html` (e.g. `fPrixMax=100000`), when user clicks "Voir sur carte" (🗺 Carte button), then the browser navigates to `/map?fPrixMax=100000` and the map only renders markers for annonces with `prix ≤ 100000`
- [x] AC5: Given a marker is visible on the map, when the user clicks it, then `window.open(annonce.lien, '_blank')` is called, opening the LBC listing in a new tab
- [x] AC6: Given no annonces match the applied filters (or none have coordinates), when the map renders, then a visible overlay message "Aucune annonce à afficher sur la carte" is displayed and no markers appear
- [x] AC7: Given N ≥ 1 markers are rendered, when rendering completes, then `map.fitBounds()` is called so all markers are visible without manual zoom, and a badge shows "N annonces affichées"

## Additional Context

### Dependencies

- Leaflet.js v1.9.x via CDN (no install required):
  - CSS: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.css`
  - JS: `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`

### Testing Strategy

- **Automated**: Add `test_map_route_returns_200` to `tests/test_web_api.py` (Task 4)
- **Manual**:
  1. Start Flask (`python web.py`), navigate to `http://localhost:5000`
  2. Set filter (e.g. Prix max = 200 000), click "🗺 Carte"
  3. Verify URL is `/map?fPrixMax=200000`, verify only matching annonces appear as markers
  4. Click a marker → verify LBC link opens in new tab
  5. Reset all filters in main page, click Carte → verify all non-nogo/non-deleted annonces with coords appear
  6. Apply filter matching zero annonces → verify "Aucune annonce" message

## Review Notes

- Adversarial review completed
- Findings: 12 total, 7 fixed, 5 skipped (noise/out-of-scope)
- Resolution approach: auto-fix
- Fixed: F1 dead code, F2 numeric coercion, F3 CSS layout, F5 z-index comment, F6 sync warning, F8 array validation, F12 pluralization

### Notes

- **Risk**: `trajetToMin()` duplication — if the function changes in `index.html` in the future, `map.html` must be updated manually. Accept for now (no bundler).
- **Known limitation**: Map shows state at page load time. If annonces change while map is open, refresh needed.
- **Future consideration** (out of scope): Add a filter sidebar directly on the map page to avoid needing to go back to the table to change filters.
