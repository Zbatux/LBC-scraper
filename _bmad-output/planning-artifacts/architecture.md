---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
status: 'complete'
completedAt: '2026-03-10'
inputDocuments: ['prd.md', 'product-brief-LBC-Scraper-2026-03-10.md', 'project-context.md', 'ARCHITECTURE.md']
workflowType: 'architecture'
project_name: 'LBC-Scraper'
user_name: 'Bogoss'
date: '2026-03-10'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:** 23 FRs across 7 capability areas — Ad Identity & Matching (FR1–3), History Tracking (FR4–8), Listing State Management (FR9–11), Scrape Pipeline (FR12–14), Web UI Main Table (FR15–17), Web UI History Modal (FR18–21), Data Integrity (FR22–23).

**Non-Functional Requirements:** 9 NFRs — Performance (NFR1–4: scrape time parity, 2s table load, 500ms modal, no O(n²) queries), Reliability (NFR5–7: atomic snapshots, idempotent schema init, clean re-run), Integration (NFR8–9: graceful NULL handling for missing `date_publication` and GPS).

**Scale & Complexity:** Low. Single-user local tool, SQLite, <500 listings, no deployment, no multi-tenancy.

### Technical Constraints & Dependencies

- SQLite via raw `sqlite3` module — no ORM
- Additive-only schema migrations (existing pattern in `database.py`)
- No new CLI flags for MVP — fuzzy matching integrates transparently into `--scrape`
- `date_publication` extracted from `__NEXT_DATA__` JSON during Playwright scrape
- `lat`/`lng` are parsed today by `parsers.get_coords` but not persisted — must be added to schema and save logic
- Existing `unique_key` (MD5 hash) must be preserved for backward compatibility

### Cross-Cutting Concerns Identified

| Concern | Affected Components |
|---------|-------------------|
| SQLite transaction atomicity for history snapshots | `database.py` |
| Fuzzy match threshold constants (50m GPS, 10% area) | `config.py`, new `matcher.py` |
| `lat`/`lng` persistence gap (parsed but not stored today) | `database.py` schema + `parsers.py` output |
| Backward compatibility on existing populated DBs | `database.py` migration block |
| History API response safety (no column injection) | `web.py` |

---

## Starter Template Evaluation

### Primary Technology Domain

Brownfield enhancement of existing Python CLI + Flask web app. No starter template applicable — project already exists and is running in production on the developer's local machine.

### Existing Technical Foundation (Locked Decisions)

| Decision | Choice | Notes |
|----------|--------|-------|
| Language | Python 3.x | All modules, no TypeScript |
| Scraping | Playwright (sync API) | Anti-bot browser automation |
| Database | SQLite via `sqlite3` stdlib | No ORM; raw SQL with additive migrations |
| Web framework | Flask (minimal) | Local-only, single-page, no auth |
| Frontend | Vanilla JS + Jinja2 template | `templates/index.html` — no build step |
| AI analysis | Ollama local (`gemma3:12b`) | `analyzer.py`, no external API |
| Travel routing | OSRM HTTP API | `routing.py` |
| Config | `config.py` hardcoded constants | No env vars, no config files |

### New Module Decision

**`matcher.py`** — New standalone module for fuzzy GPS+area matching logic.

**Rationale:** Isolating matching logic into its own module:
- Keeps `database.py` focused on persistence only
- Makes the matcher independently testable
- Makes threshold constants easy to find and tune
- Follows the existing single-responsibility file pattern of the project

**No new dependencies required.** Haversine distance uses Python `math` stdlib only.

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical (block implementation):**
- Schema additions to `annonces` + new `annonces_history` table
- Fuzzy matcher algorithm + NULL-handling policy
- Pipeline integration point for match/merge logic

**Important (shape architecture):**
- History modal endpoint design (full snapshot vs. diff)
- `matcher.py` as isolated module

**Deferred (Post-MVP):**
- Summary stats endpoint
- Filter/sort by status
- CSV history export

### Data Architecture

**Schema: New columns on `annonces` (additive migration):**

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `lat` | REAL | NULL | GPS latitude — parsed today, not stored |
| `lng` | REAL | NULL | GPS longitude — parsed today, not stored |
| `status` | TEXT | `'new'` | `new` / `price_changed` / `reposted` / `unchanged` |
| `first_seen` | TEXT | scrape datetime | ISO8601 string |
| `date_publication` | TEXT | NULL | From `__NEXT_DATA__`; NULL if absent (NFR8) |

**New table: `annonces_history`**
- Full-column snapshot per detected change
- `annonce_id` FK to `annonces.id`
- `scraped_at` TEXT (ISO8601)
- Index on `annonce_id` for O(1) modal lookups (NFR4)

