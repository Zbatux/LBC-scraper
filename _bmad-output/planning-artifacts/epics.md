---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-epic-1', 'step-03-epic-2', 'step-04-final-validation']
inputDocuments: ['prd.md', 'architecture.md']
---

# LBC-Scraper - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for LBC-Scraper, decomposing the requirements from the PRD and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: The system can identify when a scraped listing corresponds to a previously seen physical land parcel using GPS proximity (within ~50m) and area similarity (within 10%)
FR2: The system can handle listings with no GPS data by treating them as new records (no forced match)
FR3: The system can detect when the same physical land is re-listed under a new list_id and link it to the existing record
FR4: The system can record a full-column snapshot of a listing's previous state to the history table whenever a change is detected during a scrape
FR5: The system can timestamp each history snapshot with the scrape run date/time
FR6: The system can preserve multiple history snapshots per listing, building a complete chronological change log over time
FR7: The system can capture the original Leboncoin publication date (date_publication) for each listing from __NEXT_DATA__ during scraping
FR8: The system can record the date a listing was first inserted into the database (first_seen)
FR9: The system can assign a status to each listing after each scrape: new, price_changed, reposted, or unchanged
FR10: The system can update the main listing record with the latest scraped data when a fuzzy match is found
FR11: The system can reset the status field to unchanged for listings that matched but had no data differences
FR12: The scraper can run all existing pipeline steps (--scrape, --get-description, --analyze, --export-csv, --web) without modification to their interfaces or outputs
FR13: The --scrape step can execute fuzzy matching, history snapshotting, and status assignment transparently as part of its existing run
FR14: The system can initialize the annonces_history table on first run alongside the existing annonces table
FR15: The user can see a status indicator (new / price changed / reposted) for each listing in the main table
FR16: The user can distinguish at a glance which listings appeared since the last scrape (status = new)
FR17: The user can see date_publication and first_seen dates in the listing view
FR18: The user can open a history modal for any listing that has at least one history snapshot
FR19: The user can view the full chronological list of all recorded snapshots for a listing, ordered oldest to newest
FR20: The user can see which specific fields changed between each snapshot (price, description, list_id, etc.)
FR21: The user can see the timestamp of each history snapshot
FR22: The system can guarantee that a scrape interruption does not produce partial or corrupt history snapshots (atomic writes)
FR23: The system can support a full database drop-and-recreate workflow without losing schema correctness on the next run

### NonFunctional Requirements

NFR1: The --scrape step must complete within the same order of magnitude time as before the fuzzy matching changes — no visible regression for a typical run of <500 listings
NFR2: The web UI main table must load within 2 seconds on localhost for up to 500 listings
NFR3: The history modal must open and display snapshots within 500ms of user click
NFR4: The fuzzy matching loop must not cause an O(n²) query pattern — matching must use indexed DB lookups, not full table scans per listing
NFR5: History snapshots must be written atomically — a crash or keyboard interrupt during a scrape run must not leave partial or corrupt rows in annonces_history
NFR6: The schema initialization must be idempotent — running --scrape on an existing database must not fail if annonces_history or the new columns already exist
NFR7: A full database drop and re-creation must result in a valid, consistent schema on the very next --scrape run with no manual intervention
NFR8: The date_publication extraction must gracefully handle Leboncoin listings where __NEXT_DATA__ does not include a publication date — defaulting to NULL without crashing the scrape
NFR9: The fuzzy matcher must gracefully handle listings where GPS coordinates are absent or malformed — treating them as new records (no match attempted)

### Additional Requirements

- New matcher.py module required: pure haversine + area diff logic, no DB access, no Flask imports, no new dependencies (uses math stdlib only)
- Implementation order is fixed by cross-component dependencies: config.py → matcher.py → database.py → parsers.py → web.py → templates/index.html
- lat/lng fields are currently parsed but NOT persisted — both parsers.py output dict and database.py schema must be updated to store them
- Additive-only schema migrations: every new column uses the ALTER TABLE ADD COLUMN try/except pattern (idempotent, never raises)
- save_to_database in database.py must be replaced/renamed to save_or_merge to integrate match/merge logic
- GPS_MATCH_THRESHOLD_M = 50 and AREA_MATCH_THRESHOLD_PCT = 0.10 constants must be added to config.py
- All new Flask endpoints return bare arrays/dicts — no response wrappers; all JSON keys snake_case
- History endpoint must use typed integer path param <int:annonce_id> to prevent injection
- All datetimes stored as ISO8601 TEXT via datetime.now().isoformat()
- Single SQLite transaction must wrap all snapshot + update/insert operations per scrape run (NFR5)
- unique_key (MD5 hash) must be preserved for backward compatibility — fuzzy matching complements, not replaces, it
- No UX design document (vanilla JS + Jinja2, local-only — no UX doc produced)
- No starter template (brownfield project — existing code is the foundation)

