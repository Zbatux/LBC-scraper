# Story 2.3: History API Endpoint

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the history modal,
I want `GET /api/annonces/<id>/history` to return the full chronological snapshot list for a listing,
so that the frontend can render the complete change log without any additional queries.

## Acceptance Criteria

### AC1: Chronological snapshot array for listing with history

**Given** a listing with one or more rows in `annonces_history`
**When** `GET /api/annonces/<id>/history` is called with a valid integer ID
**Then** a JSON array of all snapshot rows is returned, ordered by `scraped_at` ASC (FR19)

### AC2: Full snapshot columns in each object

**Given** the JSON array returned
**Then** each object contains `scraped_at`, `annonce_id`, and all snapshot columns (FR21)
(Full column list: `id`, `annonce_id`, `scraped_at`, `titre`, `prix`, `superficie`, `prix_m2`,
`trajet`, `lien`, `unique_key`, `description`, `viabilise`, `emprise_sol`,
`partiellement_constructible`, `partiellement_agricole`, `analyse_faite`, `nogo`, `note`,
`lat`, `lng`, `status`, `first_seen`, `date_publication`, `list_id`)

### AC3: Empty array for listing with no history

**Given** a listing that exists in `annonces` but has no history rows in `annonces_history`
**When** the endpoint is called with that listing's valid integer ID
**Then** an empty JSON array `[]` is returned (no 404, no crash)

### AC4: 404 for non-integer or non-existent ID

**Given** a non-integer value in the path (e.g., `/api/annonces/abc/history`)
**When** the endpoint is called
**Then** Flask returns 404 automatically — the typed `<int:annonce_id>` path param handles this

**Given** a valid integer ID that does not exist in `annonces`
**When** the endpoint is called
**Then** Flask returns 404 with `{"error": "not found"}`

### AC5: Bare JSON array — no response wrapper

**Given** the response shape
**Then** it is a bare JSON array `[{...}, ...]` — not wrapped in `{"data": [...]}` or any object

---

## Tasks / Subtasks

