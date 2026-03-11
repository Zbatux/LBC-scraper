# Story 2.2: Status Badges in Main Table

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As Bogoss,
I want to see a visual status badge (new / price changed / reposted) for each listing in the web UI main table,
so that I can immediately identify actionable listings without opening each one individually.

## Acceptance Criteria

### AC1: Green "new" badge for new listings

**Given** a listing with `status = 'new'`
**When** the main table renders
**Then** a green "new" badge is displayed in the status column for that listing (FR15, FR16)

### AC2: Amber "price changed" badge

**Given** a listing with `status = 'price_changed'`
**When** the main table renders
**Then** an amber "price changed" badge is displayed (FR15)

### AC3: Blue "reposted" badge

**Given** a listing with `status = 'reposted'`
**When** the main table renders
**Then** a blue "reposted" badge is displayed (FR15)

### AC4: No visual noise for unchanged listings

**Given** a listing with `status = 'unchanged'`
**When** the main table renders
**Then** no badge or only a neutral/muted indicator is shown (no visual noise)

### AC5: Dates visible in row

**Given** a listing
**When** the main table renders
**Then** `date_publication` and `first_seen` are visible in the listing row (FR17)

### AC6: Performance

**Given** 500 listings loaded from the API
**When** the page fully renders
**Then** load time is under 2 seconds on localhost (NFR2)

---

## Tasks / Subtasks