**Migration strategy:** Additive-only — follow existing `ALTER TABLE ADD COLUMN` try/except pattern in `database.py`. Schema init is idempotent (NFR6, NFR7).

### Fuzzy Matcher Algorithm

**Algorithm:** Haversine distance (GPS) + relative area difference.

```
match_condition = haversine(lat1, lng1, lat2, lng2) <= 50  # metres
             AND abs(area1 - area2) / max(area1, area2) <= 0.10  # 10%
```

**NULL policy (NFR9):** If GPS coordinates OR area are absent/malformed for either candidate → no match attempted → insert as new. Never force a merge on incomplete data.

**Constants in `config.py`:** `GPS_MATCH_THRESHOLD_M = 50`, `AREA_MATCH_THRESHOLD_PCT = 0.10`

**Implementation:** Pure Python `math` stdlib (haversine uses `sin`, `cos`, `asin`, `sqrt`). No new dependencies.

### Pipeline Integration

**Match/merge logic lives in `database.py`** — specifically in the save function (renamed `save_or_merge`). `matcher.py` is imported as a stateless utility supplying `find_match(lat, lng, area, candidates) -> annonce_id | None`.

**Scrape flow:**
1. `get_all_ads` → raw listings (unchanged)
2. `process` → add travel times (unchanged)
3. `save_or_merge` → for each listing:
   - Load GPS-indexed candidates from DB
   - Call `matcher.find_match`
   - If match: snapshot → UPDATE → set status
   - If no match: INSERT with `status='new'`, `first_seen=now`
   - All within a single SQLite transaction (NFR5)

### API & Communication Patterns

**New endpoint:** `GET /api/annonces/<int:annonce_id>/history`
- Returns JSON array of full `annonces_history` rows for the given ID, ordered `scraped_at ASC`
- Full snapshot rows (not diff-only): simple server logic, client-side diff in JS if needed (FR20)
- Typed integer path param prevents SQL injection — read-only, no whitelist needed beyond that

### Security

- History endpoint: read-only, typed `<int:annonce_id>` path param — no column injection surface
- No new EDITABLE_FIELDS mutations for history data
- All existing PATCH protections unchanged

### Infrastructure & Deployment

Local machine only. No deployment, no CI/CD, no hosting. SQLite file on disk. All existing patterns apply unchanged.

### Decision Impact Analysis

**Implementation sequence:**
1. `config.py` — add matcher threshold constants
2. `matcher.py` — new module, pure haversine + area diff logic
3. `database.py` — schema migrations, `save_or_merge` replacing `save_to_database`
4. `parsers.py` — ensure `lat`, `lng`, `date_publication` included in output dict
5. `web.py` — add `/api/annonces/<id>/history` endpoint
6. `templates/index.html` — status column badges + history modal JS

**Cross-component dependencies:**
- `matcher.py` depends on: `config.py` (thresholds)
- `database.py` depends on: `matcher.py`, `parsers.py` (`lat`/`lng`/`date_publication` in output)
- `web.py` depends on: `database.py` schema (`annonces_history` table)
- `templates/index.html` depends on: `web.py` (history endpoint + `status` field in `/api/annonces`)

---

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

7 areas where AI agents could make different choices that would create incompatibility.

### Naming Patterns

**Database Naming Conventions:**
- Tables: `snake_case` plural (`annonces`, `annonces_history`)
- Columns: `snake_case` (`first_seen`, `date_publication`, `annonce_id`, `scraped_at`)
- Foreign keys: `{table_singular}_id` pattern (`annonce_id`)
- Never: `camelCase`, `PascalCase`, or hyphenated names in SQL

**API Naming Conventions:**
- Endpoints: lowercase, hyphen-separated multi-word resources (Flask convention)
- Path params: typed integers `<int:annonce_id>` — never string params for IDs
- JSON response keys: `snake_case` (match DB column names — `sqlite3.Row` serializes as-is)

**Code Naming Conventions:**
- Python functions: `snake_case` — matches all existing code (`save_to_database`, `find_match`)
- Module names: `snake_case` single word or underscore-joined (`matcher.py`, `database.py`)

### Format Patterns

**API Response Formats:**
- Success: plain JSON array `[{...}]` or plain dict `{...}` — no wrapper object
- Error: `{"error": "human-readable message"}` with appropriate HTTP status code (400, 404)
- Never: `{"data": [...], "error": null, "status": "ok"}` wrappers

