---
title: 'Comparison Modal UX Improvements'
slug: 'comparison-modal-ux-improvements'
created: '2026-03-12'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['HTML/CSS', 'Vanilla JavaScript']
files_to_modify: ['templates/index.html']
code_patterns: ['single-file frontend', 'dynamic HTML via string concatenation', 'existing sort pattern (sortCol/sortDir) for main table']
test_patterns: ['no frontend tests — backend tests only via pytest in tests/']
---

# Tech-Spec: Comparison Modal UX Improvements

**Created:** 2026-03-12

## Overview

### Problem Statement

The comparison modal has two UX issues:
1. Table header text has poor contrast — dark text on light gray (`#f1f5f9`) background is hard to read.
2. The comparison table has no sorting capability, making it difficult to analyze and compare listings.

### Solution

1. Restyle table headers with a high-contrast dark background and white text.
2. Add click-to-sort functionality on all table columns with a visual sort direction indicator.

### Scope

**In Scope:**
- Improve header contrast (dark background, white text)
- Add click-to-sort on all 6 columns (Titre, Prix €, Superficie m², €/m², Trajet, Distance)
- Sort direction indicator arrow on active column
- Preserve existing best/worst highlighting after sort

**Out of Scope:**
- Multi-column sort
- Persistent sort preference
- Changes to the backend API
- Changes to the comparison matching logic

## Context for Development

### Codebase Patterns

- Single-file frontend: all HTML, CSS, and JS live in `templates/index.html`
- No JS framework — vanilla JavaScript with inline `<script>` and `<style>` blocks
- Table is built dynamically via JS string concatenation in the compare modal open handler
- Main table already uses `sortCol`/`sortDir` pattern (line 425-426) — compare sort should follow same convention
- Data comes from `/api/annonces/<id>/similar` returning `{ target, similar, summary }`

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `templates/index.html:276-281` | Current `.cmp-table th` CSS styles (contrast fix) |
| `templates/index.html:784-815` | JS that builds comparison table HTML (sort + re-render) |
| `templates/index.html:740-760` | `openCompare()` — fetches data, stores in local vars |
| `templates/index.html:411-420` | Compare modal HTML structure |
| `templates/index.html:425-426` | Main table sort pattern to follow |

### Technical Decisions

- Pure CSS/JS solution — no external libraries for sorting
- Sort is client-side only (data already in memory from API response)
- Store `similar` and `summary` data in module-level vars for re-sort without re-fetch
- Numeric sort for Prix, Superficie, €/m², Distance; alphabetic sort for Titre, Trajet
- Null values sort to the end regardless of direction

## Implementation Plan

### Tasks

- [x] Task 1: Fix table header contrast
  - File: `templates/index.html` (CSS block, `.cmp-table th` rule ~line 276)
  - Action: Change `background: #f1f5f9` to `background: #334155` (slate-700) and add `color: #ffffff`
  - Notes: Keep all other th properties (padding, font-size, font-weight, text-transform, letter-spacing, white-space). Change `border-bottom` to `2px solid #475569` to match the darker scheme.

- [x] Task 2: Add sortable header cursor and hover styles
  - File: `templates/index.html` (CSS block, after `.cmp-table th` rule)
  - Action: Add `cursor: pointer` to `.cmp-table th` rule. Add new rule `.cmp-table th:hover { background: #475569; }` for hover feedback. Add `.cmp-sort-arrow` style for the sort indicator arrow (inline, margin-left 4px, font-size 10px).

- [x] Task 3: Add module-level state variables for compare sort
  - File: `templates/index.html` (JS block, near existing `sortCol`/`sortDir` declarations ~line 425)
  - Action: Add three new module-level variables:
    ```js
    let cmpSortCol = null;
    let cmpSortDir = 1;
    let cmpData = null; // stores { target, similar, summary } from last API call
    ```

- [x] Task 4: Store API response data for re-sort
  - File: `templates/index.html` (JS block, in `openCompare()` ~line 748)
  - Action: After `const { target, similar, summary } = data;`, add `cmpData = data;`. Reset sort state: `cmpSortCol = null; cmpSortDir = 1;`.

- [x] Task 5: Extract table rendering into a dedicated function
  - File: `templates/index.html` (JS block, after `openCompare()`)
  - Action: Create a new function `renderCmpTable(similar, summary)` that contains the existing table-building logic (lines 784-814: highlighting logic, thead, tbody loop). This function:
    1. Builds `<thead>` with `<th>` elements. Each `<th>` gets an `onclick="sortCmpTable('colKey')"` attribute. The active sort column's `<th>` appends a sort arrow span (`▲` or `▼`).
    2. Builds `<tbody>` rows exactly as current code does (preserving `cmp-best`, `cmp-worst`, `nogo-row` classes).
    3. Returns the HTML string for the table only (not target card or stats bar).
  - Notes: Column keys mapping: `titre` (string), `prix` (number), `superficie` (number), `prix_m2` (number), `trajet` (string), `distance_m` (number).

