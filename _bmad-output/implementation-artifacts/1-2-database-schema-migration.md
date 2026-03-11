# Story 1.2: Database Schema Migration

Status: done

## Story

As a developer,
I want the database schema to include the new columns and `annonces_history` table,
so that all subsequent pipeline steps and web endpoints have the data structures they need without manual DB setup.

## Acceptance Criteria

### AC1: New columns on fresh database

**Given** a fresh database with no existing tables
**When** `--scrape` is run
**Then** `annonces` includes columns `lat`, `lng`, `status`, `first_seen`, `date_publication` alongside all existing columns

### AC2: annonces_history table created on fresh database

**Given** the same `--scrape` run on a fresh database
**Then** `annonces_history` table exists with columns: `id` (PK), `annonce_id` (FK), `scraped_at` TEXT, and one column mirroring each column in `annonces`

### AC3: Idempotent schema init (NFR6)

**Given** a database that already has all new columns and `annonces_history`
**When** `--scrape` is run again
**Then** no `OperationalError` is raised and the run completes normally

### AC4: Index on annonce_id for O(1) lookups (NFR4)

**Given** the `annonces_history` table
**Then** an index on `annonce_id` exists for O(1) modal lookups

### AC5: Full DB drop and re-create (NFR7)

**Given** a complete drop and re-creation of the SQLite file
**When** `--scrape` is run
**Then** a valid, consistent schema is created with no manual intervention

## Tasks / Subtasks

