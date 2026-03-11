# Story 2.1: Updated Listings API Response

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a web UI consumer,
I want the `GET /api/annonces` endpoint to include `status`, `first_seen`, and `date_publication` in each listing object,
so that the frontend has everything it needs to render status badges and dates without a second API call.

## Acceptance Criteria

### AC1: New fields present in response

**Given** at least one listing exists in `annonces`
**When** `GET /api/annonces` is called
**Then** each listing object in the JSON array includes `status`, `first_seen`, and `date_publication` fields

### AC2: Status value is lowercase string literal

**Given** a listing with `status = 'new'`
**When** returned by the API
**Then** `"status": "new"` appears in the JSON object — lowercase string, no enum wrapping (architecture: status values are TEXT literals)

### AC3: NULL date_publication serializes to null (not crash/omission)

**Given** a listing where `date_publication` is `NULL` in the DB
**When** returned by the API
**Then** `"date_publication": null` appears in the JSON — no crash, no omitted key (NFR8)

### AC4: Existing fields are unchanged (non-regression)

**Given** all fields already returned by `GET /api/annonces` before this story:
`id`, `titre`, `prix`, `superficie`, `prix_m2`, `trajet`, `lien`,
`viabilise`, `emprise_sol`, `partiellement_constructible`, `partiellement_agricole`,
`analyse_faite`, `nogo`, `note`
**When** the SELECT query is updated
**Then** all these fields remain present and identical in every response (FR12)

---

## Tasks / Subtasks

