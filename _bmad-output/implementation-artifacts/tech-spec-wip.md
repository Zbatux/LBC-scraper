---
title: 'Terrain À Visiter Flag'
slug: 'terrain-a-visiter-flag'
created: '2026-04-16'
status: 'review'
stepsCompleted: [1, 2, 3]
tech_stack: ['Python 3/Flask', 'SQLite3', 'Vanilla JS (ES2017+)', 'Jinja2 HTML templates', 'pytest']
files_to_modify: ['database.py', 'web.py', 'templates/index.html']
code_patterns: ['ALTER TABLE idempotent migration (try/except OperationalError)', 'EDITABLE_FIELDS whitelist auto-validates booleans', 'optimistic UI toggle', 'localStorage filter persistence saveFilters/loadFilters', 'class-based event delegation in bindRowEvents()']
test_patterns: ['pytest + tmp_path + monkeypatch.setattr(web, DB_NAME)', 'database.save_or_merge() to seed test DB']
---

# Tech-Spec: Terrain À Visiter Flag

**Created:** 2026-04-16

## Overview

### Problem Statement

No way to mark a terrain for physical visit. Users must rely on mental notes or external tools to track which listings they want to visit in person.

### Solution

Add a boolean column `a_visiter` (INTEGER DEFAULT 0) to the `annonces` table. Surface it as a clickable star icon (☆/★) in the main table — click toggles on/off instantly via PATCH API. Add a checkbox filter "À visiter seulement" that hides non-flagged rows, persisted to localStorage. Add `a_visiter` to the bulk-toggle toolbar.

### Scope

**In Scope:**
- New DB column `a_visiter INTEGER DEFAULT 0`
- Migration in `web.py:ensure_columns()` and `database.py:ensure_columns()` + `init_db()`
- `a_visiter` added to `EDITABLE_FIELDS` whitelist in `web.py`
- `a_visiter` included in `GET /api/annonces` SELECT
- Star column in `<thead>` (sortable, `data-col="a_visiter"`)
- Star cell in row render: ★ (yellow) when 1, ☆ (grey) when 0/null
- Click-to-toggle on star cell via PATCH `/api/annonces/<id>` — no confirmation
- Checkbox filter "À visiter seulement" in filters bar — hides rows where `a_visiter != 1`
- Filter persisted in localStorage (`saveFilters` / `loadFilters`)
- `a_visiter` added to bulk-toggle toolbar group
- `resetFilters` resets the new checkbox

**Out of Scope:**
- map.html integration
- Notifications / reminders
- Export / calendar integration
- Confirmation dialogs

## Context for Development

### Codebase Patterns

1. **DB migration pattern — 3 locations** — `ALTER TABLE` migrations exist in THREE places, each wrapped in `try/except sqlite3.OperationalError`. Must add `a_visiter` in all three:
   - `database.py:save_to_database()` — `migrations` list ~line 99
   - `database.py:save_or_merge()` — `migrations` list ~line 203
   - `web.py:ensure_columns()` — inline try-loop ~line 50
   The CREATE TABLE statements in `save_to_database` and `save_or_merge` only contain base columns; `a_visiter` does NOT need to go in the CREATE TABLE block (migrations handle it).

2. **EDITABLE_FIELDS whitelist + auto boolean validation** — `web.py:29`. Adding `"a_visiter"` here unlocks both PATCH endpoints. Bonus: line 264 `for bool_field in EDITABLE_FIELDS - {"note", "commentaire"}` auto-validates `a_visiter` as 0/1/None — no extra validation code needed.

3. **GET /api/annonces SELECT** — `web.py:122-128` — Explicit column list; must append `a.a_visiter`.

4. **Bulk PATCH** — `web.py:214-241` — Generic; handles any EDITABLE_FIELDS field. Line 228 checks `value not in (0, 1)` — correct for `a_visiter`. No changes needed beyond the whitelist.

5. **Inline toggle pattern** — `nogo-cell` (line ~654) uses `badge()`. Star cell uses `★`/`☆` emoji with CSS classes, same click→PATCH flow as `note-cell`. Optimistic update: mutate `allData` entry directly, re-render only if `showAVisiter` filter is active (to avoid hiding the row mid-interaction).

6. **Filter persistence** — `saveFilters()` line 675 saves state to `localStorage.setItem("lbc_filters", ...)`. `loadFilters()` line 698 restores via `setChk()`. `resetFilters` at line 1248 calls `localStorage.removeItem("lbc_filters")` + page reload — no manual reset code needed.