### FR Coverage Map

FR1: Epic 1 — Fuzzy GPS+area match logic in matcher.py + save_or_merge in database.py
FR2: Epic 1 — NULL GPS policy in matcher.py: no match attempted → insert as new
FR3: Epic 1 — save_or_merge links new list_id to existing record on fuzzy match
FR4: Epic 1 — Full-column snapshot written to annonces_history on change detection
FR5: Epic 1 — scraped_at timestamp on every history row (ISO8601 via datetime.now().isoformat())
FR6: Epic 1 — Multiple snapshots per listing accumulated in annonces_history over time
FR7: Epic 1 — parsers.py extracts date_publication from __NEXT_DATA__ JSON
FR8: Epic 1 — first_seen column added to annonces, set on INSERT only
FR9: Epic 1 — Status assigned in save_or_merge: new / price_changed / reposted / unchanged
FR10: Epic 1 — save_or_merge UPDATE path writes latest scraped values to annonces row
FR11: Epic 1 — Matched-but-unchanged listings get status = unchanged in save_or_merge
FR12: Epic 1 — All existing CLI flags unaffected; save_or_merge replaces save_to_database transparently
FR13: Epic 1 — Fuzzy match, history snapshot, and status assignment run inside --scrape with no new flags
FR14: Epic 1 — annonces_history table created in idempotent schema init block
FR15: Epic 2 — GET /api/annonces includes status field; index.html renders status badge column
FR16: Epic 2 — status = new badge visually distinct (green) in main table
FR17: Epic 2 — GET /api/annonces includes date_publication and first_seen; rendered in listing view
FR18: Epic 2 — History modal trigger shown for listings with at least one annonces_history row
FR19: Epic 2 — GET /api/annonces/<id>/history returns rows ordered scraped_at ASC
FR20: Epic 2 — Client-side JS diffs consecutive snapshots and highlights changed fields in modal
FR21: Epic 2 — scraped_at timestamp displayed per row in history modal
FR22: Epic 1 — All snapshot + update/insert ops wrapped in single SQLite transaction with rollback
FR23: Epic 1 — Schema init is idempotent; full DB drop + recreate succeeds on next --scrape

## Epic List

### Epic 1: Core Data Engine — Identity, History & Status Recording
After each `--scrape` run, the system correctly identifies returning land listings by GPS+area, records all data changes to history, assigns accurate status flags, and stores publication dates — transforming the scraper from a point-in-time snapshot into a persistent market tracker.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR22, FR23
**NFRs covered:** NFR1, NFR4, NFR5, NFR6, NFR7, NFR8, NFR9

### Epic 2: Market Intelligence Web UI
Bogoss opens the web UI and immediately sees status indicators (new / price changed / reposted) in the main table, and can click any listing to view its complete change history — turning raw scrape data into actionable negotiation intelligence.
**FRs covered:** FR15, FR16, FR17, FR18, FR19, FR20, FR21
**NFRs covered:** NFR2, NFR3

---

## Epic 1: Core Data Engine — Identity, History & Status Recording

After each `--scrape` run, the system correctly identifies returning land listings by GPS+area, records all data changes to history, assigns accurate status flags, and stores publication dates — transforming the scraper from a point-in-time snapshot into a persistent market tracker.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR22, FR23
**NFRs covered:** NFR1, NFR4, NFR5, NFR6, NFR7, NFR8, NFR9

### Story 1.1: Fuzzy Matcher Module

As a developer,
I want a standalone haversine + area fuzzy matching utility in `matcher.py`,
So that GPS+area identity matching can be reused, independently tested, and tuned without touching the database layer.

**Acceptance Criteria:**

**Given** two listings each with valid `lat`, `lng`, and `superficie`
**When** haversine distance ≤ 50m AND `abs(area1 - area2) / max(area1, area2)` ≤ 0.10
**Then** `find_match` returns the `annonce_id` of the matching candidate

**Given** a listing where `lat`, `lng`, or `superficie` is `None` or malformed
**When** `find_match` is called
**Then** it returns `None` without raising any exception (NFR9)

