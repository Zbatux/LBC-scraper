---
title: 'Right-click to Mark as NoGo on Map'
slug: 'right-click-nogo-map'
created: '2026-04-13'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python/Flask', 'SQLite', 'Leaflet.js 1.9.4', 'Vanilla JS']
files_to_modify: ['templates/map.html']
code_patterns: ['Leaflet marker event listeners', 'PATCH /api/annonces/<id>']
test_patterns: ['tests/test_web_api.py - Flask test client']
---

# Tech-Spec: Right-click to Mark as NoGo on Map

**Created:** 2026-04-13

## Overview

### Problem Statement

Users cannot mark an ad as NoGo directly from the map view. They must navigate back to the list (`index.html`) to do so, which breaks the map workflow when reviewing multiple listings geographically.

### Solution

Add a `contextmenu` (right-click) event listener to each Leaflet marker in `map.html`. On right-click, display a lightweight inline context menu with a "Marquer NoGo" action that calls `PATCH /api/annonces/<id>` with `{"nogo": 1}`, then removes the marker from the map immediately on success.

### Scope

**In Scope:**
- Right-click on a map marker → context menu with "Marquer NoGo" option
- `PATCH /api/annonces/<id>` call with `{"nogo": 1}`
- Immediate removal of the marker from the Leaflet feature group on success
- Update of the displayed count badge after removal
- Context menu dismissal on outside click or Escape key

**Out of Scope:**
- Undo/un-NoGo from the map
- Showing NoGo ads in a different color on the map
- NoGo marking from `index.html` (list view)
- Multi-select NoGo

---

## Context for Development

### Codebase Patterns

- **No bundler**: All JS is inline in HTML templates. No `import`/`export`, no modules.
- **Leaflet marker events**: Existing pattern at `map.html:142` — `marker.on('click', () => { if (a.lien) window.open(a.lien, '_blank'); })`. The new `contextmenu` listener follows the exact same pattern.
- **Leaflet event object**: `e.originalEvent` gives access to the native DOM event (for `clientX`/`clientY` and `preventDefault()`).
- **NoGo filtering**: `map.html:114` — `if (a.nogo === 1) return;` already excludes NoGo ads at load time. After marking, removing the layer is sufficient — no page reload needed.
- **API call pattern**: `map.html` has no existing PATCH calls. Use native `fetch` with `method: 'PATCH'`, `Content-Type: application/json`, `body: JSON.stringify({nogo: 1})`. The endpoint is at `web.py:244`.
- **Context menu pattern**: No existing context menu in the project. A single `<div id="ctx-menu">` appended once to `<body>`, repositioned via `style.left/top` on each right-click, is consistent with the no-framework approach.
- **Badge update**: Badge text is set at `map.html:148` via `document.getElementById('badge').textContent`. Must be recalculated after layer removal using `group.getLayers().length`.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `templates/map.html` | Only file to modify — entire map UI and JS inline |
| `web.py:244-280` | `PATCH /api/annonces/<id>` — validates and updates `nogo` field |
| `web.py:29` | `EDITABLE_FIELDS` — confirms `nogo` is editable |
| `tests/test_web_api.py` | Existing test patterns for Flask test client |

### Technical Decisions

- **Single context menu DOM node**: Created once, reused per right-click (not per marker). Avoids memory leak from creating N menu elements.
- **`position: fixed`**: Uses `clientX/clientY` from the native event — works regardless of page scroll.
- **Prevent default**: `e.originalEvent.preventDefault()` suppresses the browser's native context menu.
- **Dismiss handlers attached once**: `document.addEventListener('click', hideMenu)` and `keydown` Escape listener added once at init, not per right-click.
- **Error handling**: On non-200 PATCH response, log to `console.error` and close menu — marker stays on map.
- **Badge count**: Integer is decremented by re-reading `group.getLayers().length` (not by parsing the text string).

---

## Implementation Plan

### Tasks

- [x] Task 1: Add context menu HTML element to `map.html`
  - File: `templates/map.html`
  - Action: Insert the following `<div>` immediately before the closing `</body>` tag (before the existing `<script>` block):
    ```html
    <div id="ctx-menu" style="display:none; position:fixed; z-index:9999; background:#fff; border:1px solid #cbd5e1; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.15); padding:4px 0; min-width:160px;">
      <button id="ctx-nogo" style="display:block; width:100%; padding:8px 16px; background:none; border:none; text-align:left; cursor:pointer; font-size:14px; color:#dc2626;">🚫 Marquer NoGo</button>
    </div>
    ```
  - Notes: `z-index:9999` ensures it renders above all Leaflet layers (max z-index ~600).

- [x] Task 2: Add context menu JS helpers inside the `<script>` block, at the top of the `DOMContentLoaded` callback (before `const map = L.map(...)`)
  - File: `templates/map.html`
  - Action: Insert the following block:
    ```js
    const ctxMenu = document.getElementById('ctx-menu');
    let _ctxCallback = null;
    function showMenu(x, y, cb) {
      _ctxCallback = cb;
      ctxMenu.style.left = x + 'px';
      ctxMenu.style.top  = y + 'px';
      ctxMenu.style.display = 'block';
    }
    function hideMenu() {
      ctxMenu.style.display = 'none';
      _ctxCallback = null;
    }
    document.getElementById('ctx-nogo').addEventListener('click', () => {
      const cb = _ctxCallback;
      hideMenu();
      if (cb) cb();
    });
    document.addEventListener('click', e => {
      if (!ctxMenu.contains(e.target)) hideMenu();
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') hideMenu(); });
    ```
  - Notes: The `click` dismiss guard (`!ctxMenu.contains(e.target)`) prevents the menu from closing when the user clicks the "Marquer NoGo" button itself (the button's own click handler fires first, then the document click fires — but by then `hideMenu()` already ran, so it's a no-op).

