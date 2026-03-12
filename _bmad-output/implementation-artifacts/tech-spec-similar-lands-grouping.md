---
title: 'Similar Lands Price Comparison Modal'
slug: 'similar-lands-grouping'
created: '2026-03-11'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3', 'Flask', 'SQLite3', 'Vanilla JS', 'Jinja2 templates']
files_to_modify: ['config.py', 'matcher.py', 'web.py', 'templates/index.html', 'tests/test_matcher.py', 'tests/test_web_api.py']
code_patterns: ['Pure functions in logic modules (no DB in matcher.py)', 'sqlite3.Row + dict conversion for JSON', 'Plain JSON arrays (no wrapper)', 'Additive-only migrations (idempotent)', 'Client-side filtering/sorting/rendering']
test_patterns: ['pytest', 'Temp DB per test (tempfile.mkstemp)', 'Bare top-level test functions (not classes)', 'unittest.mock.patch for side effects', 'Direct assertions on DB state']
---

# Tech-Spec: Similar Lands Price Comparison Modal

**Created:** 2026-03-11

## Overview

### Problem Statement

Each listing is displayed individually with no market context. Users cannot quickly assess whether a land plot is competitively priced compared to similar plots nearby.

### Solution

A **"Comparer" button** on each listing row (for listings with GPS coordinates) that opens a **modal** showing all similar listings within a 2 km radius and ±20% area tolerance. The modal displays a comparison table with prix, superficie, prix/m² and summary stats (median, min, max prix/m²).

This follows the same UX pattern as the existing history modal — click a button on a row, see contextual data in an overlay.

### Scope

**In Scope:**
- `find_similar()` function in `matcher.py` to find similar listings for a given target
- API endpoint `GET /api/annonces/<id>/similar` returning similar listings + summary stats
- Extend `GET /api/annonces` to include `lat` and `lng` in the response
- "Comparer" button on each row (only for listings with GPS)
- Comparison modal in `index.html` with table + stats
- Read-only

**Out of Scope:**
- Trajet-based comparison (users can already filter by trajet in the main table)
- Separate comparison page
- CSV export of comparisons
- Saving comparisons
- Cross-listing historical price comparison
- Sparklines / graphical visualizations

## Context for Development

### Codebase Patterns

- **Module separation:** Pure logic in `matcher.py` (no DB access), persistence in `database.py`, HTTP in `web.py`
- **API style:** Plain JSON arrays, errors as `{"error": "msg"}` with HTTP status codes
- **DB access:** `sqlite3.connect()` + `conn.row_factory = sqlite3.Row` + `dict(row)` for JSON serialization
- **Frontend:** Single-file HTML with inline `<style>` and `<script>`, vanilla JS, no framework
- **Config:** Constants in `config.py` (flat module, no class)
- **Existing haversine:** `matcher._haversine(lat1, lng1, lat2, lng2)` returns distance in metres — reusable internally by `find_similar()`. `web.py` must NEVER call `_haversine()` directly — only `matcher.find_similar()`.
- **Existing area comparison:** `abs(a1 - a2) / max(a1, a2)` pattern in `find_match()` with `max_area > 0` guard — reusable for area tolerance
- **Existing modal pattern:** History modal in `index.html` — same overlay/dialog/header/body structure, same close handlers (close button, overlay click, Escape key), `role="dialog"` + `aria-modal="true"` + `aria-label`
- **Existing history button pattern:** `.hist-btn` on each row with `data-id` — same approach for compare button
- **Existing test pattern:** `tests/test_web_api.py` uses **bare top-level test functions** (not test classes). New tests must follow this convention.
- **Import constraint:** `tests/test_matcher.py` line 197 enforces `matcher.py` imports ⊆ `{"math", "config"}`. `find_similar()` uses only these — no new imports needed. Verify this test still passes after changes.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `config.py` | Add `SIMILAR_GPS_RADIUS_M = 2000` and `SIMILAR_AREA_TOLERANCE_PCT = 0.20` |
| `matcher.py` | Reuse `_haversine()`, add `find_similar()` function |
| `web.py` | Extend `GET /api/annonces` query to include `lat`, `lng`. Add `GET /api/annonces/<id>/similar` endpoint. Add `import matcher` and `import statistics`. |
| `templates/index.html` | Add compare button per row, comparison modal, JS logic |
| `tests/test_matcher.py` | Add tests for `find_similar()` (bare functions, not class) |
| `tests/test_web_api.py` | Add tests for similar endpoint (bare functions, not class) |

