# Story 1.4: Save-or-Merge Integration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the scrape pipeline,
I want `save_or_merge` in `database.py` to run fuzzy matching, snapshot changes, and assign statuses atomically,
so that each `--scrape` run produces an accurate market state and complete change history with no risk of partial writes.

## Acceptance Criteria

### AC1: Fuzzy match with changed data → snapshot + update + status

**Given** a scraped listing with valid GPS+area that fuzzy-matches an existing DB record AND at least one data field has changed
**When** `save_or_merge` runs
**Then** a full-column snapshot of the *previous* state is written to `annonces_history`, the `annonces` row is updated with the latest values, and status is set to `price_changed` (if `prix` differs) or `reposted` (if `list_id` differs) — see AC4 for reposted details

### AC2: Fuzzy match with identical data → unchanged, no snapshot

**Given** a scraped listing that fuzzy-matches an existing DB record and all data fields are identical
**When** `save_or_merge` runs
**Then** `status` is set to `unchanged`, no `annonces_history` row is written, and no unnecessary UPDATE is executed

### AC3: No GPS or no match → INSERT as new

**Given** a scraped listing with no GPS data (lat/lng = None) OR no fuzzy match in the DB
**When** `save_or_merge` runs
**Then** the listing is inserted as a new `annonces` row with `status = 'new'` and `first_seen = datetime.now().isoformat()`

### AC4: Repost detection via list_id

**Given** a scraped listing whose GPS+area fuzzy-matches an existing DB record but has a different `list_id` (the Leboncoin ad identifier)
**When** `save_or_merge` runs
**Then** `status` is set to `'reposted'` and the main record's `list_id` is updated to the new value (along with all other changed fields)

### AC5: Atomic write — no partial snapshots (NFR5)

**Given** a `--scrape` run that is interrupted mid-way (keyboard interrupt or crash)
**When** the DB is inspected immediately after
**Then** all changes are either fully committed or fully absent — no partial `annonces_history` rows (single SQLite transaction with rollback)

### AC6: main.py compatibility — no interface change (FR12–13)

**Given** the existing `save_to_database` call in `main.py`
**When** this story is deployed
**Then** `main.py` imports and calls `save_or_merge(rows)` with the same `rows` argument — no other change to `main.py`'s interface, flags, or output messages required

---

## Tasks / Subtasks