**Data Exchange Formats:**
- Datetimes: ISO8601 strings `"YYYY-MM-DDTHH:MM:SS"` — use `datetime.now().isoformat()`
- Booleans in DB: `INTEGER 0/1` — never Python `True`/`False` stored as TEXT
- Nullable fields: `NULL` in DB, `None` in Python, `null` in JSON — consistent throughout
- Status values: lowercase snake_case string literals — `'new'`, `'price_changed'`, `'reposted'`, `'unchanged'`

### Structure Patterns

**Project Organization:**
- One responsibility per file — matches existing pattern (`parsers.py`, `routing.py`, `analyzer.py`)
- New `matcher.py`: pure matching logic only — no DB access, no Flask imports
- `database.py`: all SQLite operations — schema init, save, merge, history snapshot
- `web.py`: all Flask routes — no business logic, delegates to DB layer

**DB Connection Pattern:**
- Use `get_db()` helper in `web.py` for Flask routes (already exists)
- Use `sqlite3.connect(db_name)` directly in `database.py` functions (existing pattern)
- Always `conn.close()` in a finally block or let context manager handle it
- Never share a single global connection across calls

### Process Patterns

**Schema Migration Pattern:**
```python
migrations = [
    "ALTER TABLE annonces ADD COLUMN new_col TYPE",
]
for sql in migrations:
    try:
        cursor.execute(sql)
    except sqlite3.OperationalError:
        pass  # column already exists
```
Every new column follows this exact pattern — idempotent, never raises.

**Transaction Pattern for History Snapshots (NFR5):**
```python
conn = sqlite3.connect(db_name)
try:
    # snapshot + update/insert all in one transaction
    conn.commit()
except Exception:
    conn.rollback()
    raise
finally:
    conn.close()
```

**Matcher Interface Contract:**
```python
# matcher.py — stateless, no DB access
def find_match(lat: float, lng: float, area: float, candidates: list[dict]) -> int | None:
    """Returns annonce_id of matched candidate, or None if no match / missing data."""
```
Caller provides `candidates` as list of dicts with keys: `id`, `lat`, `lng`, `superficie`.

### Enforcement Guidelines

**All AI Agents MUST:**
- Use `snake_case` for all DB columns, API JSON keys, and Python identifiers
- Return bare arrays/dicts from Flask endpoints — no response wrappers
- Store all datetimes as ISO8601 TEXT via `datetime.now().isoformat()`
- Follow the additive-only migration pattern for any schema changes
- Keep `matcher.py` free of DB connections — pass candidates as dicts from the caller
- Use SQLite transactions with rollback for any multi-step write operations

**Anti-Patterns (never do these):**
- `status = 1` (use `status = 'new'`)
- `{"data": rows, "error": null}` response envelopes
- `matcher.find_match()` opening its own DB connection
- `ALTER TABLE` without the try/except migration guard
- `datetime.now().strftime(...)` with non-ISO formats for stored values

---

## Project Structure & Boundaries

### Complete Project Directory Structure

Brownfield project — structure shows final state after history tracking feature is added.
`[NEW]` = new file, `[MOD]` = modified file, no marker = unchanged.

```
LBC-scraper/
├── config.py               [MOD] Add GPS_MATCH_THRESHOLD_M, AREA_MATCH_THRESHOLD_PCT
├── matcher.py              [NEW] Fuzzy GPS+area matching — pure logic, no DB access
├── database.py             [MOD] Schema migrations, save_or_merge, history snapshots
├── parsers.py              [MOD] Include lat, lng, date_publication in output dict
├── web.py                  [MOD] Add GET /api/annonces/<id>/history endpoint
├── browser.py              (unchanged)
├── descriptions.py         (unchanged)
├── analyzer.py             (unchanged)
├── exporter.py             (unchanged)
├── routing.py              (unchanged)
├── main.py                 (unchanged)
├── requirements.txt        (unchanged — no new dependencies)
├── lbc_data.db             (runtime — SQLite database file)
├── templates/
│   └── index.html          [MOD] Status column badges + history modal JS
└── _bmad-output/
    └── planning-artifacts/
        ├── prd.md
        └── architecture.md
```

### Architectural Boundaries

**Module Boundaries:**

| Module | Responsibility | Imports | Does NOT do |
|--------|---------------|---------|-------------|
| `matcher.py` | GPS+area fuzzy match algorithm | `math`, `config` | DB access, Flask, I/O |
| `database.py` | All SQLite operations: schema, save, merge, history | `matcher`, `parsers`, `sqlite3`, `datetime` | Scraping, routing, Flask |
| `parsers.py` | Field extraction from raw LBC JSON | `re` | DB, Flask, network |
| `web.py` | Flask routes + JSON responses | `flask`, `sqlite3` | Business logic, matching |
| `config.py` | Global constants | (none) | Logic of any kind |