- [x] Task 1: Add `GET /api/annonces/<int:annonce_id>/history` route to `web.py` (AC: #1, #2, #3, #4, #5)
  - [x] Add route decorated with `@app.route("/api/annonces/<int:annonce_id>/history", methods=["GET"])`
  - [x] Check if `annonce_id` exists in `annonces` table; if not, return `jsonify({"error": "not found"}), 404`
  - [x] Query `annonces_history` with `WHERE annonce_id = ? ORDER BY scraped_at ASC`
  - [x] Return `jsonify([dict(r) for r in rows])` (bare array, using sqlite3.Row → dict pattern)
  - [x] Use `try/finally` for DB connection cleanup (existing pattern)

- [x] Task 2: Add tests for the new endpoint to `tests/test_web_api.py` (AC: #1, #2, #3, #4, #5)
  - [x] Add `import sqlite3` at the top of `test_web_api.py` (required — tests call `sqlite3.connect()` directly)
  - [x] `test_history_returns_snapshots_ordered_asc`: insert listing + 2 history rows, verify ASC order and presence of key columns (`annonce_id`, `scraped_at`, `titre`, `prix`, `status`, `list_id`) — covers AC1 + AC2
  - [x] `test_history_returns_empty_for_listing_with_no_history`: insert listing without history, verify status 200 + `data == []` + `isinstance(data, list)` — covers AC3 + AC5
  - [x] `test_history_returns_404_for_nonexistent_id`: verify status 404 + `{"error": ...}` for unused integer ID — covers AC4 (non-existent)
  - [x] `test_history_noninteger_id_returns_404`: verify Flask auto-404 for `/api/annonces/abc/history` — covers AC4 (non-integer)

- [x] Task 3: Update `web.py` module docstring to include the new endpoint (AC: documentation)
  - [x] Add `GET /api/annonces/<id>/history → History snapshots for a listing` to the module docstring at top

---

## Dev Notes

### What This Story Does and Does NOT Include

**Does:**
- Add `GET /api/annonces/<int:annonce_id>/history` endpoint to `web.py`
- Add `import sqlite3` + 4 new test functions in `tests/test_web_api.py`
- Update the module docstring at the top of `web.py`

**Does NOT:**
- Modify `templates/index.html` — the modal UI is Story 2.4
- Modify `database.py` — `annonces_history` table and index already exist (Story 1.2 + 1.4 done)
- Add new Python dependencies
- Modify any other file

### Critical: Exact Implementation for `web.py`

**Insert location:** After the existing `get_annonces()` route (line 73–86), before `delete_annonces()`.

**Insert location for grouping:** Place the new route directly after `get_annonces()` to keep GET routes together. Flask resolves routes by URL pattern and HTTP method — there is no ordering conflict with the existing PATCH routes (`/api/annonces/<int:annonce_id>/history` and `/api/annonces/<int:annonce_id>` are distinct patterns with different segment counts, in addition to different methods).

**Exact implementation to add after `get_annonces()` in `web.py`:**

```python
@app.route("/api/annonces/<int:annonce_id>/history", methods=["GET"])
def get_annonce_history(annonce_id):
    conn = get_db()
    try:
        # Verify annonce exists (AC4: 404 for non-existent integer IDs)
        row = conn.execute("SELECT id FROM annonces WHERE id = ?", (annonce_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        rows = conn.execute(
            "SELECT * FROM annonces_history "
            "WHERE annonce_id = ? ORDER BY scraped_at ASC",
            (annonce_id,),
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])
```

**Why `SELECT *`:** The `annonces_history` table is a full-column snapshot by design (architecture).
All columns are relevant for the modal. Using `SELECT *` is safe here because: (1) it's read-only,
(2) column injection is impossible via the typed `<int:annonce_id>` path param, and (3) as history
columns evolve, the API response automatically includes new fields without endpoint changes.

**Why the existence check:** AC3 specifies `[]` for listing with no history (listing exists).
AC4 specifies 404 for non-existent IDs. These two behaviors require checking whether the annonce
itself exists before querying history. Without the check, a non-existent ID would also return `[]`,
conflating the two cases.

### Critical: `annonces_history` Schema (Confirmed from `database.py`)

```sql
CREATE TABLE IF NOT EXISTS annonces_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    annonce_id INTEGER,
    scraped_at TEXT,
    titre TEXT,
    prix REAL,
    superficie REAL,
    prix_m2 REAL,
    trajet TEXT,
    lien TEXT,
    unique_key TEXT,
    description TEXT,
    viabilise INTEGER,
    emprise_sol REAL,
    partiellement_constructible INTEGER,
    partiellement_agricole INTEGER,
    analyse_faite INTEGER DEFAULT 0,
    nogo INTEGER DEFAULT 0,
    note INTEGER,
    lat REAL,
    lng REAL,
    status TEXT,
    first_seen TEXT,
    date_publication TEXT,
    list_id TEXT  -- added via ALTER TABLE migration in save_or_merge
)
```

Index: `idx_history_annonce_id ON annonces_history(annonce_id)` — already exists (NFR4).
The `SELECT * ... WHERE annonce_id = ?` query hits this index, ensuring O(1) lookup.

### Critical: Flask Route for Non-Integer IDs

When using `<int:annonce_id>` as the path parameter type, Flask automatically returns **404** for
any non-integer value in the URL. No manual handling is needed. Example:
- `/api/annonces/abc/history` → Flask 404 (built-in, type mismatch)
- `/api/annonces/999/history` where 999 doesn't exist in `annonces` → Our explicit 404

### Critical: Module Docstring Update

The docstring at top of `web.py` currently lists 5 endpoints. Add the new one:

**Before (current docstring endpoints list):**
```
  GET  /                       → Sert l'UI (templates/index.html)
  GET  /api/annonces           → Retourne toutes les annonces en JSON
  DELETE /api/annonces         → Suppression bulk  { ids: [int, ...] }
  PATCH  /api/annonces/bulk    → Toggle bool bulk   { ids, field, value }
  PATCH  /api/annonces/<id>    → Mise à jour partielle d'une annonce
```

**After:**
```
  GET  /                               → Sert l'UI (templates/index.html)
  GET  /api/annonces                   → Retourne toutes les annonces en JSON
  GET  /api/annonces/<id>/history      → Snapshots historiques d'une annonce
  DELETE /api/annonces                 → Suppression bulk  { ids: [int, ...] }
  PATCH  /api/annonces/bulk            → Toggle bool bulk   { ids, field, value }
  PATCH  /api/annonces/<id>            → Mise à jour partielle d'une annonce
```

### Critical: Test Implementation Pattern

Follow the exact pattern from `tests/test_web_api.py` (Story 2.1):

```python
import sqlite3  # ADD this at top of test_web_api.py alongside existing imports


def test_history_returns_snapshots_ordered_asc(client):
    """AC1+AC2: History rows ordered by scraped_at ASC, all key columns present."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    annonce = conn.execute("SELECT id FROM annonces LIMIT 1").fetchone()
    annonce_id = annonce["id"]
    conn.execute(
        "INSERT INTO annonces_history (annonce_id, scraped_at, titre, prix, status, list_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (annonce_id, "2024-01-01T10:00:00", "Terrain test v1", 40000.0, "price_changed", "1000001")
    )
    conn.execute(
        "INSERT INTO annonces_history (annonce_id, scraped_at, titre, prix, status, list_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (annonce_id, "2024-02-01T10:00:00", "Terrain test v2", 45000.0, "price_changed", "1000001")
    )
    conn.commit()
    conn.close()

    response = c.get(f"/api/annonces/{annonce_id}/history")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    # AC1: chronological ASC order
    assert data[0]["scraped_at"] == "2024-01-01T10:00:00"
    assert data[1]["scraped_at"] == "2024-02-01T10:00:00"
    # AC2: key snapshot columns present (SELECT * returns all columns)
    for key in ("annonce_id", "scraped_at", "titre", "prix", "status", "list_id"):
        assert key in data[0], f"Missing column in history response: {key}"


def test_history_returns_empty_for_listing_with_no_history(client):
    """AC3+AC5: Listing exists but has no history → empty bare array, status 200."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    annonce = conn.execute("SELECT id FROM annonces LIMIT 1").fetchone()
    annonce_id = annonce["id"]
    conn.close()

    response = c.get(f"/api/annonces/{annonce_id}/history")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)   # AC5: bare array, NOT a dict
    assert data == []               # AC3: empty, not 404


def test_history_returns_404_for_nonexistent_id(client):
    """AC4: Non-existent integer ID → 404 with {"error": ...}."""
    c, db_path = client

    response = c.get("/api/annonces/99999/history")

    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_history_noninteger_id_returns_404(client):
    """AC4: Non-integer path value → Flask auto-404 (regression guard for <int:> param type)."""
    c, db_path = client

    response = c.get("/api/annonces/abc/history")

    assert response.status_code == 404
```

### Architecture Compliance

Per [architecture.md — API Boundaries](../../planning-artifacts/architecture.md#api-boundaries):
- Endpoint: `GET /api/annonces/<int:id>/history` ✓
- Path param: typed `<int:annonce_id>` prevents injection ✓
- Response: bare JSON array `[{...}]` — no wrapper ✓
- JSON keys: `snake_case` matching DB column names — `sqlite3.Row` serializes as-is ✓

Per [architecture.md — Structure Patterns](../../planning-artifacts/architecture.md#structure-patterns):
- `web.py`: Flask routes only — no business logic ✓ (query directly via `get_db()`)
- DB access: `get_db()` helper → `try/finally conn.close()` pattern ✓

Per [architecture.md — Format Patterns](../../planning-artifacts/architecture.md#format-patterns):
- Error response: `{"error": "not found"}` (not `{"message": ...}`, not `{"detail": ...}`) ✓
- Datetimes: already stored as ISO8601 TEXT — no transformation needed ✓

Per [architecture.md — Security](../../planning-artifacts/architecture.md#security):
- Read-only endpoint — no EDITABLE_FIELDS involved ✓
- `<int:annonce_id>` typed param — no column injection surface ✓

### Performance (NFR3)

The history modal must open within 500ms of click. The query is:
```sql
SELECT * FROM annonces_history WHERE annonce_id = ? ORDER BY scraped_at ASC
```
- Index `idx_history_annonce_id` on `annonce_id` → O(1) lookup (NFR4 ✓)
- For a typical listing, history will have < 20 snapshots → trivially fast
- All within `try/finally` with immediate `conn.close()` → no connection leak
- NFR3 (500ms) is easily met on localhost

### Previous Story Intelligence (Story 2.2)

Key confirmed facts from Story 2.2 completion:
- `web.py` uses `try/finally` for DB connection cleanup — confirmed pattern ✓
- `ensure_columns()` guarded with `os.path.exists(DB_NAME)` (M3 fix from Story 2.1 code review) — do not remove this guard ✓
- `templates/index.html` now has status badges, `first_seen`, `date_publication` columns, and status filter dropdown — this story does NOT touch index.html ✓
- `parsers.py` was modified (M1 from Story 2.2 code review): `parse_date_publication` now handles Unix timestamp integers ✓
- 4 existing tests pass in `tests/test_web_api.py` — the new tests must not break them ✓
- Story 2.4 (history modal JS) depends on this endpoint being correct — the AC2 column list is critical for 2.4's diff rendering ✓

### Git Intelligence (last 5 commits)

```
2e7f936 story 2-2 implemented  → templates/index.html: status badges, date cols, status filter, fmtDate, statusBadge
f0eba7d story 2-1 implemented  → web.py: GET /api/annonces SELECT updated; tests/test_web_api.py created
8c46b1e story 1-4 implemented  → database.py: save_or_merge, transactions, annonces_history writes
c5cfbd9 story 1-3 implemented  → parsers.py: lat, lng, date_publication extraction
d1ca5ef Story 1-2 implemented  → database.py: schema migrations, annonces_history table, idx_history_annonce_id
```

Pattern: one commit per story. This story's commit will be `story 2-3 implemented`.

### Project Structure Notes

**File to modify:**
- `web.py` — add 1 route function, update module docstring

**File to modify:**
- `tests/test_web_api.py` — add `import sqlite3` + 4 new test functions (5 test items total)

**Files NOT touched:**
- `database.py` — `annonces_history` schema complete (Epic 1 done)
- `templates/index.html` — modal UI deferred to Story 2.4
- `matcher.py`, `config.py`, `parsers.py`, `main.py` — all untouched

### References

- [web.py:1-13](../../web.py#L1) — module docstring to update
- [web.py:34-37](../../web.py#L34) — `get_db()` helper (use this for DB connections)
- [web.py:59-61](../../web.py#L59) — `ensure_columns()` guard pattern (do not modify)
- [web.py:73-86](../../web.py#L73) — `get_annonces()` (insert new route after this)
- [database.py:224-261](../../database.py#L224) — `annonces_history` CREATE TABLE + index definition
- [tests/test_web_api.py:1-122](../../tests/test_web_api.py#L1) — existing test patterns to follow
- [Epics: Story 2.3](../../planning-artifacts/epics.md#story-23-history-api-endpoint) — acceptance criteria source
- [architecture.md — API Boundaries](../../planning-artifacts/architecture.md#api-boundaries) — endpoint contract
- [architecture.md — Security](../../planning-artifacts/architecture.md#security) — typed path param safety

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Task 1: Added `get_annonce_history(annonce_id)` route to `web.py` after `get_annonces()`. Uses `try/finally` pattern for connection cleanup. Two-query approach: first verifies annonce existence (404 if missing), then queries `annonces_history` ordered `scraped_at ASC` with `SELECT *`. Flask's `<int:annonce_id>` typed param auto-handles non-integer paths.
- Task 2: Added `import sqlite3` to `tests/test_web_api.py` (required for direct DB manipulation in tests). Added 4 new test functions covering all 5 ACs. All 4 pass. Pre-existing failure in `test_parser_enrichment.py::test_coerces_non_string_to_string` is unrelated to Story 2.3 — it was introduced by Story 2.2's M1 fix to `parsers.py` and is out of scope.
- Task 3: Updated module docstring at top of `web.py` to include the new history endpoint.
- Test run: 72/73 pass (1 pre-existing failure in parsers unrelated to this story). 4 new Story 2.3 tests all pass.
- Code review (2026-03-11): 3 medium issues fixed. M1: AC2 column assertion in `test_history_returns_snapshots_ordered_asc` expanded from 6 to all 24 `annonces_history` columns. M2: `sprint-status.yaml` added to File List (was modified but undocumented). M3: `ensure_columns()` in `web.py` now creates `annonces_history` table and index — prevents `OperationalError` on pre-Story-1.2 DBs. All 8 web API tests pass.

### File List

- `web.py` — modified: added `get_annonce_history()` route + updated module docstring + `ensure_columns()` now creates `annonces_history` table (code review fix)
- `tests/test_web_api.py` — modified: added `import sqlite3` + 4 new test functions; AC2 column assertion expanded to all 24 columns (code review fix)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — modified: story status updated

---

### Senior Developer Review (AI) — Pre-Implementation Story Review

**Date:** 2026-03-11
**Reviewer:** claude-sonnet-4-6 (adversarial story review)
**Outcome:** Story corrected — ready for dev

**Issues fixed (5 total):**
- **H1** (Story Tasks): Added explicit `import sqlite3` subtask to Task 2 — was only in a note, would have caused `NameError` in all tests
- **H2** (Story Tests): Strengthened `test_history_returns_snapshots_ordered_asc` to assert presence of key columns (`annonce_id`, `scraped_at`, `titre`, `prix`, `status`, `list_id`) — previously only checked 2 fields, leaving AC2 unvalidated
- **M1** (Story Tests): Added `test_history_noninteger_id_returns_404` to cover the non-integer path case of AC4; removed redundant `test_history_response_is_bare_array` and folded its `isinstance(data, list)` check into `test_history_returns_empty_for_listing_with_no_history`
- **M2** (Story Tests): Consolidated AC5 (bare array check) into `test_history_returns_empty_for_listing_with_no_history` — reduced duplication
- **M3** (Story Notes): Removed incorrect "Route registration order matters" note that falsely implied Flask routing ambiguity; replaced with accurate explanation