7. **Bulk-toggle toolbar** — `index.html:419-424` — `<input type="checkbox" class="toggle-col" value="<field>" />`. JS reads all `.toggle-col` checked values automatically — adding the label is the only change required.

8. **Test pattern** — `tests/test_web_api.py` uses `pytest`, `tmp_path`, `monkeypatch.setattr(web, "DB_NAME", db_path)`, seeds with `database.save_or_merge([...], db_name=db_path)`. Direct pattern to replicate for new tests.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `web.py` | EDITABLE_FIELDS, ensure_columns(), GET /api/annonces SELECT |
| `database.py` | ensure_columns() + init_db() migrations |
| `templates/index.html` | filters bar, thead, row render, saveFilters, loadFilters, bindRowEvents, toolbar |
| `tests/test_web_api.py` | Existing API test patterns to extend |

### Technical Decisions

- Column name: `a_visiter` (snake_case, consistent with `analyse_faite`, `partiellement_constructible`)
- Star render: use HTML entities `★` (U+2605) / `☆` (U+2606), styled yellow via CSS class `star-on`
- Cell class: `avisiter-cell` with `data-id="${a.id}"` — mirrors `nogo-cell` / `note-cell` pattern
- Toggle: optimistic UI update (flip star immediately, revert on API error) — same as note-cell pattern
- Filter: checkbox `id="showAVisiter"`, label "À visiter seulement" — simple boolean, no select needed

## Implementation Plan

### Tasks

**T1 — database.py: add migration (2 locations)**
- File: `database.py`
- In `save_to_database()` `migrations` list (~line 113): append `"ALTER TABLE annonces ADD COLUMN a_visiter INTEGER DEFAULT 0"`
- In `save_or_merge()` `migrations` list (~line 218): append `"ALTER TABLE annonces ADD COLUMN a_visiter INTEGER DEFAULT 0"`
- Do NOT modify the CREATE TABLE blocks — migrations handle it

**T2 — web.py: migration + whitelist + SELECT**
- File: `web.py`
- `ensure_columns()` line ~51: add `"ALTER TABLE annonces ADD COLUMN a_visiter INTEGER DEFAULT 0"` to the try-loop
- `EDITABLE_FIELDS` line 29: add `"a_visiter"` to the set
- `get_annonces()` SELECT line ~125: append `a.a_visiter,` to the selected columns string

**T3 — index.html: CSS for star**
- File: `templates/index.html`
- In `<style>` block, add:
  ```css
  .avisiter-cell { text-align: center; cursor: pointer; min-width: 32px; }
  .star-on  { color: #f59e0b; font-size: 18px; }
  .star-off { color: #94a3b8; font-size: 18px; }
  ```

**T4 — index.html: thead column**
- File: `templates/index.html`
- In `<thead><tr>`, after `<th class="sortable" data-col="nogo">Nogo</th>` (line ~449), add:
  ```html
  <th class="sortable" data-col="a_visiter">★</th>
  ```

**T5 — index.html: row render**
- File: `templates/index.html`
- In the `tr.innerHTML` template (line ~639), after `<td class="nogo-cell">${badge(a.nogo)}</td>` (line ~654), add:
  ```js
  <td class="avisiter-cell" data-id="${a.id}"><span class="${a.a_visiter === 1 ? 'star-on' : 'star-off'}">${a.a_visiter === 1 ? '★' : '☆'}</span></td>
  ```

**T6 — index.html: bindRowEvents — star click toggle**
- File: `templates/index.html`
- In `bindRowEvents()` (after line ~809), add:
  ```js
  document.querySelectorAll(".avisiter-cell").forEach(td => {
    td.addEventListener("click", async () => {
      const id = parseInt(td.dataset.id);
      const a = allData.find(x => x.id === id);
      if (!a) return;
      const newVal = a.a_visiter === 1 ? 0 : 1;
      const span = td.querySelector("span");
      // Optimistic update
      a.a_visiter = newVal;
      span.className = newVal === 1 ? 'star-on' : 'star-off';
      span.textContent = newVal === 1 ? '★' : '☆';
      try {
        const res = await fetch(`/api/annonces/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ a_visiter: newVal })
        });
        if (!res.ok) throw new Error();
      } catch {
        // Revert on error
        a.a_visiter = newVal === 1 ? 0 : 1;
        span.className = a.a_visiter === 1 ? 'star-on' : 'star-off';
        span.textContent = a.a_visiter === 1 ? '★' : '☆';
      }
      if (document.getElementById("showAVisiter").checked) render();
    });
  });
  ```

**T7 — index.html: filter bar**
- File: `templates/index.html`
- In `#filters` div (after `hideDeleted` label, line ~358), add before the first `<span class="filter-sep">`:
  ```html
  <label>
    <input type="checkbox" id="showAVisiter" />
    À visiter seulement
  </label>
  ```