- [x] Task 1: Add CSS for status badge variants (AC: #1, #2, #3, #4)
  - [x] Add `.status-badge` base style + `.status-new`, `.status-changed`, `.status-reposted`, `.status-unchanged` variants in the `<style>` block (after the existing `.badge-null` rule)

- [x] Task 2: Add "Statut" column header to `<thead>` (AC: #1, #2, #3, #4)
  - [x] Insert `<th class="sortable" data-col="status">Statut</th>` as the **2nd column** in `<thead>` (right after the checkbox `<th class="sel-cell">`, before `Titre`)

- [x] Task 3: Add date columns to `<thead>` (AC: #5)
  - [x] Insert `<th class="sortable" data-col="first_seen">1ère vue</th>` and `<th class="sortable" data-col="date_publication">Publié le</th>` after "Statut" header

- [x] Task 4: Add `statusBadge()` helper function in JS (AC: #1, #2, #3, #4)
  - [x] Implement `function statusBadge(status)` returning the correct badge HTML per status value

- [x] Task 5: Add `fmtDate()` helper function in JS (AC: #5)
  - [x] Implement `function fmtDate(iso)` that formats ISO8601 string to `DD/MM/YYYY` (locale-friendly), returning `"—"` for null

- [x] Task 6: Update `render()` to insert new cells into `tr.innerHTML` (AC: #1–#5)
  - [x] Add status badge `<td>` right after `<td class="sel-cell">...</td>` in `tr.innerHTML`
  - [x] Add first_seen `<td>` and date_publication `<td>` in the correct position

- [x] Task 7: Add status filter dropdown to filter bar (optional but useful for FR16) (AC: #1)
  - [x] Add `<select id="fStatus">` with options: Tous / Nouveaux / Prix changé / Reposté / Inchangé
  - [x] Hook it into `getFiltered()` with appropriate filter logic
  - [x] Include it in `resetFilters` cleanup

---

## Dev Notes

### What This Story Does and Does NOT Include

**Does:**
- Add status badge column to `templates/index.html` (CSS + thead + tbody rendering)
- Add `first_seen` and `date_publication` display columns to the table
- Add a status filter dropdown
- No backend changes — `GET /api/annonces` already returns all three fields (Story 2.1 complete)

**Does NOT:**
- Modify `web.py` — API is complete and correct
- Add any new Flask endpoint (Story 2.3)
- Add the history modal (Story 2.4)
- Add `status` to `EDITABLE_FIELDS` — it is read-only (set by `save_or_merge`)
- Write Python unit tests — this is a pure frontend change with no new server-side logic

### Critical: No Backend Changes

`GET /api/annonces` already returns `status`, `first_seen`, and `date_publication` in every listing object (confirmed by Story 2.1 completion). The `allData` array in `index.html` already contains these fields after `loadData()`. This story is **100% frontend**.

### Critical: Exact Insertion Points in `templates/index.html`

#### 1. CSS — Insert after `.badge-null` rule (approx line 148)

```css
/* status badge */
.status-badge {
  display: inline-block; padding: 2px 7px;
  border-radius: 10px; font-size: 10px; font-weight: 700;
  white-space: nowrap;
}
.status-new      { background: #dcfce7; color: #166534; }  /* green */
.status-changed  { background: #fef3c7; color: #92400e; }  /* amber */
.status-reposted { background: #dbeafe; color: #1e40af; }  /* blue */
.status-unchanged { background: #f1f5f9; color: #94a3b8; font-weight: 400; } /* neutral muted */
```

#### 2. `<thead>` — Insert right after the checkbox `<th>` (line 257)

**Before:**
```html
<th class="sel-cell"><input type="checkbox" id="selectAll" /></th>
<th class="sortable" data-col="titre">Titre</th>
```

**After:**
```html
<th class="sel-cell"><input type="checkbox" id="selectAll" /></th>
<th class="sortable" data-col="status">Statut</th>
<th class="sortable" data-col="first_seen">1ère vue</th>
<th class="sortable" data-col="date_publication">Publié le</th>
<th class="sortable" data-col="titre">Titre</th>
```

#### 3. `statusBadge()` JS helper — Add near the existing `badge()` function (approx line 286)

```javascript
function statusBadge(status) {
  if (status === 'new')           return `<span class="status-badge status-new">nouveau</span>`;
  if (status === 'price_changed') return `<span class="status-badge status-changed">prix changé</span>`;
  if (status === 'reposted')      return `<span class="status-badge status-reposted">reposté</span>`;
  if (status === 'unchanged')     return `<span class="status-badge status-unchanged">—</span>`;
  return `<span class="status-badge status-unchanged">—</span>`; // null/unknown fallback
}
```

#### 4. `fmtDate()` JS helper — Add near `statusBadge()`

```javascript
function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return "—";
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
}
```

#### 5. `tr.innerHTML` in `render()` — Insert new cells right after `<td class="sel-cell">` (approx line 384)

**Before (first two cells in tr.innerHTML):**
```javascript
tr.innerHTML = `
  <td class="sel-cell"><input type="checkbox" class="row-cb" /></td>
  <td class="titre-cell" title="${escHtml(a.titre || "")}">${escHtml(a.titre || "—")}</td>
```

**After:**
```javascript
tr.innerHTML = `
  <td class="sel-cell"><input type="checkbox" class="row-cb" /></td>
  <td>${statusBadge(a.status)}</td>
  <td>${fmtDate(a.first_seen)}</td>
  <td>${fmtDate(a.date_publication)}</td>
  <td class="titre-cell" title="${escHtml(a.titre || "")}">${escHtml(a.titre || "—")}</td>
```

#### 6. Status filter dropdown — Add to the `#filters` div (after the Note filter, before the reset button)

```html
<span class="filter-sep">|</span>
<label>Statut
  <select id="fStatus">
    <option value="">Tous</option>
    <option value="new">Nouveaux</option>
    <option value="price_changed">Prix changé</option>
    <option value="reposted">Reposté</option>
    <option value="unchanged">Inchangé</option>
  </select>
</label>
```

#### 7. `getFiltered()` — Add status filter logic

Add inside the `return allData.filter(a => {` block, after existing filters:
```javascript
const fStatus = document.getElementById("fStatus").value;
// ...
if (fStatus && a.status !== fStatus) return false;
```

Also add `"fStatus"` to the event listener array:
```javascript
["hideNogo","fPrixMin","fPrixMax","fSurfMin","fSurfMax","fPm2Min","fPm2Max","fTrajetMax","fNoteMin",
 "fViabilise","fConstruct","fAgricole","fStatus"]
  .forEach(id => document.getElementById(id).addEventListener("input", render));
["hideNogo","fViabilise","fConstruct","fAgricole","fStatus"].forEach(id =>
  document.getElementById(id).addEventListener("change", render));
```

And add `"fStatus"` to the reset block:
```javascript
["fViabilise","fConstruct","fAgricole","fStatus"]
  .forEach(id => document.getElementById(id).value = "");
```

### Critical: Sorting Already Works for New Columns

The existing `getSorted()` function (line 357) uses `a[sortCol]` generically. Since `status`, `first_seen`, and `date_publication` are now in `allData` (from the API), adding them as `data-col` attributes on `<th>` is sufficient — sorting is automatically handled. No changes to `getSorted()` needed.

### Critical: Performance (NFR2)

The status badge rendering is a simple string substitution — zero additional API calls or DOM queries per row. `statusBadge()` and `fmtDate()` are pure functions. For 500 listings, the added cost is negligible. The existing `render()` pattern with `innerHTML` batch DOM writes already meets NFR2.

`Date.toLocaleDateString("fr-FR")` is called once per row for each date field. For 500 rows, this is ~1000 calls — well within the 2-second budget on any modern machine.

### Testing: No New Python Tests Required

This story adds only HTML/CSS/JS to `templates/index.html`. There is no new Flask route, no new SQL, and no new Python logic. The existing 4 tests in `tests/test_web_api.py` already cover the API contract (Story 2.1). No new test file is needed for pure frontend rendering — there is no JS test framework in this project and no build step.

The dev agent should **not** add Python tests for HTML rendering. The acceptance criteria are verified visually by loading the web UI after a `--scrape` run.

### Previous Story Intelligence (Story 2.1)

Key confirmed facts from Story 2.1 completion:
- `GET /api/annonces` returns 17 fields per listing: the 14 original + `status`, `first_seen`, `date_publication`
- `status` is always a lowercase string literal or `null` (never an int, never an enum)
- `first_seen` is an ISO8601 string (e.g., `"2024-01-01T10:00:00"`) set on INSERT — never null for new listings
- `date_publication` can be `null` (listings without publication date) — the UI must handle this gracefully
- `web.py` uses `try/finally` for DB connection cleanup — no change needed
- `ensure_columns()` already covers all three new fields — old databases are migrated on startup
- 4 existing tests pass (`tests/test_web_api.py`) — do not break them

**Code Review fixes already applied in Story 2.1 that affect this story:**
- M3: `ensure_columns()` guarded with `os.path.exists(DB_NAME)` — prevents empty DB creation at import, safe for test environments

### Git Intelligence (last 5 commits)

```
f0eba7d story 2-1 implemented   → web.py: SELECT + ensure_columns; tests/test_web_api.py created
8c46b1e story 1-4 implemented   → database.py: save_or_merge, transactions
c5cfbd9 story 1-3 implemented   → parsers.py: lat, lng, date_publication
d1ca5ef Story 1-2 implemented   → database.py: schema migrations, annonces_history
4b19125 story 1-1 implemented   → matcher.py, config.py
```

Pattern: one commit per story. No work-in-progress commits. This story's commit will be `story 2-2 implemented`.

### Architecture Compliance

Per [architecture.md — Structure Patterns](../../planning-artifacts/architecture.md#structure-patterns):
- `web.py`: Flask routes only — no business logic ✓ (no changes to web.py this story)
- `templates/index.html`: Vanilla JS + Jinja2 — no build step, no npm ✓

Per [architecture.md — Format Patterns](../../planning-artifacts/architecture.md#format-patterns):
- Status values: lowercase string literals (`'new'`, `'price_changed'`, `'reposted'`, `'unchanged'`) — badge logic must match exactly ✓
- Nullable fields: `null` in JSON — `fmtDate()` must handle `null` gracefully ✓

Per [architecture.md — API Boundaries](../../planning-artifacts/architecture.md#api-boundaries):
- `/api/annonces` response shape: `[{id, titre, prix, ..., status, first_seen, date_publication}]` ✓ (already complete)

### Project Structure Notes

**File to modify:**
- `templates/index.html` — add CSS, 3 `<th>` headers, 3 `<td>` cells per row, 2 JS helpers, 1 filter dropdown, filter logic updates

**Files NOT touched:**
- `web.py` — API complete and correct (Story 2.1 done)
- `database.py` — complete (Epic 1 done)
- `matcher.py` — complete
- `tests/test_web_api.py` — no new tests needed for pure frontend
- All other files

### References

- [templates/index.html:141-148](../../templates/index.html#L141) — existing `.badge*` CSS rules (insert new status CSS here)
- [templates/index.html:255-273](../../templates/index.html#L255) — `<thead>` (insert new `<th>` headers)
- [templates/index.html:284-290](../../templates/index.html#L284) — `badge()` helper (add `statusBadge()` and `fmtDate()` nearby)
- [templates/index.html:379-403](../../templates/index.html#L379) — `render()` and `tr.innerHTML` (add new `<td>` cells)
- [templates/index.html:570-583](../../templates/index.html#L570) — filter event listeners and reset logic (add `fStatus`)
- [web.py:73-86](../../web.py#L73) — `get_annonces()` — SELECT already includes `status`, `first_seen`, `date_publication`
- [Epics: Story 2.2](../../planning-artifacts/epics.md#story-22-status-badges-in-main-table) — acceptance criteria source
- [architecture.md — API Boundaries](../../planning-artifacts/architecture.md#api-boundaries) — API response shape contract

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Task 1: Added `.status-badge` base class + `.status-new` (green), `.status-changed` (amber), `.status-reposted` (blue), `.status-unchanged` (neutral) CSS after the `.badge-null` rule.
- Task 2: Added `<th class="sortable" data-col="status">Statut</th>` as 2nd column in `<thead>` (after checkbox, before Titre).
- Task 3: Added `<th>` headers for `first_seen` ("1ère vue") and `date_publication` ("Publié le") immediately after the Statut header. Sorting works automatically via the existing `getSorted()` generic `a[sortCol]` lookup — no changes to sorting logic required.
- Task 4: Added `statusBadge(status)` pure function returning correct badge HTML for all 4 status values + null/unknown fallback.
- Task 5: Added `fmtDate(iso)` pure function formatting ISO8601 strings to `DD/MM/YYYY` via `toLocaleDateString("fr-FR")`, returning `"—"` for null/invalid.
- Task 6: Added 3 new `<td>` cells in `tr.innerHTML` (status badge, first_seen, date_publication) immediately after the checkbox cell, before the titre cell.
- Task 7: Added `<select id="fStatus">` filter dropdown with 5 options in the `#filters` div; added `fStatus` variable and filter predicate in `getFiltered()`; added `fStatus` to both input and change event listener arrays; added `fStatus` to `resetFilters` reset block.
- All 69 pre-existing tests pass — zero regressions. No new Python tests added (pure frontend change, no new Flask routes or Python logic).

### File List

- `templates/index.html` — modified: status badge CSS, 3 new thead columns, `statusBadge()` + `fmtDate()` JS helpers, 3 new td cells per row, status filter dropdown + getFiltered() logic + event listeners + reset
- `parsers.py` — modified (code review fix M1): `parse_date_publication` now normalizes Unix timestamp integers to ISO 8601 datetime strings

### Senior Developer Review (AI)

**Date:** 2026-03-11
**Reviewer:** claude-sonnet-4-6 (adversarial code review)
**Outcome:** Approved with fixes applied

**Fixes applied:**
- **M1** (`parsers.py:54`): `parse_date_publication` now handles Unix timestamp integers (LBC API may return `first_publication_date` as an int). Converts via `datetime.fromtimestamp(..., tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")` before storing. Falls back to `str(val)` for non-numeric formats.
- **M2** (`templates/index.html:fmtDate`): Added date-only ISO string detection (`/^\d{4}-\d{2}-\d{2}$/`) and appends `T00:00:00` before parsing to force local-time interpretation, preventing off-by-one-day display for French users (UTC+1/+2).
- **M3** (`templates/index.html:event listeners`): Removed `fStatus` from the "input" listener array — `<select>` elements should only use "change". Eliminates double `render()` call on each status filter interaction.
- **L1** (`templates/index.html:statusBadge`): Removed redundant `unchanged` branch; single fallback return covers both `unchanged` and `null/unknown`.

**Remaining known issues (accepted):**
- L2: ISO dates sorted via `localeCompare` — functionally correct for ASCII date strings
- L3: `null` status not a selectable filter option — acceptable (null = legacy pre-migration rows)
- L4: No error handling in `loadData()` — pre-existing, out of scope for this story
