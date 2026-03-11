# Story 2.4: History Modal

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As Bogoss,
I want to click a listing and see a history modal with every recorded snapshot and highlighted field changes,
so that I can read price trajectories and seller behaviour signals at a glance — my key negotiation tool.

## Acceptance Criteria

### AC1: Modal opens with chronological snapshots for listings with history

**Given** a listing with at least one `annonces_history` row
**When** I click the history trigger for that listing
**Then** a modal opens displaying the full chronological list of snapshots ordered oldest to newest (FR18, FR19)

### AC2: Each snapshot shows its timestamp

**Given** the modal is open
**Then** each snapshot row shows its `scraped_at` timestamp (FR21)

### AC3: Price changes are highlighted

**Given** two consecutive snapshots where `prix` differs
**When** the modal renders
**Then** the price field is visually highlighted (e.g., colour, bold) to indicate the change (FR20)

### AC4: Other field changes are also highlighted

**Given** two consecutive snapshots where fields other than `prix` differ (e.g., `titre`, `list_id`)
**When** the modal renders
**Then** those fields are also highlighted (FR20)

### AC5: History trigger is hidden for listings with no history

**Given** a listing with no history rows
**When** the main table renders
**Then** the history trigger is hidden or disabled — no empty modal can be opened (FR18)

### AC6: Full flow completes within 500ms

**Given** clicking the history trigger
**When** the API call to `/api/annonces/<id>/history` completes and the modal renders
**Then** the full flow takes under 500ms on localhost (NFR3)

---

## Tasks / Subtasks