**API Boundaries:**

| Endpoint | Method | Purpose | Response shape |
|----------|--------|---------|----------------|
| `/api/annonces` | GET | All listings (incl. status, first_seen, date_publication) | `[{id, titre, prix, ..., status, first_seen, date_publication}]` |
| `/api/annonces/<int:id>/history` | GET | History snapshots for one listing | `[{id, annonce_id, scraped_at, titre, prix, ...}]` |
| `/api/annonces` | DELETE | Bulk delete | `{deleted: n}` |
| `/api/annonces/bulk` | PATCH | Bulk field update | `{updated: n}` |
| `/api/annonces/<int:id>` | PATCH | Single listing update | `{updated: 1}` |

### Requirements to Structure Mapping

| FR Group | FRs | File(s) |
|----------|-----|---------|
| Ad Identity & Matching | FR1-3 | `matcher.py`, `database.py` |
| History Tracking | FR4-8 | `database.py` (schema + snapshot), `parsers.py` (`date_publication`) |
| Listing State Management | FR9-11 | `database.py` (status assignment in `save_or_merge`) |
| Scrape Pipeline | FR12-14 | `database.py` (idempotent schema init), `main.py` (unchanged) |
| Web UI — Main Table | FR15-17 | `web.py` (status in GET response), `templates/index.html` |
| Web UI — History Modal | FR18-21 | `web.py` (history endpoint), `templates/index.html` (modal JS) |
| Data Integrity | FR22-23 | `database.py` (transaction wrapping, idempotent init) |

### Integration Points

**Internal communication:**
- `main.py` calls `database.save_or_merge(rows)` — replaces current `save_to_database` call
- `database.save_or_merge` calls `matcher.find_match(lat, lng, area, candidates)` — pure function
- `web.py` queries SQLite directly via `get_db()` — no intermediate service layer

**External integrations (unchanged):**
- Leboncoin via Playwright (`browser.py`)
- OSRM HTTP API for travel times (`routing.py`)
- Ollama local API for AI analysis (`analyzer.py`)

**Data flow — `--scrape`:**
```
Playwright scrape -> parsers enrich -> save_or_merge:
  for each listing:
    load DB candidates (rows with lat/lng)
    -> matcher.find_match -> match?  -> snapshot + UPDATE (status=price_changed/reposted)
                                     -> no match -> INSERT (status=new, first_seen=now)
  commit all in single transaction
```

**Data flow — history modal:**
```
Browser click "history" -> GET /api/annonces/<id>/history
  -> web.py queries annonces_history WHERE annonce_id=id ORDER BY scraped_at ASC
  -> returns JSON array of full snapshot rows
  -> index.html JS renders modal table with client-side diff highlighting
```

---

## Architecture Validation Results

### Coherence Validation

All module boundaries, naming conventions, API shapes, and transaction patterns are internally consistent. No conflicts between decisions. matcher.py isolation is clean - no circular imports possible: config <- matcher <- database <- main/web.

### Requirements Coverage Validation

All 23 FRs and 9 NFRs have explicit architectural support (see Requirements to Structure Mapping). No gaps found.

Clarification: GET /api/annonces SELECT query in web.py must be updated to include status, first_seen, date_publication - new columns exist after migration but will not appear in API responses until the SELECT list is updated.

### Implementation Readiness Validation

- All decisions documented with rationale
- No outstanding version conflicts (stdlib-only additions)
- All 7 potential conflict points covered by patterns
- Matcher interface contract fully specified
- Transaction pattern specified for the one risky multi-step write

### Gap Analysis Results

No critical gaps. One minor clarification:
- web.py GET /api/annonces SELECT column list needs explicit update (documented in Decision Impact Analysis)

### Architecture Completeness Checklist

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped
- [x] Critical decisions documented
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed (NFR1-4)
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented (migration, transaction, matcher contract)
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

Key Strengths:
- Zero new dependencies - pure stdlib additions reduce risk
- Additive-only schema changes - existing DB and pipeline untouched
- Clear module isolation - matcher.py is independently testable
- All patterns derived from existing codebase conventions - no style drift

Implementation Handoff - AI agents should implement in this order:
1. config.py - threshold constants
2. matcher.py - haversine + area diff (testable standalone)
3. database.py - migrations + save_or_merge
4. parsers.py - add lat, lng, date_publication to output
5. web.py - update GET select list + add history endpoint
6. templates/index.html - status badges + history modal