### Technical Decisions

- **GPS-only comparison:** Only listings with valid `lat`, `lng`, and `superficie` (> 0) can be compared. The "Comparer" button is hidden for listings without GPS.
- **Simple radius search, not clustering:** `find_similar(target, candidates)` returns all candidates within 2 km + ±20% area of the target. No greedy grouping, no chain-linking, no order-dependence. Deterministic results.
- **Area tolerance formula:** `max_area = max(target_area, cand_area); max_area > 0 and abs(target_area - cand_area) / max_area <= SIMILAR_AREA_TOLERANCE_PCT`. The `max_area > 0` guard prevents `ZeroDivisionError` when both areas are 0. Same `<=` as existing `find_match()`. Candidates with `superficie = 0` or `None` are skipped.
- **Modal reuse:** Reuses the existing modal overlay structure from the history modal. Only one modal open at a time (opening compare closes history and vice versa). Must include `role="dialog"`, `aria-modal="true"`, `aria-label` attributes.
- **Summary stats:** Computed server-side in the API endpoint. Filter out NULL `prix_m2` values before computing `min`, `max`, `median`. Use `statistics.median` from stdlib. No `avg` (not displayed in UI).
- **Consistent response shape:** Summary is always an object `{"count": N, "min_prix_m2": ..., "max_prix_m2": ..., "median_prix_m2": ...}`. When no similar listings are found, `count` is 0 and stat fields are `null`. When all similar listings have NULL `prix_m2`, stat fields are `null` but `count` reflects the actual number of similar listings found.
- **Distance included:** Each similar listing in the response includes a `distance_m` field (rounded to nearest metre) so the user can see how far away each comparable is.
- **Sorted by distance:** Similar listings returned sorted by `distance_m` ascending (closest first).
- **Spread formula for highlighting:** `spread = (max_prix_m2 - min_prix_m2) / min_prix_m2`. Highlighting applied only when `spread > 0.10` (i.e., max is more than 10% above min). If only 1 similar listing, no highlighting (min equals max, spread is 0).
- **Nogo listings:** Included in results with their nogo flag. Frontend dims them (reduced opacity). Excluded from summary stats to avoid skewing the comparison of viable properties.
- **Scaling note:** The similar endpoint queries all listings from `annonces` on each call (O(N) full table scan). Acceptable for <500 listings. If dataset grows significantly, consider adding a lat/lng bounding-box WHERE clause in the SQL query as a pre-filter.

## Implementation Plan

### Tasks

- [x] Task 1: Add similarity config constants
  - File: `config.py`
  - Action: Add `SIMILAR_GPS_RADIUS_M = 2000` and `SIMILAR_AREA_TOLERANCE_PCT = 0.20`
  - Notes: Separate from existing match thresholds (50m / 10%) which are for repost detection.