- [x] Task 1: Add new columns to `annonces` via additive migration pattern (AC: #1, #3)
  - [x] Add `lat REAL` migration entry
  - [x] Add `lng REAL` migration entry
  - [x] Add `status TEXT` migration entry
  - [x] Add `first_seen TEXT` migration entry
  - [x] Add `date_publication TEXT` migration entry
  - [x] Verify all new migrations follow existing try/except pattern

- [x] Task 2: Create `annonces_history` table (AC: #2, #5)
  - [x] Write `CREATE TABLE IF NOT EXISTS annonces_history` with full column mirror of `annonces`
  - [x] Include `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - [x] Include `annonce_id INTEGER` (FK — no enforced FK constraint needed, consistent with existing pattern)
  - [x] Include `scraped_at TEXT` (ISO8601 snapshot timestamp)
  - [x] Mirror ALL `annonces` columns (see Dev Notes for complete list)

- [x] Task 3: Create index on `annonces_history.annonce_id` (AC: #4)
  - [x] Add `CREATE INDEX IF NOT EXISTS idx_history_annonce_id ON annonces_history(annonce_id)`

- [x] Task 4: Write tests for schema idempotency (AC: #3, #5)
  - [x] Test: run schema init twice → no OperationalError
  - [x] Test: verify all new `annonces` columns exist after init
  - [x] Test: verify `annonces_history` table exists after init
  - [x] Test: verify `idx_history_annonce_id` index exists

## Dev Notes

### What This Story Does NOT Include

This story is **schema-only**. Do NOT implement:
- `save_or_merge` logic (Story 1.4)
- Parser changes for `lat`, `lng`, `date_publication` (Story 1.3)
- Any data writing to `annonces_history` (Story 1.4)
- Any web endpoint changes (Epic 2)

The only file to touch is **`database.py`**. No other file requires modification.

### Critical: Complete annonces Column List

The `annonces_history` table must mirror ALL columns currently in `annonces`. As of the end of Story 1.1, the effective column set for `annonces` is:

**Original CREATE TABLE columns:**
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `titre TEXT`
- `prix REAL`
- `superficie REAL`
- `prix_m2 REAL`
- `trajet TEXT`
- `lien TEXT`
- `unique_key TEXT UNIQUE`
- `description TEXT`

**Already-existing additive migration columns (in database.py):**
- `viabilise INTEGER`
- `emprise_sol REAL`
- `partiellement_constructible INTEGER`
- `partiellement_agricole INTEGER`
- `analyse_faite INTEGER DEFAULT 0`
- `nogo INTEGER DEFAULT 0`
- `note INTEGER`

**New columns to add in this story:**
- `lat REAL`
- `lng REAL`
- `status TEXT`
- `first_seen TEXT`
- `date_publication TEXT`

The `annonces_history` table mirrors all of the above data columns (minus `id` and `unique_key` constraints — just bare column types). It adds its own `id` PK, `annonce_id`, and `scraped_at`.

### annonces_history Table Definition

```python
cursor.execute('''
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
        analyse_faite INTEGER,
        nogo INTEGER,
        note INTEGER,
        lat REAL,
        lng REAL,
        status TEXT,
        first_seen TEXT,
        date_publication TEXT
    )
''')
```

### Index Creation

```python
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_history_annonce_id "
    "ON annonces_history(annonce_id)"
)
```

`CREATE INDEX IF NOT EXISTS` is idempotent — safe to run on every startup.

### New Migrations to Add (additive, idempotent)

Append these 5 entries to the existing `migrations` list in `save_to_database`:

```python
"ALTER TABLE annonces ADD COLUMN lat REAL",
"ALTER TABLE annonces ADD COLUMN lng REAL",
"ALTER TABLE annonces ADD COLUMN status TEXT",
"ALTER TABLE annonces ADD COLUMN first_seen TEXT",
"ALTER TABLE annonces ADD COLUMN date_publication TEXT",
```

They follow the exact existing pattern — each wrapped in `try/except sqlite3.OperationalError: pass`.

### Execution Order Within save_to_database

The schema ops must run in this order:
1. `CREATE TABLE IF NOT EXISTS annonces` (unchanged existing block)
2. Run all migrations list (ALTER TABLE, try/except — add 5 new entries)
3. `CREATE TABLE IF NOT EXISTS annonces_history` ← **new**
4. `CREATE INDEX IF NOT EXISTS idx_history_annonce_id` ← **new**
5. Then the existing INSERT loop (unchanged)

### Existing Code NOT to Touch

- `generate_unique_key()` — unchanged
- `get_existing_trajets()` — unchanged
- `process()` — unchanged
- The existing CREATE TABLE for `annonces` — add nothing to the CREATE TABLE statement itself; use the migration list instead (so existing populated DBs are unaffected)
- The INSERT statement inside the loop — unchanged (new columns will be NULL by default; Story 1.4 handles real writes)
- `main.py` — must NOT be touched in this story

### Architecture Compliance

**Module boundary:** `database.py` owns all SQLite schema operations. No schema changes belong elsewhere.

**Migration pattern (MANDATORY):**
```python
migrations = [
    # ... existing migrations ...
    "ALTER TABLE annonces ADD COLUMN lat REAL",
    "ALTER TABLE annonces ADD COLUMN lng REAL",
    "ALTER TABLE annonces ADD COLUMN status TEXT",
    "ALTER TABLE annonces ADD COLUMN first_seen TEXT",
    "ALTER TABLE annonces ADD COLUMN date_publication TEXT",
]
for sql in migrations:
    try:
        cursor.execute(sql)
    except sqlite3.OperationalError:
        pass  # column already exists
```

**Naming conventions:**
- Table: `annonces_history` (snake_case plural)
- FK column: `annonce_id` (singular FK pattern)
- Index: `idx_history_annonce_id`
- New columns: `lat`, `lng`, `status`, `first_seen`, `date_publication` — all snake_case

**Do NOT use:**
- `datetime` module in this story (no timestamps written here)
- `matcher` import (not needed for schema)
- Any `DEFAULT` value on `status` in the migration (Story 1.4 sets status explicitly)

### Previous Story Intelligence (Story 1.1)

From Story 1.1 completion notes:
- `config.py` already has `GPS_MATCH_THRESHOLD_M = 50` and `AREA_MATCH_THRESHOLD_PCT = 0.10` ✓
- `matcher.py` is at project root with `find_match(lat, lng, area, candidates) -> int | None` ✓
- Tests live in `tests/test_matcher.py` — add this story's tests in `tests/test_database_schema.py`
- Agent model: claude-sonnet-4-6 with Python `math` stdlib, no new dependencies

### Testing Approach

Create `tests/test_database_schema.py` using `tempfile.mkstemp()` for isolated SQLite files.

Pattern:
```python
import sqlite3
import tempfile
import os
import database

def test_schema_idempotent():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        database.save_to_database([], db_name=path)  # first init
        database.save_to_database([], db_name=path)  # second init — must not raise
    finally:
        os.unlink(path)
```

Verify column existence with:
```python
cursor.execute("PRAGMA table_info(annonces)")
columns = {row[1] for row in cursor.fetchall()}
assert "lat" in columns
```

Verify index:
```python
cursor.execute("PRAGMA index_list(annonces_history)")
indexes = {row[1] for row in cursor.fetchall()}
assert "idx_history_annonce_id" in indexes
```

### Project Structure Notes

Only file modified: `database.py` (project root).

New test file: `tests/test_database_schema.py`.

No other files touched. This is intentionally minimal — the schema must be stable before Stories 1.3 and 1.4 build on it.

### FRs and NFRs Covered

| Requirement | Description |
|-------------|-------------|
| FR4 | `annonces_history` table created for change snapshots |
| FR5 | `scraped_at` column on history table |
| FR6 | Multiple snapshots per listing possible |
| FR8 | `first_seen` column on `annonces` |
| FR9 | `status` column on `annonces` |
| FR14 | `annonces_history` created on first run (idempotent) |
| NFR4 | Index on `annonce_id` for O(1) modal lookups |
| NFR6 | Idempotent schema init — existing DB → no OperationalError |
| NFR7 | Fresh DB drop → valid schema on next `--scrape` |

### References

- [Architecture: Data Architecture](../_bmad-output/planning-artifacts/architecture.md#data-architecture) — Schema columns, annonces_history definition, migration pattern
- [Architecture: Process Patterns](../_bmad-output/planning-artifacts/architecture.md#process-patterns) — Schema Migration Pattern code block
- [Architecture: Project Structure](../_bmad-output/planning-artifacts/architecture.md#complete-project-directory-structure) — `database.py [MOD]`
- [Epics: Story 1.2](../_bmad-output/planning-artifacts/epics.md#story-12-database-schema-migration) — Acceptance criteria
- [Story 1.1 completion notes](1-1-fuzzy-matcher-module.md#completion-notes-list) — config.py and matcher.py already done

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation straightforward, all 5 tests passed on first run.

### Completion Notes List

- Added 5 additive migrations to `save_to_database`: `lat REAL`, `lng REAL`, `status TEXT`, `first_seen TEXT`, `date_publication TEXT` — all follow existing try/except pattern (AC1, AC3).
- Created `annonces_history` table with `CREATE TABLE IF NOT EXISTS` mirroring all 21 `annonces` columns plus `id PK`, `annonce_id`, `scraped_at` (AC2, AC5).
- Created `CREATE INDEX IF NOT EXISTS idx_history_annonce_id ON annonces_history(annonce_id)` for O(1) lookups (AC4).
- Schema ops execute in correct order within `save_to_database`: CREATE TABLE annonces → migrations → CREATE TABLE annonces_history → CREATE INDEX → INSERT loop.
- 5 tests added in `tests/test_database_schema.py` covering all ACs; 35/35 tests pass with zero regressions.

### File List

- `database.py` (modified)
- `tests/test_database_schema.py` (created)