- [x] Task 1: Update `GET /api/annonces` to include `history_count` per listing (AC: #5)
  - [x] In `web.py` `get_annonces()`, add subquery: `(SELECT COUNT(*) FROM annonces_history WHERE annonce_id = a.id) AS history_count` to the SELECT
  - [x] Alias the `annonces` table as `a` in the FROM clause: `FROM annonces a ORDER BY a.id`
  - [x] Verify all existing column names are qualified with `a.` if needed (no ambiguity since only one table, alias is safe)

- [x] Task 2: Add history modal CSS to `templates/index.html` (AC: #1, #2, #3, #4)
  - [x] Add modal overlay + dialog styles (`.modal-overlay`, `.modal-dialog`, `.modal-header`, `.modal-body`)
  - [x] Add history table styles (`.history-table`)
  - [x] Add diff-highlight style (`.cell-changed`) — amber/yellow background to signal change
  - [x] Add snapshot separator / timestamp row style

- [x] Task 3: Add "Historique" column and trigger button to `templates/index.html` table (AC: #5)
  - [x] Add `<th>Historique</th>` header at the end of `<thead>` row (after "Lien")
  - [x] In `render()` function, add history trigger cell to each row's `tr.innerHTML`:
    - If `a.history_count > 0` → `<td><button class="hist-btn" data-id="${a.id}">📋 ${a.history_count}</button></td>`
    - Else → `<td class="hist-cell">—</td>`

- [x] Task 4: Add modal HTML to `templates/index.html` body (AC: #1, #2)
  - [x] Add modal overlay div after `#tableWrap`:
    ```html
    <div id="historyModal" class="modal-overlay" style="display:none" role="dialog" aria-modal="true" aria-label="Historique de l'annonce">
      <div class="modal-dialog">
        <div class="modal-header">
          <span id="modalTitle">Historique</span>
          <button id="modalClose" aria-label="Fermer">✕</button>
        </div>
        <div class="modal-body" id="modalBody"></div>
      </div>
    </div>
    ```

- [x] Task 5: Add `openHistoryModal(id)` JS function to `templates/index.html` (AC: #1, #2, #3, #4, #6)
  - [x] Fetch `GET /api/annonces/<id>/history`
  - [x] Render history table with columns: `scraped_at`, `status`, `prix`, `titre`, `list_id`, `superficie`, `prix_m2`
  - [x] Diff logic: for each snapshot at index `i > 0`, compare each displayed field with snapshot `i-1`; if different → add `cell-changed` class to that `<td>`
  - [x] First snapshot (index 0) has no diff — render normally (no highlighting)
  - [x] Display modal

- [x] Task 6: Bind history trigger click events in `bindRowEvents()` (AC: #1)
  - [x] Add event listener for `.hist-btn` clicks → call `openHistoryModal(parseInt(btn.dataset.id))`

- [x] Task 7: Bind modal close events (AC: #1)
  - [x] `#modalClose` button click → `closeModal()`
  - [x] Overlay click (outside dialog) → `closeModal()`
  - [x] Escape key → `closeModal()`
  - [x] `closeModal()`: set `#historyModal` display to none, clear `#modalBody`

- [x] Task 8: Add tests for updated `/api/annonces` with `history_count` to `tests/test_web_api.py` (AC: #5)
  - [x] `test_get_annonces_includes_history_count`: insert listing + 2 history rows, verify `history_count == 2` — covers AC5 (count present)
  - [x] `test_get_annonces_history_count_zero_for_no_history`: insert listing without history rows, verify `history_count == 0` — covers AC5 (zero = trigger hidden)
  - [x] `test_get_annonces_non_regression_after_history_count_addition`: verify `history_count` in field list of basic listing response (non-regression guard)

---

## Dev Notes

### What This Story Does and Does NOT Include

**Does:**
- Update `web.py` `get_annonces()` SELECT to include `history_count` subquery
- Add CSS for modal overlay, dialog, history table, diff highlighting to `templates/index.html`
- Add "Historique" `<th>` column header and trigger cell to the main table
- Add modal HTML structure to the page body
- Add `openHistoryModal(id)` JS function with fetch + diff rendering
- Add modal close handlers (button, overlay click, Escape key)
- Bind `.hist-btn` click events in `bindRowEvents()`
- Add 3 new test functions to `tests/test_web_api.py`

**Does NOT:**
- Modify `database.py` — `annonces_history` schema is complete (Epic 1 done)
- Add new Flask endpoints — `GET /api/annonces/<int:id>/history` already exists (Story 2.3 done)
- Add new Python dependencies
- Modify `matcher.py`, `config.py`, `parsers.py`, `main.py`

### Critical: `web.py` GET /api/annonces Query Update (Task 1)

**Current query (lines 109–115):**
```python
rows = conn.execute(
    "SELECT id, titre, prix, superficie, prix_m2, trajet, lien, "
    "viabilise, emprise_sol, partiellement_constructible, partiellement_agricole, "
    "analyse_faite, nogo, note, "
    "status, first_seen, date_publication "
    "FROM annonces ORDER BY id"
).fetchall()
```

**Updated query with `history_count`:**
```python
rows = conn.execute(
    "SELECT a.id, a.titre, a.prix, a.superficie, a.prix_m2, a.trajet, a.lien, "
    "a.viabilise, a.emprise_sol, a.partiellement_constructible, a.partiellement_agricole, "
    "a.analyse_faite, a.nogo, a.note, "
    "a.status, a.first_seen, a.date_publication, "
    "(SELECT COUNT(*) FROM annonces_history WHERE annonce_id = a.id) AS history_count "
    "FROM annonces a ORDER BY a.id"
).fetchall()
```

**Why subquery instead of LEFT JOIN + GROUP BY:**
- Simpler query — no GROUP BY on all 17 columns
- Same performance for <500 listings (SQLite query optimizer handles it well)
- `idx_history_annonce_id` index on `annonces_history(annonce_id)` makes the COUNT(*) subquery O(1) per row (NFR4)
- Consistent with architecture pattern: web.py routes query directly, no intermediate service layer

### Critical: History Modal JS Implementation (Tasks 4–7)

**Full `openHistoryModal(id)` function:**
```javascript
async function openHistoryModal(id) {
  const ann = allData.find(x => x.id === id);
  document.getElementById("modalTitle").textContent =
    ann ? `Historique — ${escHtml(ann.titre || "annonce #" + id)}` : `Historique #${id}`;
  document.getElementById("modalBody").innerHTML = "<p>Chargement…</p>";
  document.getElementById("historyModal").style.display = "flex";

  const res = await fetch(`/api/annonces/${id}/history`);
  const snapshots = await res.json();

  if (!Array.isArray(snapshots) || snapshots.length === 0) {
    document.getElementById("modalBody").innerHTML = "<p>Pas d'historique pour cette annonce.</p>";
    return;
  }

  // Columns to display in modal (subset of full snapshot)
  const COLS = [
    { key: "scraped_at",  label: "Date snapshot" },
    { key: "status",      label: "Statut" },
    { key: "prix",        label: "Prix €" },
    { key: "titre",       label: "Titre" },
    { key: "list_id",     label: "ID annonce" },
    { key: "superficie",  label: "Superficie m²" },
    { key: "prix_m2",     label: "€/m²" },
  ];

  let html = '<table class="history-table"><thead><tr>';
  COLS.forEach(c => { html += `<th>${c.label}</th>`; });
  html += "</tr></thead><tbody>";

  snapshots.forEach((snap, i) => {
    const prev = i > 0 ? snapshots[i - 1] : null;
    html += "<tr>";
    COLS.forEach(c => {
      const val = snap[c.key];
      const changed = prev !== null && String(prev[c.key]) !== String(val);
      const cls = changed ? ' class="cell-changed"' : "";
      let display;
      if (c.key === "scraped_at") {
        display = fmtDate(val);
      } else if (c.key === "prix" || c.key === "prix_m2") {
        display = val != null ? fmt(val, 0) : "—";
      } else {
        display = val != null ? escHtml(String(val)) : "—";
      }
      html += `<td${cls}>${display}</td>`;
    });
    html += "</tr>";
  });

  html += "</tbody></table>";
  document.getElementById("modalBody").innerHTML = html;
}

function closeModal() {
  document.getElementById("historyModal").style.display = "none";
  document.getElementById("modalBody").innerHTML = "";
}
```

**Key design decisions:**
- `fmtDate()` and `fmt()` and `escHtml()` are already defined — reuse them
- `String(prev[c.key]) !== String(val)` comparison handles null vs "null" edge case correctly: both sides convert to string so null → "null", preserving intent
- `display = "flex"` for the overlay so the `modal-dialog` can be centred with flexbox
- The first snapshot is never highlighted (no `prev` → `changed = false`) — this is correct because we have no baseline to compare against

### Critical: CSS Additions (Task 2)

**Add to the `<style>` block before `</style>`:**
```css
/* ── History modal ────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, .5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal-dialog {
  background: #fff; border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0,0,0,.25);
  width: 90%; max-width: 860px; max-height: 80vh;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: #1a1a2e; color: #fff;
  font-size: 14px; font-weight: 600;
  flex-shrink: 0;
}
.modal-header button {
  background: none; border: none; color: #fff;
  font-size: 18px; cursor: pointer; line-height: 1;
}
.modal-header button:hover { color: #aab; }
.modal-body {
  overflow-y: auto; padding: 16px;
  flex: 1;
}
.history-table {
  width: 100%; border-collapse: collapse; font-size: 12px;
}
.history-table th {
  background: #f1f5f9; padding: 7px 8px;
  text-align: left; font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .04em;
  white-space: nowrap; border-bottom: 2px solid #e2e8f0;
}
.history-table td {
  padding: 6px 8px; border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}
.history-table tr:last-child td { border-bottom: none; }
.cell-changed {
  background: #fef3c7; color: #92400e; font-weight: 700;
}

/* history trigger button */
.hist-btn {
  padding: 3px 8px; background: #e0e7ff; border: none;
  border-radius: 4px; font-size: 11px; cursor: pointer; white-space: nowrap;
}
.hist-btn:hover { background: #c7d2fe; }
```

### Critical: Table Column Addition (Task 3)

**Thead — add after `<th>Lien</th>`:**
```html
<th>Historique</th>
```

**Tbody — in `render()` function, add after the lien cell in `tr.innerHTML`:**
```javascript
<td>${a.history_count > 0
  ? `<button class="hist-btn" data-id="${a.id}">📋 ${a.history_count}</button>`
  : '—'
}</td>
```

### Critical: Event Binding (Tasks 6–7)

**In `bindRowEvents()`, add after the existing listeners:**
```javascript
// History trigger
document.querySelectorAll(".hist-btn").forEach(btn => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation(); // prevent row checkbox from triggering
    openHistoryModal(parseInt(btn.dataset.id));
  });
});
```

**After `loadData()` at end of script (Escape key + overlay click — bound once):**
```javascript
// Modal close handlers (bound once at init)
document.getElementById("modalClose").addEventListener("click", closeModal);
document.getElementById("historyModal").addEventListener("click", function(e) {
  if (e.target === this) closeModal(); // click outside dialog
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeModal();
});
```

### Critical: Test Implementation (Task 8)

Follow the exact existing test pattern in `tests/test_web_api.py`:

```python
# ---------------------------------------------------------------------------
# Story 2.4: history_count field in GET /api/annonces
# ---------------------------------------------------------------------------

def test_get_annonces_includes_history_count(client):
    """AC5: history_count is present and equals number of history rows."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    annonce = conn.execute("SELECT id FROM annonces LIMIT 1").fetchone()
    annonce_id = annonce["id"]
    conn.execute(
        "INSERT INTO annonces_history (annonce_id, scraped_at, titre, prix, status, list_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (annonce_id, "2024-01-01T10:00:00", "Terrain v1", 40000.0, "price_changed", "1000001")
    )
    conn.execute(
        "INSERT INTO annonces_history (annonce_id, scraped_at, titre, prix, status, list_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (annonce_id, "2024-02-01T10:00:00", "Terrain v2", 45000.0, "price_changed", "1000001")
    )
    conn.commit()
    conn.close()

    response = c.get("/api/annonces")
    data = response.get_json()
    listing = data[0]

    assert "history_count" in listing
    assert listing["history_count"] == 2


def test_get_annonces_history_count_zero_for_no_history(client):
    """AC5: listing with no history rows → history_count == 0."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    response = c.get("/api/annonces")
    data = response.get_json()
    listing = data[0]

    assert "history_count" in listing
    assert listing["history_count"] == 0


def test_get_annonces_non_regression_after_history_count_addition(client):
    """Non-regression: all 17 previously expected fields still present after history_count added."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    response = c.get("/api/annonces")
    data = response.get_json()
    listing = data[0]

    expected_fields = [
        "id", "titre", "prix", "superficie", "prix_m2", "trajet", "lien",
        "viabilise", "emprise_sol", "partiellement_constructible", "partiellement_agricole",
        "analyse_faite", "nogo", "note", "status", "first_seen", "date_publication",
        "history_count",
    ]
    for field in expected_fields:
        assert field in listing, f"Field missing from GET /api/annonces response: {field}"
```

### Architecture Compliance

Per [architecture.md — API Boundaries](../../planning-artifacts/architecture.md#api-boundaries):
- `GET /api/annonces` returns bare JSON array `[{...}]` — adding `history_count` field preserves this ✓
- History endpoint `GET /api/annonces/<int:id>/history` already implemented (Story 2.3) ✓
- Subquery returns an `INTEGER` — consistent with snake_case JSON key convention ✓

Per [architecture.md — Structure Patterns](../../planning-artifacts/architecture.md#structure-patterns):
- `web.py`: query updated in `get_annonces()` — no business logic added ✓
- DB access: `get_db()` helper → `try/finally conn.close()` pattern preserved ✓
- `templates/index.html`: vanilla JS + Jinja2, no build step, no frameworks added ✓

Per [architecture.md — Format Patterns](../../planning-artifacts/architecture.md#format-patterns):
- No new API endpoints — only extended existing GET response ✓
- `history_count` INTEGER — stored as-is from SQLite COUNT(*) ✓

Per [architecture.md — Performance](../../planning-artifacts/architecture.md#nfr):
- `idx_history_annonce_id` index on `annonces_history(annonce_id)` makes COUNT(*) subquery O(1) per row (NFR4) ✓
- Modal fetch and render: single API call → <500ms on localhost (NFR3) ✓
- Main table load: subquery adds negligible overhead for <500 listings (NFR2) ✓

### Previous Story Intelligence (Story 2.3)

Key confirmed facts from Story 2.3 completion notes:

**Architecture confirmed in production:**
- `web.py` uses `try/finally` for DB connection cleanup ✓
- `ensure_columns()` in `web.py` is guarded with `os.path.exists(DB_NAME)` — do not remove this guard ✓
- `ensure_columns()` now creates `annonces_history` table and index (code review fix M3) ✓
- `templates/index.html` has: status badges, `first_seen`, `date_publication` columns, status filter dropdown, `statusBadge()`, `fmtDate()` — all available for reuse ✓
- `parsers.py` `parse_date_publication` handles Unix timestamp integers (Story 2.2 M1 fix) ✓
- 8 existing tests pass in `tests/test_web_api.py` — new tests must not break them ✓
- `GET /api/annonces/<int:id>/history` is working and returns full `annonces_history` rows including: `id`, `annonce_id`, `scraped_at`, `titre`, `prix`, `superficie`, `prix_m2`, `trajet`, `lien`, `unique_key`, `description`, `viabilise`, `emprise_sol`, `partiellement_constructible`, `partiellement_agricole`, `analyse_faite`, `nogo`, `note`, `lat`, `lng`, `status`, `first_seen`, `date_publication`, `list_id` ✓

**Critical: existing `test_get_annonces_non_regression_existing_fields` test:**
This test in `tests/test_web_api.py` checks for 14 pre-existing fields. Adding `history_count` to the SELECT does NOT break this test — it checks field presence, not exhaustiveness. ✓

**Critical: `SAMPLE_LISTING` fixture (already in test file):**
```python
SAMPLE_LISTING = {
    "titre": "Terrain test", "prix": 50000.0, "superficie": 500.0,
    "prix_m2": 100.0, "trajet": "15 min", "lien": "https://www.leboncoin.fr/ad/1",
    "lat": 43.6, "lng": 1.4, "date_publication": "2024-01-01T10:00:00", "list_id": "1000001",
}
```
Reuse directly — do NOT redefine in story 2.4 tests.

### Git Intelligence (last 5 commits)

```
2e7f936 story 2-2 implemented  → templates/index.html: status badges, date cols, status filter, fmtDate, statusBadge
f0eba7d story 2-1 implemented  → web.py: GET /api/annonces SELECT updated; tests/test_web_api.py created
8c46b1e story 1-4 implemented  → database.py: save_or_merge, transactions, annonces_history writes
c5cfbd9 story 1-3 implemented  → parsers.py: lat, lng, date_publication extraction
d1ca5ef Story 1-2 implemented  → database.py: schema migrations, annonces_history table, idx_history_annonce_id
```

Pattern: one commit per story. This story's commit should follow: `story 2-4 implemented`.

**Key patterns from prior commits:**
- `web.py` modified in stories 2.1 and 2.3 — familiar territory
- `templates/index.html` modified in story 2.2 — last major JS/CSS change; story 2.4 continues this pattern
- `tests/test_web_api.py` extended in stories 2.1 and 2.3 — append new test functions at the bottom

### Project Structure Notes

**Files to modify:**
- `web.py` — update `get_annonces()` SELECT query to add `history_count` subquery (Task 1)
- `templates/index.html` — CSS additions, `<th>` column, `<td>` trigger cell, modal HTML, `openHistoryModal()` JS, `closeModal()` JS, event binding (Tasks 2–7)
- `tests/test_web_api.py` — append 3 new test functions (Task 8)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — update `2-4-history-modal` status to `done` after completion

**Files NOT touched:**
- `database.py` — `annonces_history` schema and index already exist and are complete
- `matcher.py`, `config.py`, `parsers.py`, `main.py` — all untouched
- No new Python dependencies

### References

- [web.py:106-118](../../web.py#L106) — `get_annonces()` route to update (add history_count subquery)
- [web.py:35-38](../../web.py#L35) — `get_db()` helper
- [web.py:41-87](../../web.py#L41) — `ensure_columns()` with `annonces_history` schema
- [templates/index.html:7-190](../../templates/index.html#L7) — `<style>` block to append CSS to
- [templates/index.html:278-297](../../templates/index.html#L278) — `<thead>` where to add Historique `<th>`
- [templates/index.html:421-445](../../templates/index.html#L421) — `render()` tbody loop where to add trigger cell
- [templates/index.html:462-476](../../templates/index.html#L462) — `bindRowEvents()` where to add `.hist-btn` listener
- [templates/index.html:630-632](../../templates/index.html#L630) — `loadData()` call at end of script; add modal close handlers after this
- [tests/test_web_api.py:126-208](../../tests/test_web_api.py#L126) — Story 2.3 tests to append after
- [Epics: Story 2.4](../../planning-artifacts/epics.md#story-24-history-modal) — acceptance criteria source
- [architecture.md — API Boundaries](../../planning-artifacts/architecture.md#api-boundaries) — endpoint contracts
- [architecture.md — Performance](../../planning-artifacts/architecture.md#performance) — NFR3 (500ms modal)

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Task 1: Updated `get_annonces()` in `web.py` — added `(SELECT COUNT(*) FROM annonces_history WHERE annonce_id = a.id) AS history_count` subquery; aliased `annonces` as `a`. Uses existing `idx_history_annonce_id` index for O(1) per row (NFR4). All 8 pre-existing tests continue to pass.
- Task 8 (red phase first): Added 3 test functions for `history_count` to `tests/test_web_api.py` — verified they failed before Task 1 implementation. All 3 pass after Task 1 change. Total: 11/11 tests pass.
- Tasks 2–4: Added CSS block (modal overlay, dialog, header, body, history-table, cell-changed, hist-btn) to `<style>` block; added `<div id="historyModal">` modal HTML after `#tableWrap`; added `<th>Historique</th>` column header.
- Task 3 (tbody): Added history trigger cell to `render()` tbody loop — shows `📋 N` button when `history_count > 0`, `—` otherwise. Implements AC5 (no empty modal possible).
- Task 5: Added `openHistoryModal(id)` async JS function — fetches `/api/annonces/${id}/history`, renders 7-column table (`scraped_at`, `status`, `prix`, `titre`, `list_id`, `superficie`, `prix_m2`), applies `cell-changed` class where consecutive snapshot values differ (`String()` comparison handles null gracefully). Reuses existing `fmtDateTime()`, `fmt()`, `escHtml()` helpers.
- Task 7: Added `closeModal()` function; bound `#modalClose` click, overlay background click (checks `e.target === this`), and `document` keydown Escape — all bound once at init, after `loadData()`.
- Task 6: Added `.hist-btn` click handler inside `bindRowEvents()` with `e.stopPropagation()` to prevent row checkbox interference.
- Template validation: Rendered template via Flask test context — all 10 key elements confirmed present.

### File List

- `web.py` — modified: `get_annonces()` SELECT query updated to add `history_count` subquery with table alias `a`; `ensure_columns()` wrapped in try/finally for connection safety
- `templates/index.html` — modified: CSS block (modal + hist-btn), `<th>Historique</th>`, trigger cell in tbody, modal HTML div, `openHistoryModal()` (with try/catch + res.ok guard) + `closeModal()` JS functions, `fmtDateTime()` helper for full timestamp display, `.hist-btn` binding in `bindRowEvents()`, modal close handlers at init
- `tests/test_web_api.py` — modified: 3 new test functions for `history_count` field
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — modified: story status updated
- `.gitignore` — created: excludes `*.db` and Python artifacts