- [x] Task 1: Update `process()` in `database.py` to include `list_id` in the output dict (AC: #4)
  - [x] Add `list_id = str(ad.get("list_id", ""))` extraction
  - [x] Add `"list_id": list_id` key to `rows.append({...})`

- [x] Task 2: Add schema migrations for `list_id` column (AC: #4)
  - [x] Add `"ALTER TABLE annonces ADD COLUMN list_id TEXT"` to the migrations list in `save_to_database` (preserving existing function for reference) — **AND** in the new `save_or_merge` schema init block
  - [x] Add `"ALTER TABLE annonces_history ADD COLUMN list_id TEXT"` migration (history table already exists — use try/except pattern)

- [x] Task 3: Implement `save_or_merge(data, db_name="lbc_data.db")` in `database.py` (AC: #1–#5)
  - [x] Open a single SQLite connection with `conn.row_factory = sqlite3.Row` to allow column-name access
  - [x] Run schema init: CREATE TABLE IF NOT EXISTS + all migrations (same block as `save_to_database` + `list_id` additions) — this ensures `save_or_merge` is self-contained and idempotent
  - [x] Load all DB candidates with lat/lng in ONE query before the loop: `SELECT id, lat, lng, superficie FROM annonces WHERE lat IS NOT NULL AND lng IS NOT NULL`
  - [x] For each incoming listing:
    - [x] Call `matcher.find_match(lat, lng, area, candidates)` → `matched_id | None`
    - [x] **If match found (`matched_id`):**
      - [x] Load full matched row: `SELECT * FROM annonces WHERE id = ?`
      - [x] Determine status: if `list_id` differs → `'reposted'`; elif `prix` differs → `'price_changed'`; else → `'unchanged'`
      - [x] If status != `'unchanged'`: write snapshot row to `annonces_history` (all `annonces` columns + `scraped_at`, `annonce_id`)
      - [x] If status != `'unchanged'`: UPDATE `annonces` row with all incoming values + new status
      - [x] If status == `'unchanged'`: SET `status = 'unchanged'` only (no snapshot, no UPDATE of data fields)
    - [x] **If no match (`matched_id` is None):**
      - [x] INSERT new row with `status = 'new'`, `first_seen = datetime.now().isoformat()`, all fields
      - [x] Use `INSERT OR IGNORE` with `unique_key` constraint as fallback dedup for GPS-less listings
  - [x] Wrap ALL operations in a single transaction: `conn.commit()` at end, `conn.rollback()` in except, `conn.close()` in finally
  - [x] Import `matcher` at the top of `database.py`
  - [x] Import `datetime` at the top of `database.py`
  - [x] Return `nouvelles` count (number of new inserts, for main.py summary display)

- [x] Task 4: Update `main.py` to use `save_or_merge` (AC: #6)
  - [x] Change import: `from database import process, save_or_merge`
  - [x] Change call: `nouvelles = save_or_merge(rows)` (replacing `save_to_database(rows)`)

- [x] Task 5: Write tests in `tests/test_save_or_merge.py` (AC: #1–#5)
  - [x] Test: new listing (no GPS match) → `status='new'`, `first_seen` set, row inserted
  - [x] Test: GPS match + prix changed → `status='price_changed'`, snapshot in history, annonces row updated
  - [x] Test: GPS match + list_id different → `status='reposted'`, snapshot in history
  - [x] Test: GPS match + data identical → `status='unchanged'`, no history row
  - [x] Test: GPS=None listing → `status='new'` (no match attempted)
  - [x] Test: atomicity — simulate exception mid-loop → no partial history rows (use monkeypatch/mock)
  - [x] Test: `list_id` is persisted to DB on INSERT
  - [x] Test: `lat`, `lng`, `date_publication` persisted to DB on INSERT
  - [x] Test: schema migration idempotency (run save_or_merge twice on same DB → no error)

---

## Dev Notes

### What This Story Does and Does NOT Include

**Does:**
- Implement `save_or_merge` in `database.py` — the core match/snapshot/status engine
- Add `list_id` extraction in `process()` (minor output dict addition)
- Add schema migrations for `list_id` on both `annonces` and `annonces_history`
- Update `main.py` call from `save_to_database` to `save_or_merge`
- Persist `lat`, `lng`, `date_publication`, `list_id`, `status`, `first_seen` to `annonces` on INSERT

**Does NOT:**
- Remove `save_to_database` — keep it in `database.py` (backward-compat for any direct callers)
- Modify `web.py` or `templates/index.html` (Epic 2)
- Change `matcher.py` (already complete from Story 1.1)
- Change `parsers.py` (already complete from Story 1.3)
- Add new CLI arguments to `main.py`

### Critical: Current State After Stories 1.1–1.3

**`database.py` current INSERT** (`save_to_database`):
```python
cursor.execute('''
    INSERT INTO annonces (titre, prix, superficie, prix_m2, trajet, lien, unique_key)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', (annonce.get("titre"), ...))
```
**Problem:** `lat`, `lng`, `date_publication`, `status`, `first_seen` are NOT written to the DB today. `save_or_merge` must fix this for all INSERT and UPDATE paths.

**`process()` current output dict** (after Story 1.3):
```python
{"titre", "prix", "superficie", "prix_m2", "trajet", "lien", "lat", "lng", "date_publication"}
```
**Add:** `"list_id"` key (Task 1 above).

**`matcher.py`** — fully implemented. Interface:
```python
find_match(lat: float, lng: float, area: float, candidates: list[dict]) -> int | None
```
`candidates` dicts must have keys: `id`, `lat`, `lng`, `superficie`.

**`annonces` schema after Story 1.2** — all columns present including `lat`, `lng`, `status`, `first_seen`, `date_publication`. Add `list_id TEXT` migration.

**`annonces_history` schema after Story 1.2** — mirrors all `annonces` columns including `lat`, `lng`, `status`, `first_seen`, `date_publication`. Add `list_id TEXT` migration (same try/except pattern).

### Critical: save_or_merge Architecture

```python
import matcher
from datetime import datetime

def save_or_merge(data, db_name="lbc_data.db"):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row  # enables column-name access: row["prix"]
    try:
        cursor = conn.cursor()

        # Schema init (idempotent — same pattern as save_to_database)
        cursor.execute('''CREATE TABLE IF NOT EXISTS annonces (...)''')
        migrations = [...]  # include list_id TEXT
        for sql in migrations:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError:
                pass

        cursor.execute('''CREATE TABLE IF NOT EXISTS annonces_history (...)''')
        # history list_id migration:
        try:
            cursor.execute("ALTER TABLE annonces_history ADD COLUMN list_id TEXT")
        except sqlite3.OperationalError:
            pass
        cursor.execute("CREATE INDEX IF NOT EXISTS ...")

        # Load ALL GPS candidates ONCE before the loop (NFR4 - no O(n²))
        cursor.execute(
            "SELECT id, lat, lng, superficie FROM annonces "
            "WHERE lat IS NOT NULL AND lng IS NOT NULL"
        )
        candidates = [dict(row) for row in cursor.fetchall()]

        nouvelles = 0
        scraped_at = datetime.now().isoformat()  # consistent timestamp for this run

        for annonce in data:
            unique_key = generate_unique_key(annonce)
            lat = annonce.get("lat")
            lng = annonce.get("lng")
            area = annonce.get("superficie")

            matched_id = matcher.find_match(lat, lng, area, candidates)

            if matched_id is not None:
                # Load full existing row
                cursor.execute("SELECT * FROM annonces WHERE id = ?", (matched_id,))
                existing = cursor.fetchone()

                # Determine status
                incoming_list_id = annonce.get("list_id", "")
                existing_list_id = existing["list_id"] or ""
                if incoming_list_id and incoming_list_id != existing_list_id:
                    status = 'reposted'
                elif existing["prix"] != annonce.get("prix"):
                    status = 'price_changed'
                else:
                    # Check all other trackable fields
                    changed = any(
                        existing[f] != annonce.get(f)
                        for f in ("titre", "superficie", "lien")
                    )
                    status = 'price_changed' if changed else 'unchanged'

                if status != 'unchanged':
                    # Snapshot previous state
                    cursor.execute('''
                        INSERT INTO annonces_history (
                            annonce_id, scraped_at,
                            titre, prix, superficie, prix_m2, trajet, lien,
                            unique_key, description, viabilise, emprise_sol,
                            partiellement_constructible, partiellement_agricole,
                            analyse_faite, nogo, note,
                            lat, lng, status, first_seen, date_publication, list_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (matched_id, scraped_at,
                          existing["titre"], existing["prix"], existing["superficie"],
                          existing["prix_m2"], existing["trajet"], existing["lien"],
                          existing["unique_key"], existing["description"],
                          existing["viabilise"], existing["emprise_sol"],
                          existing["partiellement_constructible"], existing["partiellement_agricole"],
                          existing["analyse_faite"], existing["nogo"], existing["note"],
                          existing["lat"], existing["lng"], existing["status"],
                          existing["first_seen"], existing["date_publication"],
                          existing["list_id"]))

                    # Update row with new values + new status
                    cursor.execute('''
                        UPDATE annonces SET
                            titre=?, prix=?, superficie=?, prix_m2=?, trajet=?, lien=?,
                            lat=?, lng=?, date_publication=?, status=?, list_id=?
                        WHERE id=?
                    ''', (annonce.get("titre"), annonce.get("prix"),
                          annonce.get("superficie"), annonce.get("prix_m2"),
                          annonce.get("trajet"), annonce.get("lien"),
                          lat, lng, annonce.get("date_publication"),
                          status, annonce.get("list_id", ""), matched_id))
                else:
                    # Mark as unchanged
                    cursor.execute(
                        "UPDATE annonces SET status=? WHERE id=?",
                        ('unchanged', matched_id)
                    )

            else:
                # No match → INSERT as new
                try:
                    cursor.execute('''
                        INSERT INTO annonces (
                            titre, prix, superficie, prix_m2, trajet, lien,
                            unique_key, lat, lng, date_publication,
                            status, first_seen, list_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        annonce.get("titre"), annonce.get("prix"),
                        annonce.get("superficie"), annonce.get("prix_m2"),
                        annonce.get("trajet"), annonce.get("lien"),
                        unique_key, lat, lng,
                        annonce.get("date_publication"),
                        'new', datetime.now().isoformat(),
                        annonce.get("list_id", "")
                    ))
                    nouvelles += 1
                    # Add new insert to candidates if it has GPS (for within-run dedup)
                    if lat is not None and lng is not None:
                        candidates.append({
                            "id": cursor.lastrowid,
                            "lat": lat, "lng": lng,
                            "superficie": area
                        })
                except sqlite3.IntegrityError:
                    pass  # unique_key collision (GPS-less dedup fallback)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return nouvelles
```

### Critical: list_id Extraction in process()

Add to `process()` in `database.py`:
```python
# Inside the loop, after existing field extractions:
list_id = str(ad.get("list_id", ""))

# In rows.append({...}):
"list_id": list_id,
```

`list_id` in the raw LBC JSON is an integer (e.g., `2943421601`). Cast to `str` for consistency with `lien` URL and TEXT storage in SQLite.

### Critical: Within-Run Duplicate Guard

After inserting a new GPS-bearing listing, immediately append it to `candidates`. This prevents the same physical parcel appearing twice in the same scrape from being inserted twice:
```python
if lat is not None and lng is not None:
    candidates.append({
        "id": cursor.lastrowid,
        "lat": lat, "lng": lng,
        "superficie": area
    })
```

### Critical: unique_key Column UNIQUE Constraint as Safety Net

The `annonces.unique_key` has a `UNIQUE` constraint (original schema). For GPS-less listings with no fuzzy match, the `INSERT OR IGNORE` (or `try/except IntegrityError`) fallback ensures we never create exact duplicate listings (same titre+superficie hash). This is backward-compatible with the existing `save_to_database` dedup logic.

### Critical: conn.row_factory = sqlite3.Row

Using `sqlite3.Row` is essential to access existing row columns by name (`existing["prix"]`). Without it, `cursor.fetchone()` returns a plain tuple where column access requires position indices — extremely fragile and error-prone.

### Critical: main.py Update

**Current import in `main.py` (line 9):**
```python
from database import process, save_to_database
```
**Replace with:**
```python
from database import process, save_or_merge
```

**Current call in `main.py` (line 96):**
```python
nouvelles = save_to_database(rows)
```
**Replace with:**
```python
nouvelles = save_or_merge(rows)
```

These are the **only two changes to main.py**. The `nouvelles` return value and all existing summary print statements remain unchanged.

### Critical: annonces_history list_id Migration

`annonces_history` was created in Story 1.2 and already exists in the DB. To add `list_id`:
```python
try:
    cursor.execute("ALTER TABLE annonces_history ADD COLUMN list_id TEXT")
except sqlite3.OperationalError:
    pass  # column already exists (idempotent)
```
This must run inside `save_or_merge`'s schema init block, after the `CREATE TABLE IF NOT EXISTS annonces_history` statement.

### Status Value Reference

| Status | Trigger |
|--------|---------|
| `'new'` | No fuzzy GPS match AND no unique_key collision |
| `'price_changed'` | Fuzzy match found, `prix` differs (or other data differs) |
| `'reposted'` | Fuzzy match found, `list_id` differs |
| `'unchanged'` | Fuzzy match found, all data identical |

All status values are lowercase string literals stored as TEXT in SQLite. Never use integers.

### Testing Approach

Use `tempfile.mkstemp()` for isolated SQLite DBs (established pattern from Story 1.2):
```python
import tempfile, os
import database

def make_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path
```

**Candidates structure for mock inserts:**
```python
# Pre-populate a "known" listing in the DB for match testing
sample_row = {
    "titre": "Terrain test", "prix": 50000.0, "superficie": 500.0,
    "prix_m2": 100.0, "trajet": "15 min", "lien": "https://www.leboncoin.fr/ad/1",
    "lat": 43.6044622, "lng": 1.4442469, "date_publication": "2024-01-01T10:00:00",
    "status": "new", "first_seen": "2024-01-01T10:00:00", "list_id": "1000001",
    "unique_key": "abc123"
}
```

**Mock `drive_time` and `get_existing_trajets`** when calling `process()`, or call `save_or_merge` directly with pre-constructed rows (bypassing `process()`).

**Atomicity test:**
```python
from unittest.mock import patch

def test_atomicity_rollback(tmp_db):
    # Insert one row to DB manually, then simulate a crash mid-save_or_merge
    # Verify no annonces_history row was written
    with patch("database.matcher.find_match", side_effect=[matched_id, Exception("crash")]):
        with pytest.raises(Exception):
            database.save_or_merge([row1, row2], db_name=tmp_db)
    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM annonces_history").fetchone()[0]
    conn.close()
    assert count == 0
```

### Previous Story Intelligence

**Story 1.1 (done):**
- `matcher.find_match(lat, lng, area, candidates) -> int | None` — fully tested, 25 tests pass
- `config.GPS_MATCH_THRESHOLD_M = 50`, `config.AREA_MATCH_THRESHOLD_PCT = 0.10`
- Pattern: pure functions, no DB access in matcher

**Story 1.2 (done):**
- `annonces` has all required columns: `lat`, `lng`, `status`, `first_seen`, `date_publication`
- `annonces_history` exists and mirrors all `annonces` columns (except `list_id` — added by this story)
- `idx_history_annonce_id` index exists
- 53 tests currently pass

**Story 1.3 (done — code review completed):**
- `process()` returns dict with: `titre, prix, superficie, prix_m2, trajet, lien, lat, lng, date_publication`
- `get_coords()` hardened: explicit `float()` cast, `ValueError`/`TypeError` guard
- Bug fix: `if lat is not None and lng is not None:` (not `if lat and lng:`) — prevents falsy zero bug
- `parse_date_publication()` returns `str(val)` if truthy, `None` otherwise

**Git context (recent commits):**
- `c5cfbd9 story 1-3 implemented` — parsers.py and database.py enriched with lat/lng/date_publication
- `d1ca5ef Story 1-2 implemented` — schema migrations + annonces_history table
- `4b19125 implementation de la story 1-1` — matcher.py created

### Architecture Compliance

Per [architecture.md — Pipeline Integration](../../planning-artifacts/architecture.md#pipeline-integration):
- `save_or_merge` lives in `database.py` ✓
- `matcher.py` imported as stateless utility — no DB access in matcher ✓
- Single SQLite transaction wraps all snapshot + update/insert ops per scrape run (NFR5) ✓
- Load GPS candidates ONCE before the loop (NFR4 — no O(n²) pattern) ✓

Per [architecture.md — Process Patterns](../../planning-artifacts/architecture.md#process-patterns):
- All datetimes: `datetime.now().isoformat()` (ISO8601 TEXT) ✓
- Status values: lowercase string literals ✓
- Transaction pattern with rollback ✓

Per [architecture.md — Module Boundaries](../../planning-artifacts/architecture.md#architectural-boundaries):
- `database.py`: "All SQLite operations: schema, save, merge, history" ✓
- `matcher.py`: "does NOT do: DB access, Flask, I/O" ✓

**Do NOT:**
- Open DB connection inside `matcher.find_match` — pass candidates as list of dicts from the caller
- Use `datetime.now().strftime(...)` with non-ISO formats
- Use `status = 1` (use `status = 'new'`)
- Add `{"data": rows, ...}` response envelopes (N/A for this story)

### Project Structure Notes

**Files to modify:**
- `database.py` — add `save_or_merge` function + update `process()` for `list_id` + add `list_id` migration entries
- `main.py` — 2-line change: import + call site

**New test file:**
- `tests/test_save_or_merge.py`

**Files NOT touched:**
- `matcher.py` (complete)
- `parsers.py` (complete)
- `web.py` (Epic 2)
- `templates/index.html` (Epic 2)
- `config.py` (complete)
- `browser.py`, `descriptions.py`, `analyzer.py`, `exporter.py`, `routing.py` (unchanged throughout)

### FRs and NFRs Covered

| Requirement | Description |
|-------------|-------------|
| FR1 | Fuzzy GPS+area match logic in `save_or_merge` (via `matcher.find_match`) |
| FR2 | NULL GPS → no match attempted → insert as new |
| FR3 | Re-listed land (different list_id, same GPS+area) → `reposted` status, list_id updated |
| FR4 | Full-column snapshot written to `annonces_history` on change detection |
| FR5 | `scraped_at` timestamp on every history row (ISO8601) |
| FR6 | Multiple snapshots accumulate per listing over time |
| FR8 | `first_seen` set on INSERT only, never updated |
| FR9 | Status assigned: `new` / `price_changed` / `reposted` / `unchanged` |
| FR10 | UPDATE path writes latest scraped values to matched `annonces` row |
| FR11 | Matched-but-unchanged → `status = 'unchanged'`, no snapshot |
| FR12 | `main.py` call site changes by 2 lines only — all existing flags/output unchanged |
| FR13 | Fuzzy match + history + status run inside `--scrape` transparently |
| NFR1 | Candidates loaded once (O(n) not O(n²)), no visible scrape time regression |
| NFR4 | No O(n²) query pattern — single pre-loop candidate query |
| NFR5 | Single transaction with rollback — no partial history rows on crash |
| NFR6 | Schema init idempotent — `CREATE IF NOT EXISTS` + try/except migrations |
| NFR7 | Full DB drop + recreate → valid schema on next `--scrape` |
| NFR9 | GPS NULL → `find_match` returns None → INSERT as new, no crash |

### References

- [Architecture: Pipeline Integration](../../planning-artifacts/architecture.md#pipeline-integration) — scrape flow diagram
- [Architecture: Transaction Pattern](../../planning-artifacts/architecture.md#process-patterns) — NFR5 transaction code pattern
- [Architecture: Data Architecture](../../planning-artifacts/architecture.md#data-architecture) — schema column definitions
- [Architecture: Matcher Interface Contract](../../planning-artifacts/architecture.md#process-patterns) — `find_match` signature
- [Epics: Story 1.4](../../planning-artifacts/epics.md#story-14-save-or-merge-integration) — acceptance criteria
- [Story 1.1 completion notes](1-1-fuzzy-matcher-module.md#completion-notes-list) — matcher.py interface confirmed
- [Story 1.2 completion notes](1-2-database-schema-migration.md#completion-notes-list) — schema columns confirmed
- [Story 1.3 completion notes](1-3-parser-enrichment.md#completion-notes-list) — process() output dict confirmed, falsy zero fix

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — all 10 new tests passed after one test correction (within-run dedup test had wrong expected status: `reposted` is correct when list_ids differ, not `price_changed`).

### Completion Notes List

- Added `import matcher` and `from datetime import datetime` to `database.py` imports.
- Updated `process()` in `database.py`: added `list_id = str(ad.get("list_id") or "")` extraction and `"list_id": list_id` key to `rows.append({...})`. All 53 existing tests still pass.
- Added `"ALTER TABLE annonces ADD COLUMN list_id TEXT"` migration to `save_to_database` migrations list (backward-compat for existing DBs using old function).
- Implemented `save_or_merge(data, db_name)` in `database.py`:
  - `conn.row_factory = sqlite3.Row` for column-name access on existing rows.
  - Full idempotent schema init (CREATE IF NOT EXISTS + all migrations including `list_id`).
  - `ALTER TABLE annonces_history ADD COLUMN list_id TEXT` with try/except guard.
  - GPS candidates loaded once before loop (O(n), not O(n²) — NFR4).
  - Status logic: `reposted` (both list_ids non-empty and differ) > `price_changed` (prix differs or titre/superficie/lien/trajet differs) > `unchanged`.
  - Full-column snapshot to `annonces_history` on any status != `unchanged` (NFR5: single transaction with rollback).
  - Within-run duplicate guard: new GPS inserts appended to candidates immediately.
  - `unique_key` IntegrityError swallowed silently as GPS-less dedup fallback.
  - Returns `nouvelles` count (compatible with `main.py` summary display).
- Updated `main.py`: import `save_or_merge` instead of `save_to_database` (line 9), call `save_or_merge(rows)` instead of `save_to_database(rows)` (line 96). No other `main.py` changes.
- Created `tests/test_save_or_merge.py` with 10 tests covering: new insert, price_changed+snapshot, reposted+snapshot, unchanged+no-snapshot, GPS-None insert, atomicity rollback, field persistence, schema idempotency, GPS-less dedup, within-run dedup.
- Code review fixes applied: (1) added `"trajet"` to change-detection fields; (2) `unchanged` branch now persists `list_id` for migrated rows with empty existing `list_id`; (3) added 2 new tests (titre-changed snapshot, list_id migration population).
- Final suite: **65/65 tests pass**, zero regressions.

### File List

- `database.py` — added `import matcher`, `from datetime import datetime`; updated `process()` with `list_id`; added `list_id` migration in `save_to_database`; added `save_or_merge` function (~100 lines)
- `main.py` — updated import line + call site (2 lines only)
- `tests/test_save_or_merge.py` — new file (10 tests)