**T8 — index.html: getFiltered()**
- File: `templates/index.html`
- In `getFiltered()` function (line ~575), add after `hideDeleted` read:
  ```js
  const showAVisiter = document.getElementById("showAVisiter").checked;
  ```
- In the `.filter()` body, add after the `hideDeleted` check:
  ```js
  if (showAVisiter && a.a_visiter !== 1) return false;
  ```

**T9 — index.html: saveFilters()**
- File: `templates/index.html`
- In `saveFilters()` state object (line ~677), add:
  ```js
  showAVisiter: document.getElementById("showAVisiter").checked,
  ```

**T10 — index.html: loadFilters()**
- File: `templates/index.html`
- In `loadFilters()` (line ~698), add after existing `setChk` calls:
  ```js
  setChk("showAVisiter", state.showAVisiter);
  ```

**T11 — index.html: bulk-toggle toolbar**
- File: `templates/index.html`
- In `#toggleGroup` (line ~419), add:
  ```html
  <label class="toggle-cb-label"><input type="checkbox" class="toggle-col" value="a_visiter" /> À visiter</label>
  ```

### Acceptance Criteria

**AC1 — DB column exists after app start**
- Given: fresh DB or existing DB without `a_visiter`
- When: Flask app starts (ensure_columns runs)
- Then: `PRAGMA table_info(annonces)` shows `a_visiter INTEGER DEFAULT 0`

**AC2 — GET /api/annonces returns a_visiter field**
- Given: at least one annonce in DB
- When: GET /api/annonces
- Then: each object in response JSON includes `"a_visiter"` key with value 0, 1, or null

**AC3 — PATCH toggles a_visiter**
- Given: annonce id=1 with a_visiter=0
- When: PATCH /api/annonces/1 with body `{"a_visiter": 1}`
- Then: response 200, DB row has a_visiter=1; subsequent GET returns a_visiter=1

**AC4 — Star renders correctly**
- Given: row with a_visiter=0 and row with a_visiter=1
- When: table renders
- Then: a_visiter=1 shows ★ in yellow (`.star-on`), a_visiter=0 shows ☆ in grey (`.star-off`)

**AC5 — Click toggles star immediately (optimistic UI)**
- Given: row with a_visiter=0
- When: user clicks star cell
- Then: star immediately changes to ★ yellow without page reload; PATCH is called; star stays on success

**AC6 — Click reverts on API error**
- Given: star toggled optimistically
- When: PATCH returns non-2xx
- Then: star reverts to previous state

**AC7 — Filter hides non-flagged rows**
- Given: mix of a_visiter=0 and a_visiter=1 rows
- When: "À visiter seulement" checkbox is checked
- Then: only rows with a_visiter=1 are visible

**AC8 — Filter persists across page reload**
- Given: "À visiter seulement" checked
- When: page reloads
- Then: checkbox remains checked and filter is active

**AC9 — Bulk toggle works for a_visiter**
- Given: 2 rows selected
- When: "À visiter" checked in toolbar, then "→ Oui" clicked
- Then: both rows' a_visiter set to 1 via bulk PATCH; stars update

**AC10 — resetFilters clears showAVisiter**
- Given: showAVisiter checked
- When: "Réinitialiser" button clicked
- Then: checkbox unchecked (page reloads fresh, localStorage cleared)

## Additional Context

### Dependencies

- No new npm packages or pip packages required
- Existing PATCH `/api/annonces/<id>` endpoint handles `a_visiter` once added to EDITABLE_FIELDS
- Existing bulk PATCH `/api/annonces/bulk` handles it too — the bulk endpoint reads `EDITABLE_FIELDS` whitelist

### Testing Strategy

- Extend `tests/test_web_api.py` with:
  - Test AC2: assert `a_visiter` key present in GET response
  - Test AC3: PATCH a_visiter=1, verify GET reflects change
  - Test AC3b: PATCH a_visiter with invalid value (e.g. 2) — should return 400 if validation added, or 200 if not (note: current code only validates `note` range; `a_visiter` is a boolean 0/1, no extra validation needed)

### Notes

- The `resetFilters` handler at line 1248 calls `localStorage.removeItem("lbc_filters")` and reloads — no manual reset code needed
- Ensure `a_visiter` is also added to `database.py:init_db()` CREATE TABLE block to keep fresh installs consistent with migrations