- [x] Task 6: Refactor `openCompare()` to use `renderCmpTable()`
  - File: `templates/index.html` (JS block, in `openCompare()`)
  - Action: Replace the inline table-building code (lines 784-814) with a call to `renderCmpTable(similar, summary)`. The target card and stats bar HTML remain in `openCompare()`. Concatenate: `html += renderCmpTable(similar, summary);`

- [x] Task 7: Implement `sortCmpTable()` function
  - File: `templates/index.html` (JS block, after `renderCmpTable()`)
  - Action: Create function `sortCmpTable(colKey)`:
    1. Toggle direction: if `cmpSortCol === colKey`, flip `cmpSortDir *= -1`; else set `cmpSortCol = colKey; cmpSortDir = 1`.
    2. Sort `cmpData.similar` array in-place:
       - For string columns (`titre`, `trajet`): locale-aware compare with `localeCompare()`. Nulls/empty sort to end.
       - For number columns (`prix`, `superficie`, `prix_m2`, `distance_m`): numeric compare. Nulls sort to end.
       - Apply `cmpSortDir` multiplier.
    3. Re-render only the table: find the existing `<table class="cmp-table">` in `#cmpBody` and replace its `outerHTML` with `renderCmpTable(cmpData.similar, cmpData.summary)`.

- [x] Task 8: Clear compare state on modal close
  - File: `templates/index.html` (JS block, in `closeCompareModal()` ~line 818)
  - Action: Add `cmpData = null; cmpSortCol = null; cmpSortDir = 1;` to reset state when modal closes.

### Acceptance Criteria

- [ ] AC 1: Given the comparison modal is open, when looking at the table headers, then the headers have a dark background (`#334155`) with white text, providing clear readable contrast.
- [ ] AC 2: Given the comparison modal is open, when hovering over a table header, then the header background changes slightly (`#475569`) and the cursor is a pointer, indicating clickability.
- [ ] AC 3: Given the comparison modal is open with multiple similar listings, when clicking the "Prix €" header, then the table rows are sorted by price ascending, and a ▲ arrow appears next to "Prix €".
- [ ] AC 4: Given the table is sorted by "Prix €" ascending, when clicking "Prix €" again, then the sort reverses to descending and the arrow changes to ▼.
- [ ] AC 5: Given the table is sorted by "Prix €", when clicking a different header like "Distance", then the table sorts by distance ascending, the arrow moves to "Distance", and "Prix €" no longer shows an arrow.
- [ ] AC 6: Given a listing has the best (lowest) €/m² price, when the table is re-sorted by any column, then the green left border (`cmp-best`) is still applied to that row.
- [ ] AC 7: Given a listing has the worst (highest) €/m² price, when the table is re-sorted by any column, then the red left border (`cmp-worst`) is still applied to that row.
- [ ] AC 8: Given a listing has a null price value, when sorting by "Prix €", then that listing appears at the bottom of the list regardless of sort direction.
- [ ] AC 9: Given the comparison modal is closed and reopened for a different listing, when viewing the table, then no previous sort is applied (default order by distance).

## Additional Context

### Dependencies

None — self-contained CSS + JS changes in a single file.

### Testing Strategy

- **Manual testing** (no frontend test framework in place):
  1. Open comparison modal for a listing with multiple similar results
  2. Verify header contrast is visually readable (dark bg, white text)
  3. Click each column header and verify sort order toggles correctly
  4. Verify sort arrow appears on active column only
  5. Verify best/worst highlighting persists across sorts
  6. Verify listings with null values sink to bottom when sorting
  7. Close and reopen modal — verify sort resets
  8. Test with a listing that has 0 similar results — verify no errors

### Notes

- The existing `sortCol`/`sortDir` variables are for the main listings table and must not be confused with `cmpSortCol`/`cmpSortDir`.

## Review Notes

- Adversarial review completed
- Findings: 13 total, 8 fixed, 5 skipped (noise or deliberate choices)
- Resolution approach: auto-fix
- Fixed: F1 (mutation), F2 (trajet sort), F4 (unused type field), F6 (outerHTML), F7 (keyboard a11y), F8 (aria-sort), F10 (class strings)
- Skipped: F3 (float equality — pre-existing pattern), F5 (nulls at bottom — deliberate), F9 (race condition — unlikely), F11/F12 (noise), F13 (UX preference)