- [x] Task 1: Update `GET /api/annonces` SELECT query in `web.py` (AC: #1, #2, #3, #4)
  - [x] Add `status`, `first_seen`, `date_publication` to the SELECT column list at `web.py:72`
  - [x] Preserve all 14 existing columns verbatim — no reordering, no removals

- [x] Task 2: Write tests in `tests/test_web_api.py` (AC: #1–#4)
  - [x] Test: GET /api/annonces with listing that has status='new' → response includes `status`, `first_seen`, `date_publication`
  - [x] Test: date_publication=None in DB → JSON contains `"date_publication": null`
  - [x] Test: All 14 pre-existing fields are present in response (non-regression)
  - [x] Test: status value is a lowercase string (not an int, not None)

---

## Dev Notes

### What This Story Does and Does NOT Include

**Does:**
- Add 3 column names to the SELECT in `get_annonces()` in `web.py` — that's the entire code change
- Create `tests/test_web_api.py` with Flask test client tests for the endpoint

**Does NOT:**
- Add any new endpoint (Story 2.3)
- Modify `templates/index.html` (Story 2.2)
- Change any PATCH/DELETE endpoints
- Add `status` or the new fields to `EDITABLE_FIELDS` — they are read-only fields

### Critical: Exact Change Required

**Current `get_annonces()` in `web.py` (lines 69–78):**
```python
@app.route("/api/annonces", methods=["GET"])
def get_annonces():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, titre, prix, superficie, prix_m2, trajet, lien, "
        "viabilise, emprise_sol, partiellement_constructible, partiellement_agricole, "
        "analyse_faite, nogo, note "
        "FROM annonces ORDER BY id"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
```

**Replace the SELECT string with** (add 3 fields before `FROM`):
```python
    rows = conn.execute(
        "SELECT id, titre, prix, superficie, prix_m2, trajet, lien, "
        "viabilise, emprise_sol, partiellement_constructible, partiellement_agricole, "
        "analyse_faite, nogo, note, "
        "status, first_seen, date_publication "
        "FROM annonces ORDER BY id"
    ).fetchall()
```

**Nothing else in `web.py` changes.** One line modified (the `note "` string becomes `note, "`), one line added.

### Critical: NULL Handling is Free

`sqlite3.Row` + `dict(r)` + Flask's `jsonify` automatically serialize SQLite `NULL` → Python `None` → JSON `null`. No special handling needed. AC3 is satisfied by the existing response pattern.

### Critical: Status Values Are Already Correct

The `status` column contains lowercase string literals (`'new'`, `'price_changed'`, `'reposted'`, `'unchanged'`) written by `save_or_merge` in `database.py`. No transformation needed in `web.py`. AC2 is satisfied by the data layer.

### Critical: Flask Test Client Pattern (No Existing Template)

No existing `tests/test_web_api.py` exists — this story creates it. Use Flask's built-in test client. Important: `web.py` calls `ensure_columns()` inside `with app.app_context():` at import time — this will fail if `lbc_data.db` (the hardcoded `DB_NAME`) doesn't exist. **Override `DB_NAME` or use monkeypatching** to avoid touching the production DB.

**Recommended pattern:**
```python
import os
import sqlite3
import tempfile

import pytest

# Must override DB_NAME BEFORE importing web
import database  # initialize schema helper

@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    # Initialize schema via save_or_merge (idempotent)
    database.save_or_merge([], db_name=db_path)

    import web
    web.DB_NAME = db_path  # patch before test client is created
    web.app.config["TESTING"] = True
    with web.app.test_client() as c:
        yield c, db_path
```

**Alternatively**, use `monkeypatch` to patch `web.DB_NAME` before the request:
```python
def test_get_annonces_returns_new_fields(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    database.save_or_merge([...], db_name=db_path)
    monkeypatch.setattr(web, "DB_NAME", db_path)
    web.app.config["TESTING"] = True
    with web.app.test_client() as client:
        response = client.get("/api/annonces")
        ...
```

**Warning:** `web.py` calls `ensure_columns()` at module import time inside `with app.app_context()`. This runs once when the module is first imported and uses `DB_NAME` at that point. If `lbc_data.db` doesn't exist at test time, `ensure_columns()` will raise. Use `try/except` in your fixture setup, or ensure the test DB is initialized before `import web`.

**Practical approach** — import `web` at top of test file with a guard:
```python
import web  # triggers ensure_columns() on lbc_data.db at import
```
This is acceptable in CI since `lbc_data.db` may or may not exist. The `ensure_columns()` function catches `sqlite3.OperationalError` already. Just ensure `web` is imported after project root is on `sys.path`.

### Critical: DB Connection Architecture in web.py

`web.py` uses `get_db()` helper that creates a new `sqlite3.connect(DB_NAME)` per request — NOT a shared connection. `DB_NAME` is a module-level constant (`"lbc_data.db"`). To redirect to test DB, patch `web.DB_NAME` with `monkeypatch.setattr` before making requests.

```python
def get_db():
    conn = sqlite3.connect(DB_NAME)  # reads DB_NAME at call time — patchable
    conn.row_factory = sqlite3.Row
    return conn
```

### Testing: Pre-populate DB for Assertions

Insert a test listing via `database.save_or_merge` to ensure `status` / `first_seen` are populated correctly (not NULL) before calling the API:

```python
sample = {
    "titre": "Terrain test",
    "prix": 50000.0, "superficie": 500.0, "prix_m2": 100.0,
    "trajet": "15 min",
    "lien": "https://www.leboncoin.fr/ad/1",
    "lat": 43.6, "lng": 1.4,
    "date_publication": "2024-01-01T10:00:00",
    "list_id": "1000001",
}
database.save_or_merge([sample], db_name=db_path)
# → row inserted with status='new', first_seen=<iso timestamp>
```

For `date_publication=NULL` test, insert a row with `date_publication=None`.

### Non-regression: Field List Reference

The following 14 fields were returned by the endpoint before this story. ALL must remain in the response:

| Field | Type |
|-------|------|
| `id` | INTEGER |
| `titre` | TEXT |
| `prix` | REAL |
| `superficie` | REAL |
| `prix_m2` | REAL |
| `trajet` | TEXT |
| `lien` | TEXT |
| `viabilise` | INTEGER (0/1/null) |
| `emprise_sol` | REAL |
| `partiellement_constructible` | INTEGER |
| `partiellement_agricole` | INTEGER |
| `analyse_faite` | INTEGER |
| `nogo` | INTEGER |
| `note` | INTEGER |

### Architecture Compliance

Per [architecture.md — API Patterns](../../planning-artifacts/architecture.md#api--communication-patterns):
- Response is a **bare JSON array** — no `{"data": [...]}` wrapper ✓ (already the case)
- JSON keys are **snake_case** matching DB column names ✓ (sqlite3.Row + dict() handles this)
- Typed path params for ID routes ✓ (N/A for GET /api/annonces)

Per [architecture.md — Format Patterns](../../planning-artifacts/architecture.md#format-patterns):
- Nullable fields: `NULL` in DB → `None` in Python → `null` in JSON ✓ (automatic via sqlite3)
- Status values: lowercase string literals — `'new'`, `'price_changed'`, etc. ✓ (stored that way by save_or_merge)

Per [architecture.md — Structure Patterns](../../planning-artifacts/architecture.md#structure-patterns):
- `web.py`: Flask routes only — no business logic ✓ (this story is purely a SELECT column change)
- DB queries stay in `web.py` route functions ✓

### Project Structure Notes

**Files to modify:**
- `web.py` — 1 line changed in `get_annonces()` SELECT query

**New test file:**
- `tests/test_web_api.py`

**Files NOT touched:**
- `templates/index.html` (Story 2.2)
- `database.py` (complete — Epic 1 done)
- `matcher.py` (complete)
- All other files

### Previous Story Intelligence (Epic 1 Completion)

Epic 1 is fully done. Key facts for this story:

**`save_or_merge` guarantees (database.py):**
- Every INSERT writes `status='new'`, `first_seen=datetime.now().isoformat()`
- Every UPDATE writes the new `status` value (`price_changed`, `reposted`, `unchanged`)
- `list_id`, `lat`, `lng`, `date_publication` are all persisted on INSERT
- `date_publication` can be `None`/`NULL` (NFR8)

**Schema state after Epic 1:**
- `annonces` has all required columns: `status TEXT`, `first_seen TEXT`, `date_publication TEXT`, `list_id TEXT`, `lat REAL`, `lng REAL` — confirmed by passing test suite (65 tests)
- `annonces_history` exists with matching columns

**Test patterns established in Epic 1:**
- `tempfile.mkstemp(suffix=".db")` for isolated test DBs → use `tmp_path` pytest fixture (equivalent, cleaner)
- `database.save_or_merge([], db_name=path)` as schema initializer
- Direct `sqlite3.connect(path).execute(...)` for assertions

### FRs and NFRs Covered

| Requirement | Description |
|-------------|-------------|
| FR15 | GET /api/annonces includes status → feeds Story 2.2 badge rendering |
| FR16 | status='new' available in response |
| FR17 | date_publication and first_seen available in response |
| FR12 | All existing fields still present — no interface regression |
| NFR8 | date_publication=NULL → null in JSON (no crash) |

### References

- [web.py:68-78](../../web.py) — `get_annonces()` function to modify
- [architecture.md — API Boundaries](../../planning-artifacts/architecture.md#api-boundaries) — response shape contract
- [architecture.md — Format Patterns](../../planning-artifacts/architecture.md#format-patterns) — snake_case, bare arrays, nullable handling
- [Story 1.4 completion notes](1-4-save-or-merge-integration.md#completion-notes-list) — status values confirmed, schema confirmed
- [Epics: Story 2.1](../../planning-artifacts/epics.md#story-21-updated-listings-api-response) — acceptance criteria source

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Task 1: Added `status`, `first_seen`, `date_publication` to the SELECT query in `get_annonces()` (`web.py:74-75`). One line changed (`note "` → `note, "`), one line added. No other changes.
- Task 2: Created `tests/test_web_api.py` with 4 tests covering AC1–AC4. Flask test client pattern with `monkeypatch.setattr(web, "DB_NAME", db_path)` used to isolate test DB. All 69 tests pass (65 pre-existing + 4 new), zero regressions.
- AC3 (NULL date_publication → JSON null) confirmed free via sqlite3.Row + dict() + jsonify chain.
- AC2 (status lowercase string) confirmed via `database.save_or_merge` writing `'new'` on INSERT.
- [Code Review] M1 fixed: `sprint-status.yaml` added to File List.
- [Code Review] M2 fixed: `ensure_columns()` extended with `status`, `first_seen`, `date_publication` columns — prevents OperationalError on old DBs.
- [Code Review] M3 fixed: `ensure_columns()` call guarded with `os.path.exists(DB_NAME)` — prevents creation of empty `lbc_data.db` as test side effect.
- [Code Review] M4 fixed: `get_annonces()` now wraps query in `try/finally` to guarantee connection close on exception.

### File List

- `web.py` — modified: SELECT extended with new fields; `ensure_columns()` covers new columns; `os.path.exists` guard added; `get_annonces()` uses `try/finally`
- `tests/test_web_api.py` — created: 4 tests for AC1–AC4
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — modified: story status set to `review`