**Given** two listings where GPS distance > 50m OR area difference > 10%
**When** `find_match` is called
**Then** it returns `None`

**Given** `config.py`
**When** the module is imported
**Then** `GPS_MATCH_THRESHOLD_M = 50` and `AREA_MATCH_THRESHOLD_PCT = 0.10` are present

**Given** `matcher.py`
**When** the module is imported
**Then** it imports only `math` and `config` — no `sqlite3`, no `flask`, no new pip dependencies

### Story 1.2: Database Schema Migration

As a developer,
I want the database schema to include the new columns and `annonces_history` table,
So that all subsequent pipeline steps and web endpoints have the data structures they need without manual DB setup.

**Acceptance Criteria:**

**Given** a fresh database with no existing tables
**When** `--scrape` is run
**Then** `annonces` includes columns `lat`, `lng`, `status`, `first_seen`, `date_publication` alongside all existing columns

**Given** the same `--scrape` run
**Then** `annonces_history` table exists with columns: `id` (PK), `annonce_id` (FK), `scraped_at` TEXT, and one column mirroring each column in `annonces`

**Given** a database that already has all new columns and `annonces_history`
**When** `--scrape` is run again
**Then** no `OperationalError` is raised and the run completes normally (NFR6)

**Given** the `annonces_history` table
**Then** an index on `annonce_id` exists for O(1) modal lookups (NFR4)

**Given** a complete drop and re-creation of the SQLite file
**When** `--scrape` is run
**Then** a valid, consistent schema is created with no manual intervention (NFR7)

### Story 1.3: Parser Enrichment

As the scrape pipeline,
I want `parsers.py` to include `lat`, `lng`, and `date_publication` in each listing's output dict,
So that the database layer has all data needed for fuzzy matching and history tracking without additional scraping passes.

**Acceptance Criteria:**

**Given** a Leboncoin listing JSON containing GPS coordinates
**When** the parser processes it
**Then** the output dict includes `lat` and `lng` as Python `float` values

**Given** a Leboncoin listing where GPS data is absent or malformed
**When** the parser processes it
**Then** `lat` and `lng` are `None` in the output dict (no crash)

**Given** a Leboncoin listing where `__NEXT_DATA__` contains a publication date
**When** the parser processes it
**Then** `date_publication` is a non-null string in the output dict

**Given** a Leboncoin listing where `__NEXT_DATA__` does not contain a publication date
**When** the parser processes it
**Then** `date_publication` is `None` and no exception is raised (NFR8)

**Given** all existing output fields from the parser (e.g., `titre`, `prix`, `superficie`, `unique_key`)
**When** `parsers.py` is updated
**Then** all existing fields remain present and unchanged in the output dict (FR12)

### Story 1.4: Save-or-Merge Integration

As the scrape pipeline,
I want `save_or_merge` in `database.py` to run fuzzy matching, snapshot changes, and assign statuses atomically,
So that each `--scrape` run produces an accurate market state and complete change history with no risk of partial writes.

**Acceptance Criteria:**

**Given** a scraped listing with valid GPS+area that matches an existing DB record AND data has changed
**When** `save_or_merge` runs
**Then** the existing `annonces` row is updated with the latest values, a full-column snapshot of the *previous* state is written to `annonces_history`, and the appropriate status (`price_changed` or `reposted`) is set

**Given** a scraped listing that matches an existing DB record but all data is identical
**When** `save_or_merge` runs
**Then** `status` is set to `unchanged`, no `annonces_history` row is written, and no unnecessary UPDATE is executed

**Given** a scraped listing with no GPS data OR no match in the DB
**When** `save_or_merge` runs
**Then** it is inserted as a new `annonces` row with `status = 'new'` and `first_seen = datetime.now().isoformat()`

**Given** a scraped listing whose GPS+area matches an existing record but has a different `list_id`
**When** `save_or_merge` runs
**Then** `status` is set to `reposted` and the main record's `list_id` is updated to the new value

**Given** a `--scrape` run that is interrupted mid-way (keyboard interrupt or crash)
**When** the DB is inspected immediately after
**Then** all changes are either fully committed or fully absent — no partial `annonces_history` rows (NFR5)

**Given** the existing `save_to_database` call in `main.py`
**When** the change is deployed
**Then** `main.py` calls `save_or_merge` with equivalent arguments — no other changes to `main.py` required (FR12–13)

---

## Epic 2: Market Intelligence Web UI

Bogoss opens the web UI and immediately sees status indicators (new / price changed / reposted) in the main table, and can click any listing to view its complete change history — turning raw scrape data into actionable negotiation intelligence.