- [x] Task 3: Add `contextmenu` listener to each marker inside `data.forEach`
  - File: `templates/map.html`
  - Action: Immediately after the existing line `marker.on('click', () => { if (a.lien) window.open(a.lien, '_blank'); });` (currently at line 142), add:
    ```js
    marker.on('contextmenu', e => {
      e.originalEvent.preventDefault();
      showMenu(e.originalEvent.clientX, e.originalEvent.clientY, async () => {
        try {
          const res = await fetch(`/api/annonces/${a.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nogo: 1 })
          });
          if (res.ok) {
            group.removeLayer(marker);
            const remaining = group.getLayers().length;
            document.getElementById('badge').textContent =
              remaining + (remaining !== 1 ? ' annonces affichées' : ' annonce affichée');
          } else {
            console.error('NoGo PATCH failed:', res.status);
          }
        } catch (err) {
          console.error('NoGo PATCH error:', err);
        }
      });
    });
    ```
  - Notes: `a.id` is available in the closure — confirmed present in `/api/annonces` response (`web.py:123`). `e.originalEvent` is the native MouseEvent; Leaflet wraps it.

- [x] Task 4: Verify PATCH `{nogo: 1}` test coverage in `tests/test_web_api.py`
  - File: `tests/test_web_api.py`
  - Action: Search for existing test covering `PATCH /api/annonces/<id>` with `nogo`. If absent, add:
    ```python
    def test_patch_nogo(client, seeded_db):
        res = client.patch('/api/annonces/1', json={'nogo': 1})
        assert res.status_code == 200
        conn = sqlite3.connect(seeded_db)
        row = conn.execute('SELECT nogo FROM annonces WHERE id=1').fetchone()
        assert row[0] == 1
    ```
  - Notes: Follow the fixture pattern already used in the file.

### Acceptance Criteria

- [ ] AC1 — Right-click suppresses browser menu and shows custom menu
  - Given: the map is loaded with at least one visible marker
  - When: the user right-clicks on a marker
  - Then: the browser's native context menu does not appear; the custom `#ctx-menu` div becomes visible near the cursor; it contains the "Marquer NoGo" button

- [ ] AC2 — Clicking "Marquer NoGo" calls the API and removes the marker
  - Given: the custom context menu is open for marker with id `X`
  - When: the user clicks "Marquer NoGo"
  - Then: `PATCH /api/annonces/X` is called with body `{"nogo": 1}`; on HTTP 200, the marker disappears from the map; the badge count decrements by 1

- [ ] AC3 — Menu dismisses on outside click
  - Given: the custom context menu is visible
  - When: the user clicks anywhere outside the `#ctx-menu` element
  - Then: the menu closes; no API call is made

- [ ] AC4 — Menu dismisses on Escape
  - Given: the custom context menu is visible
  - When: the user presses the Escape key
  - Then: the menu closes; no API call is made

- [ ] AC5 — API failure leaves marker intact
  - Given: the custom context menu is open
  - When: the user clicks "Marquer NoGo" and the PATCH returns a non-200 response
  - Then: the marker remains on the map; the badge count is unchanged; an error is logged to `console.error`

- [ ] AC6 — Marked ad does not reappear on page reload
  - Given: a marker was successfully marked as NoGo in this session
  - When: the user reloads the map page
  - Then: that marker is not displayed (filtered by `if (a.nogo === 1) return;` at load time)

---

## Additional Context

### Dependencies

- Leaflet.js 1.9.4 — already loaded, `e.originalEvent` available on all Leaflet pointer events
- `PATCH /api/annonces/<id>` — already implemented in `web.py:244`, `nogo` already in `EDITABLE_FIELDS`
- `a.id` — already present in `/api/annonces` JSON response (`web.py:123`)
- No new libraries or backend changes required

### Testing Strategy

- **Manual (golden path)**: Load map → right-click marker → click "Marquer NoGo" → verify marker removed, badge decremented, reload page → verify marker absent
- **Manual (edge cases)**: Right-click → press Escape (menu closes, no call); right-click → click outside (same); simulate network error (DevTools offline → button → marker stays)
- **Unit/integration**: `tests/test_web_api.py` — verify PATCH `{nogo: 1}` sets DB column correctly (Task 4)

## Review Notes

- Adversarial review completed
- Findings: 10 total, 0 fixed, 10 skipped (user chose Skip)
- Resolution approach: skip

---

### Notes

- **Risk — click event order**: The `document.addEventListener('click', hideMenu)` fires after the button's own click. Since `hideMenu()` nulls `_ctxCallback` after extracting it, there is no double-fire risk.
- **Risk — menu off-screen**: If the user right-clicks near the bottom/right edge, the menu may clip outside the viewport. Not handled in this spec (out of scope for this iteration).
- **Future**: Could add "Voir l'annonce" as a second menu item to replace the current left-click behaviour, giving both actions from one right-click menu.