- [x] Task 2: Add `find_similar()` function
  - File: `matcher.py`
  - Action: Add function `find_similar(target: dict, candidates: list[dict]) -> list[dict]` that:
    1. Validates target has valid `lat`, `lng`, `superficie` (float, finite, not None, > 0). Returns empty list if invalid.
    2. Iterates candidates, skipping those with invalid/missing `lat`, `lng`, or `superficie` (None, non-finite, or ≤ 0)
    3. For each valid candidate (excluding the target itself by `id`), computes haversine distance and area difference
    4. Area tolerance check: `max_area = max(target_area, cand_area); max_area > 0 and abs(target_area - cand_area) / max_area <= config.SIMILAR_AREA_TOLERANCE_PCT`
    5. Includes candidate if distance ≤ `config.SIMILAR_GPS_RADIUS_M` AND area tolerance passes
    6. Adds `distance_m` field (rounded int) to each matched candidate dict (shallow copy of original dict + distance_m, don't mutate original)
    7. Returns list of matched candidates sorted by `distance_m` ascending
  - Notes: Pure function, no DB access. Reuses `_haversine()`. Only imports `math` and `config` (existing import constraint). O(n) per call — acceptable for <500 candidates.

- [x] Task 3: Add unit tests for `find_similar()`
  - File: `tests/test_matcher.py`
  - Action: Add **bare top-level test functions** (matching existing file convention) covering:
    - `test_find_similar_nearby_candidate_included`: Target with nearby candidate (< 2 km, area ±20%) → included with correct `distance_m`
    - `test_find_similar_candidate_too_far`: Candidate > 2 km → excluded
    - `test_find_similar_area_difference_too_large`: Candidate with area difference > 20% → excluded
    - `test_find_similar_at_threshold_boundaries`: Candidate exactly at 2 km distance and 20% area diff → included (`<=`)
    - `test_find_similar_target_no_gps`: Target with no GPS → returns empty list
    - `test_find_similar_target_no_superficie`: Target with no `superficie` → returns empty list
    - `test_find_similar_candidate_no_gps`: Candidate with no GPS → skipped
    - `test_find_similar_candidate_null_superficie`: Candidate with NULL `superficie` → skipped
    - `test_find_similar_candidate_zero_superficie`: Candidate with `superficie = 0` → skipped (no ZeroDivisionError)
    - `test_find_similar_target_zero_superficie`: Target with `superficie = 0` → returns empty list
    - `test_find_similar_self_exclusion`: Candidate with same `id` as target → excluded
    - `test_find_similar_empty_candidates`: Empty candidates list → returns empty list
    - `test_find_similar_sorted_by_distance`: Results sorted by distance ascending
  - Notes: Pure function tests with dict inputs. No DB needed. Verify import constraint test (`test_no_forbidden_imports` or similar) still passes.

- [x] Task 4: Extend `GET /api/annonces` and add similar listings API endpoint
  - File: `web.py`
  - Action:
    1. **Extend existing `GET /api/annonces`:** Add `a.lat, a.lng` to the SELECT column list (after `a.note` and before the history_count subquery). This allows the frontend to know which listings have GPS coordinates for the "Comparer" button visibility.
    2. **Add `import matcher`** and **`import statistics`** at top of `web.py`.
    3. **Add `GET /api/annonces/<int:annonce_id>/similar` endpoint** that:
       a. Queries the target listing: `SELECT id, titre, prix, superficie, prix_m2, trajet, lien, lat, lng, nogo, status FROM annonces WHERE id = ?`
       b. Returns 404 `{"error": "not found"}` if listing doesn't exist
       c. Returns 400 `{"error": "listing has no GPS coordinates"}` if target has NULL lat or lng
       d. Queries all other listings with same columns from `annonces` table
       e. Calls `matcher.find_similar(target_dict, all_candidates)`
       f. Computes summary stats from results, **excluding `nogo=1` listings and those with NULL `prix_m2`**: `count` (total similar including nogo), `min_prix_m2`, `max_prix_m2`, `median_prix_m2`
       g. Returns `{"target": {...}, "similar": [...], "summary": {"count": N, "min_prix_m2": ..., "max_prix_m2": ..., "median_prix_m2": ...}}`
       h. When no similar listings found: `summary.count` is 0, stat fields are `null`
       i. When all non-nogo similar listings have NULL prix_m2: stat fields are `null`, `count` is total similar count
  - Notes: `web.py` calls `matcher.find_similar()` only — never `matcher._haversine()`.

- [x] Task 5: Add API tests for similar endpoint
  - File: `tests/test_web_api.py`
  - Action: Add **bare top-level test functions** (matching existing file convention):
    - `test_similar_returns_nearby_listings`: With nearby listings → 200, returns target + similar array + summary
    - `test_similar_nonexistent_id_returns_404`: Non-existent id → 404
    - `test_similar_no_gps_returns_400`: Listing without GPS → 400
    - `test_similar_no_results`: No similar listings → 200, empty similar array, summary.count is 0, stat fields null
    - `test_similar_summary_stats_correct`: Stats computed from non-NULL non-nogo prix_m2 only
    - `test_similar_includes_distance`: Similar listings include `distance_m` field
    - `test_similar_sorted_by_distance`: Results sorted by distance ascending
    - `test_similar_excludes_self`: Target listing not in similar array
    - `test_similar_nogo_excluded_from_stats`: Nogo listings present in results but excluded from stat calculations
    - `test_annonces_api_includes_lat_lng`: Verify `GET /api/annonces` response now includes `lat` and `lng` fields
  - Notes: Follow existing test patterns — temp DB, insert test rows with known GPS coords, assert response structure.

- [x] Task 6: Add compare button and modal to index.html
  - File: `templates/index.html`
  - Action:
    1. **Compare button:** Add a "Comparer" button (`.cmp-btn`) in each row, next to the history button. Only rendered if `a.lat != null && a.lng != null`. Style similar to `.hist-btn` but with teal accent (`background: #ccfbf1; color: #0891b2`; hover: `background: #99f6e4`).
    2. **Comparison modal:** Add a second modal (id `compareModal`) with same structure as `historyModal`:
       - Overlay: `class="modal-overlay"`, `role="dialog"`, `aria-modal="true"`, `aria-label="Comparaison de terrains similaires"`
       - Dialog: `class="modal-dialog"` with `max-width: 960px`
       - Header: showing target listing title + close button
       - Body containing:
         - **Target card:** Small summary card showing the target listing's prix, superficie, prix/m², trajet
         - **Summary stats bar:** count of similar listings, median prix/m², range prix/m² (min–max). Hidden if count is 0.
         - **Comparison table:** columns: titre (linked), prix, superficie, prix/m², trajet, distance (m). Each row for a similar listing. Nogo listings get `nogo-row` class (opacity 0.45).
         - **Highlighting:** If `(max_prix_m2 - min_prix_m2) / min_prix_m2 > 0.10` AND min_prix_m2 > 0, the row(s) with lowest prix/m² get green left-border accent (`border-left: 3px solid #16a34a`), row(s) with highest get red (`border-left: 3px solid #dc2626`). If multiple rows share the same min or max value, all get the accent.
         - **Loading state:** "Chargement…" while API call is in flight (same as history modal pattern)
         - **Error state:** "Erreur lors du chargement des terrains similaires." on non-200 response or network error
         - **Empty state:** "Aucun terrain similaire trouvé dans un rayon de 2 km." if `summary.count === 0`
       - Close handlers: close button, overlay click, Escape key
    3. **Modal exclusivity:** `openCompareModal(id)` calls `closeHistoryModal()` first; `openHistoryModal(id)` calls `closeCompareModal()` first. Refactor existing `closeModal()` into `closeHistoryModal()` and add `closeCompareModal()`.
    4. **JS logic:** `openCompareModal(id)` async function:
       - Shows modal with "Chargement…"
       - Fetches `GET /api/annonces/${id}/similar`
       - On error: shows error state message
       - On success: renders target card, summary stats (if count > 0), and comparison table
       - Uses existing helpers: `fmt()`, `escHtml()`, `statusBadge()`
    5. **Fix `escHtml()`:** Add single-quote escaping: `.replace(/'/g, "&#39;")` to prevent XSS in attribute contexts.
    6. **Event binding:** Add click handler for `.cmp-btn` buttons in `bindRowEvents()`
  - Notes: Follows exact same pattern as existing history modal. No new template file needed.

### Acceptance Criteria

- [ ] AC1: Given a listing with GPS coordinates and similar listings within 2 km + area ±20%, when clicking "Comparer", then a modal opens showing the target listing and a table of similar listings with prix, superficie, prix/m², trajet, distance.
- [ ] AC2: Given a listing with GPS but no similar listings nearby, when clicking "Comparer", then the modal shows "Aucun terrain similaire trouvé dans un rayon de 2 km."
- [ ] AC3: Given a listing without GPS coordinates, then no "Comparer" button is displayed on that row.
- [ ] AC4: Given the similar listings modal, then summary stats show: count, median prix/m², min prix/m², max prix/m².
- [ ] AC5: Given similar listings where `(max_prix_m2 - min_prix_m2) / min_prix_m2 > 0.10`, then the row(s) with the lowest prix/m² have a green left-border accent and the row(s) with the highest have a red left-border accent. If multiple rows share the same min or max value, all get the accent.
- [ ] AC6: Given similar listings where the spread is ≤ 10% or only 1 similar listing exists, then no color accents are applied.
- [ ] AC7: Given the API endpoint `GET /api/annonces/<id>/similar`, when called with a non-existent id, then it returns 404.
- [ ] AC8: Given the API endpoint, when called with a listing that has no GPS, then it returns 400 with descriptive error.
- [ ] AC9: Given similar listings in the response, then each includes a `distance_m` field and results are sorted by distance ascending.
- [ ] AC10: Given a listing with NULL `prix_m2` among the similar results, then it is excluded from summary stat calculations (no crash).
- [ ] AC11: Given `GET /api/annonces`, then the response includes `lat` and `lng` fields for each listing.
- [ ] AC12: Given the compare modal while the API is loading, then "Chargement…" is displayed. On API error, "Erreur lors du chargement des terrains similaires." is displayed.
- [ ] AC13: Given nogo=1 listings among similar results, then they appear in the table with reduced opacity but are excluded from summary stat calculations.

## Additional Context

### Dependencies

- No new external dependencies — pure stdlib + Flask (already installed)
- `statistics.median` from Python stdlib for median calculation (used in `web.py`, NOT in `matcher.py`)
- Reuses existing `_haversine()` from `matcher.py`

### Testing Strategy

- **Unit tests** (`tests/test_matcher.py`): Test `find_similar()` with controlled dict inputs. Cover: matching logic, threshold boundaries (exact `<=`), null/missing data, zero superficie, self-exclusion, empty input, distance sorting. Bare top-level functions. Verify import constraint test still passes.
- **API tests** (`tests/test_web_api.py`): Test `GET /api/annonces/<id>/similar` and verify `GET /api/annonces` now includes lat/lng. Bare top-level functions. Temp DB, insert test rows with known GPS coords, assert response structure.
- **Manual testing**: Click "Comparer" on listings with known neighbors, verify modal shows correct similar listings, check distance values make sense, verify summary stats.

### Notes

- **No order-dependence:** `find_similar()` is a simple radius search centered on the target. Results are deterministic and independent of other listings' assignments.
- **Area tolerance formula is explicit:** `max_area > 0 and abs(a1 - a2) / max(a1, a2) <= 0.20` with `<=` (inclusive at boundary) and `> 0` guard (prevents ZeroDivisionError). Candidates with `superficie ≤ 0` or `None` are skipped. Same pattern as existing `find_match()`.
- **NULL prix_m2 safety:** Summary stats filter out NULL values before computation. `statistics.median` is never called with NULL/None values or empty list. If all non-nogo similar listings have NULL prix_m2, stat fields are null but count reflects total.
- **Nogo exclusion from stats:** `nogo=1` listings are shown in the comparison table (dimmed) but excluded from summary stats to avoid skewing the comparison of viable properties.
- **Modal exclusivity:** Opening the compare modal closes any open history modal, and vice versa. Only one modal at a time.
- **Import constraint:** `matcher.py` only imports `math` and `config` (existing constraint enforced by `test_matcher.py` line 197). `statistics` is imported in `web.py` only. `web.py` calls only `matcher.find_similar()`, never `matcher._haversine()`.
- **`escHtml()` fix:** Adding single-quote escaping prevents potential XSS in attribute contexts where single quotes delimit values.
- **Scaling:** Full table scan on each "Comparer" click is acceptable for <500 listings. For larger datasets, add a SQL bounding-box pre-filter: `WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?` using ±0.02° (~2.2 km) before passing to Python.

## Review Notes
- Adversarial review completed
- Findings: 9 total, 0 fixed, 9 skipped (all classified as noise/spec-compliant)
- Resolution approach: skip