**FRs covered:** FR15, FR16, FR17, FR18, FR19, FR20, FR21
**NFRs covered:** NFR2, NFR3

### Story 2.1: Updated Listings API Response

As a web UI consumer,
I want the `GET /api/annonces` endpoint to include `status`, `first_seen`, and `date_publication` in each listing object,
So that the frontend has everything it needs to render status badges and dates without a second API call.

**Acceptance Criteria:**

**Given** at least one listing exists in `annonces`
**When** `GET /api/annonces` is called
**Then** each listing object in the JSON array includes `status`, `first_seen`, and `date_publication` fields

**Given** a listing with `status = 'new'`
**When** returned by the API
**Then** `"status": "new"` appears in the JSON object (lowercase string literal, no enum wrapping)

**Given** a listing where `date_publication` is `NULL` in the DB
**When** returned by the API
**Then** `"date_publication": null` appears in the JSON (no crash, no omission) (NFR8)

**Given** all existing fields already returned by the endpoint (e.g., `titre`, `prix`, `superficie`)
**When** the SELECT query is updated
**Then** all previously returned fields remain present and identical (FR12)

### Story 2.2: Status Badges in Main Table

As Bogoss,
I want to see a visual status badge (new / price changed / reposted) for each listing in the web UI main table,
So that I can immediately identify actionable listings without opening each one individually.

**Acceptance Criteria:**

**Given** a listing with `status = 'new'`
**When** the main table renders
**Then** a green "new" badge is displayed in the status column for that listing (FR15, FR16)

**Given** a listing with `status = 'price_changed'`
**When** the main table renders
**Then** an amber "price changed" badge is displayed (FR15)

**Given** a listing with `status = 'reposted'`
**When** the main table renders
**Then** a blue "reposted" badge is displayed (FR15)

**Given** a listing with `status = 'unchanged'`
**When** the main table renders
**Then** no badge or a neutral indicator is shown (no visual noise)

**Given** a listing
**When** the main table renders
**Then** `date_publication` and `first_seen` are visible in the listing row or detail view (FR17)

**Given** 500 listings loaded from the API
**When** the page fully renders
**Then** load time is under 2 seconds on localhost (NFR2)

### Story 2.3: History API Endpoint

As the history modal,
I want `GET /api/annonces/<id>/history` to return the full chronological snapshot list for a listing,
So that the frontend can render the complete change log without any additional queries.

**Acceptance Criteria:**

**Given** a listing with one or more rows in `annonces_history`
**When** `GET /api/annonces/<id>/history` is called with a valid integer ID
**Then** a JSON array of all snapshot rows is returned, ordered by `scraped_at` ASC (FR19)

**Given** the JSON array returned
**Then** each object contains `scraped_at`, `annonce_id`, and all snapshot columns (FR21)

**Given** a listing with no history rows in `annonces_history`
**When** the endpoint is called
**Then** an empty JSON array `[]` is returned (no 404, no crash)

**Given** a non-integer or non-existent ID in the path
**When** the endpoint is called
**Then** Flask returns a 404 with `{"error": "not found"}` — the typed `<int:annonce_id>` path param prevents injection

**Given** the response shape
**Then** it is a bare JSON array — no `{"data": [...]}` wrapper (architecture pattern)

### Story 2.4: History Modal

As Bogoss,
I want to click a listing and see a history modal with every recorded snapshot and highlighted field changes,
So that I can read price trajectories and seller behaviour signals at a glance — my key negotiation tool.

**Acceptance Criteria:**

**Given** a listing with at least one `annonces_history` row
**When** I click the history trigger for that listing
**Then** a modal opens displaying the full chronological list of snapshots ordered oldest to newest (FR18, FR19)

**Given** the modal is open
**Then** each snapshot row shows its `scraped_at` timestamp (FR21)

**Given** two consecutive snapshots where `prix` differs
**When** the modal renders
**Then** the price field is visually highlighted (e.g., colour, bold) to indicate the change (FR20)

**Given** two consecutive snapshots where fields other than `prix` differ (e.g., `titre`, `list_id`)
**When** the modal renders
**Then** those fields are also highlighted (FR20)

**Given** a listing with no history rows
**When** the main table renders
**Then** the history trigger is hidden or disabled — no empty modal can be opened (FR18)

**Given** clicking the history trigger
**When** the API call to `/api/annonces/<id>/history` completes and the modal renders
**Then** the full flow takes under 500ms on localhost (NFR3)
