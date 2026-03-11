---
stepsCompleted: ['step-01-document-discovery', 'step-02-prd-analysis', 'step-03-epic-coverage-validation', 'step-04-ux-alignment', 'step-05-epic-quality-review', 'step-06-final-assessment']
status: 'complete'
documents:
  prd: 'prd.md'
  architecture: 'architecture.md'
  epics: 'epics.md'
  ux: null
date: '2026-03-10'
project_name: 'LBC-Scraper'
---

# Implementation Readiness Assessment Report

**Date:** 2026-03-10
**Project:** LBC-Scraper

## Document Inventory

| Document | File | Status |
|----------|------|--------|
| PRD | prd.md | Found ✓ |
| Architecture | architecture.md | Found ✓ |
| Epics & Stories | epics.md | Found ✓ |
| UX Design | — | Not found (expected — CLI + simple web UI) |

---

## PRD Analysis

### Functional Requirements

**Ad Identity & Matching (FR1–FR3)**
- FR1: The system can identify when a scraped listing corresponds to a previously seen physical land parcel using GPS proximity (within ~50m) and area similarity (within 10%)
- FR2: The system can handle listings with no GPS data by treating them as new records (no forced match)
- FR3: The system can detect when the same physical land is re-listed under a new list_id and link it to the existing record

**History Tracking (FR4–FR8)**
- FR4: The system can record a full-column snapshot of a listing's previous state to the history table whenever a change is detected during a scrape
- FR5: The system can timestamp each history snapshot with the scrape run date/time
- FR6: The system can preserve multiple history snapshots per listing, building a complete chronological change log over time
- FR7: The system can capture the original Leboncoin publication date (date_publication) for each listing from __NEXT_DATA__ during scraping
- FR8: The system can record the date a listing was first inserted into the database (first_seen)

**Listing State Management (FR9–FR11)**
- FR9: The system can assign a status to each listing after each scrape: new, price_changed, reposted, or unchanged
- FR10: The system can update the main listing record with the latest scraped data when a fuzzy match is found
- FR11: The system can reset the status field to unchanged for listings that matched but had no data differences

**Scrape Pipeline (FR12–FR14)**
- FR12: The scraper can run all existing pipeline steps (--scrape, --get-description, --analyze, --export-csv, --web) without modification to their interfaces or outputs
- FR13: The --scrape step can execute fuzzy matching, history snapshotting, and status assignment transparently as part of its existing run
- FR14: The system can initialize the annonces_history table on first run alongside the existing annonces table

**Web UI — Main Table (FR15–FR17)**
- FR15: The user can see a status indicator (new / price changed / reposted) for each listing in the main table
- FR16: The user can distinguish at a glance which listings appeared since the last scrape (status = new)
- FR17: The user can see date_publication and first_seen dates in the listing view

**Web UI — History Modal (FR18–FR21)**
- FR18: The user can open a history modal for any listing that has at least one history snapshot
- FR19: The user can view the full chronological list of all recorded snapshots for a listing, ordered oldest to newest
- FR20: The user can see which specific fields changed between each snapshot (price, description, list_id, etc.)
- FR21: The user can see the timestamp of each history snapshot

**Data Integrity (FR22–FR23)**
- FR22: The system can guarantee that a scrape interruption does not produce partial or corrupt history snapshots (atomic writes)
- FR23: The system can support a full database drop-and-recreate workflow without losing schema correctness on the next run

**Total FRs: 23**

### Non-Functional Requirements

**Performance (NFR1–NFR4)**
- NFR1: The --scrape step must complete within the same order of magnitude time as before the fuzzy matching changes — no visible regression for a typical run of <500 listings
- NFR2: The web UI main table must load within 2 seconds on localhost for up to 500 listings
- NFR3: The history modal must open and display snapshots within 500ms of user click
- NFR4: The fuzzy matching loop must not cause an O(n²) query pattern — matching must use indexed DB lookups, not full table scans per listing

**Reliability (NFR5–NFR7)**
- NFR5: History snapshots must be written atomically — a crash or keyboard interrupt during a scrape run must not leave partial or corrupt rows in annonces_history
- NFR6: The schema initialization must be idempotent — running --scrape on an existing database must not fail if annonces_history or the new columns already exist
- NFR7: A full database drop and re-creation must result in a valid, consistent schema on the very next --scrape run with no manual intervention

**Integration (NFR8–NFR9)**
- NFR8: The date_publication extraction must gracefully handle Leboncoin listings where __NEXT_DATA__ does not include a publication date — defaulting to NULL without crashing the scrape
- NFR9: The fuzzy matcher must gracefully handle listings where GPS coordinates are absent or malformed — treating them as new records (no match attempted)

**Total NFRs: 9**

### Additional Requirements

- New `matcher.py` module required: pure haversine + area diff logic, no DB access, no Flask imports, no new dependencies (uses `math` stdlib only)
- Implementation order fixed by cross-component dependencies: config.py → matcher.py → database.py → parsers.py → web.py → templates/index.html
- `lat`/`lng` fields are currently parsed but NOT persisted — both parsers.py output dict and database.py schema must be updated
- Additive-only schema migrations: every new column uses the `ALTER TABLE ADD COLUMN` try/except pattern (idempotent, never raises)
- `save_to_database` in database.py must be replaced/renamed to `save_or_merge` to integrate match/merge logic
- `GPS_MATCH_THRESHOLD_M = 50` and `AREA_MATCH_THRESHOLD_PCT = 0.10` constants added to config.py
- All new Flask endpoints return bare arrays/dicts — no response wrappers; all JSON keys snake_case
- History endpoint uses typed integer path param `<int:annonce_id>` to prevent injection
- All datetimes stored as ISO8601 TEXT via `datetime.now().isoformat()`
- Single SQLite transaction wraps all snapshot + update/insert operations per scrape run (NFR5)
- `unique_key` (MD5 hash) preserved for backward compatibility — fuzzy matching complements, not replaces, it

### PRD Completeness Assessment

The PRD is **complete and well-structured**:
- All 23 FRs are clearly numbered, grouped by capability area, and have unambiguous acceptance-testable language
- All 9 NFRs have measurable thresholds (50m, 10%, 2s, 500ms, O(n²))
- NULL-handling policies are explicitly specified (NFR8, NFR9) — no ambiguity on edge cases
- Backward compatibility is explicitly addressed (FR12, unique_key preservation)
- Scope boundaries clearly delineate MVP vs Phase 2/3
- No gaps or contradictions detected

---

## Epic Coverage Validation

### Coverage Matrix

| FR | PRD Requirement (summary) | Epic | Story | Status |
|----|---------------------------|------|-------|--------|
| FR1 | GPS proximity + area similarity matching | Epic 1 | 1.1, 1.4 | ✓ Covered |
| FR2 | No GPS → treat as new record | Epic 1 | 1.1 | ✓ Covered |
| FR3 | Re-listed land linked to existing record | Epic 1 | 1.4 | ✓ Covered |
| FR4 | Full-column snapshot on change detection | Epic 1 | 1.4 | ✓ Covered |
| FR5 | Timestamp each history snapshot | Epic 1 | 1.4 | ✓ Covered |
| FR6 | Multiple snapshots per listing (chronological log) | Epic 1 | 1.4 | ✓ Covered |
| FR7 | Capture date_publication from __NEXT_DATA__ | Epic 1 | 1.3 | ✓ Covered |
| FR8 | Record first_seen on insert | Epic 1 | 1.2, 1.4 | ✓ Covered |
| FR9 | Assign status: new/price_changed/reposted/unchanged | Epic 1 | 1.4 | ✓ Covered |
| FR10 | Update main record on fuzzy match | Epic 1 | 1.4 | ✓ Covered |
| FR11 | Reset status to unchanged when no data diff | Epic 1 | 1.4 | ✓ Covered |
| FR12 | All existing CLI steps unmodified | Epic 1 | 1.4 | ✓ Covered |
| FR13 | Fuzzy matching transparent in --scrape | Epic 1 | 1.4 | ✓ Covered |
| FR14 | annonces_history table init on first run | Epic 1 | 1.2 | ✓ Covered |
| FR15 | Status indicator in main table | Epic 2 | 2.1, 2.2 | ✓ Covered |
| FR16 | Distinguish new listings at a glance | Epic 2 | 2.2 | ✓ Covered |
| FR17 | Show date_publication and first_seen | Epic 2 | 2.1, 2.2 | ✓ Covered |
| FR18 | History modal for listings with snapshots | Epic 2 | 2.4 | ✓ Covered |
| FR19 | Chronological snapshot list (oldest→newest) | Epic 2 | 2.3, 2.4 | ✓ Covered |
| FR20 | Highlight changed fields between snapshots | Epic 2 | 2.4 | ✓ Covered |
| FR21 | Timestamp per history snapshot in modal | Epic 2 | 2.3, 2.4 | ✓ Covered |
| FR22 | Atomic writes — no partial snapshots on interrupt | Epic 1 | 1.4 | ✓ Covered |
| FR23 | Drop-and-recreate schema correctness | Epic 1 | 1.2 | ✓ Covered |

### NFR Coverage Matrix

| NFR | Requirement (summary) | Epic | Story | Status |
|-----|-----------------------|------|-------|--------|
| NFR1 | Scrape time parity (<500 listings) | Epic 1 | 1.4 | ✓ Covered |
| NFR2 | Web table load <2s for 500 listings | Epic 2 | 2.2 | ✓ Covered |
| NFR3 | History modal <500ms | Epic 2 | 2.3, 2.4 | ✓ Covered |
| NFR4 | No O(n²) — indexed DB lookups | Epic 1 | 1.2, 1.4 | ✓ Covered |
| NFR5 | Atomic snapshots (transaction rollback) | Epic 1 | 1.4 | ✓ Covered |
| NFR6 | Idempotent schema init | Epic 1 | 1.2 | ✓ Covered |
| NFR7 | Valid schema after DB drop+recreate | Epic 1 | 1.2 | ✓ Covered |
| NFR8 | Graceful NULL for missing date_publication | Epic 1 | 1.3 | ✓ Covered |
| NFR9 | Graceful NULL for absent GPS | Epic 1 | 1.1 | ✓ Covered |

### Missing Requirements

**None.** All 23 FRs and 9 NFRs from the PRD are explicitly mapped to epics and stories with traceable acceptance criteria.

### Coverage Statistics

- Total PRD FRs: 23
- FRs covered in epics: 23
- FR Coverage: **100%**
- Total PRD NFRs: 9
- NFRs covered in epics: 9
- NFR Coverage: **100%**

---

## UX Alignment Assessment

### UX Document Status

**Not Found — Expected.** The PRD and architecture both explicitly document that no UX design artifact is needed. This is a local-only CLI tool with a single-page vanilla JS web UI. No user research, wireframes, or design system apply.

### Alignment Issues

**None.** The PRD's UI-facing requirements (FR15–FR21) are fully addressed in the architecture:
- Status badge colours (green/amber/blue) specified in architecture
- History modal fed by typed `GET /api/annonces/<int:id>/history` endpoint
- Performance targets defined: NFR2 (2s table load), NFR3 (500ms modal)
- Story 2.2 and 2.4 contain explicit acceptance criteria covering all UI behaviours

### Warnings

**None.** UX documentation absence is justified and all UI requirements have architectural backing.

---

## Epic Quality Review

### Epic Structure Validation

#### User Value Assessment

| Epic | Title | User-Centric Goal? | Verdict |
|------|-------|---------------------|---------|
| Epic 1 | Core Data Engine — Identity, History & Status Recording | ✓ "…transforming the scraper from a point-in-time snapshot into a persistent market tracker" | **Pass** — outcome is user-facing market intelligence |
| Epic 2 | Market Intelligence Web UI | ✓ "Bogoss opens the web UI and immediately sees status indicators…" | **Pass** — directly user-facing |

#### Epic Independence

- Epic 1: Fully standalone — produces data state, history, status without needing Epic 2. ✓
- Epic 2: Depends on Epic 1 output (schema, status, history table) — correct forward-flowing dependency. ✓
- No circular or reverse dependencies. ✓

### Story Quality Assessment

| Story | ACs | G/W/T Format | Testable | Error Cases | Dependencies |
|-------|-----|-------------|----------|-------------|-------------|
| 1.1 Fuzzy Matcher | 5 | ✓ | ✓ | NULL GPS, no-match | None (standalone) |
| 1.2 Schema Migration | 5 | ✓ | ✓ | Idempotent re-run, drop+recreate | None (standalone DDL) |
| 1.3 Parser Enrichment | 5 | ✓ | ✓ | Missing GPS, missing date | None (standalone) |
| 1.4 Save-or-Merge | 6 | ✓ | ✓ | Interrupt, no-match, repost | 1.1, 1.2, 1.3 (backward ✓) |
| 2.1 API Response | 4 | ✓ | ✓ | NULL date_publication | Epic 1 schema (backward ✓) |
| 2.2 Status Badges | 6 | ✓ | ✓ | 500 listings perf | 2.1 (backward ✓) |
| 2.3 History Endpoint | 5 | ✓ | ✓ | No history, invalid ID | Epic 1 schema (backward ✓) |
| 2.4 History Modal | 5 | ✓ | ✓ | No history, perf target | 2.3 (backward ✓) |

### Dependency Analysis

- **Within Epic 1:** 1.1→1.4, 1.2→1.4, 1.3→1.4 — all backward. No forward references.
- **Within Epic 2:** 2.1→2.2, 2.3→2.4 — all backward. No forward references.
- **Cross-epic:** Epic 2 depends on Epic 1 — correct forward flow. No reverse coupling.

### Best Practices Compliance

| Check | Epic 1 | Epic 2 |
|-------|--------|--------|
| Delivers user value | ✓ | ✓ |
| Functions independently | ✓ | ✓ (with Epic 1) |
| Stories appropriately sized | ✓ | ✓ |
| No forward dependencies | ✓ | ✓ |
| Clear acceptance criteria | ✓ (41 ACs, all G/W/T) | ✓ |
| FR traceability maintained | ✓ (FR1–14, FR22–23) | ✓ (FR15–21) |

### Quality Violations

#### 🔴 Critical Violations
**None.**

#### 🟠 Major Issues
**None.**

#### 🟡 Minor Concerns

1. **Developer-persona stories (1.1, 1.2):** Stories 1.1 and 1.2 use "As a developer" rather than end-user persona. Acceptable for a single-developer tool where the developer IS the user, but noted for completeness.
2. **Upfront schema creation (1.2):** Story 1.2 creates all schema changes (5 columns + 1 table) in one story rather than per-story. For additive-only `ALTER TABLE` migrations on a brownfield project, splitting would be artificial fragmentation. **Pragmatic exception accepted.**

### Epic Quality Verdict

**PASS.** Epics are well-structured with complete FR/NFR traceability, proper dependency ordering, clear user value, and rigorous acceptance criteria. No critical or major issues found.

---

## Summary and Recommendations

### Overall Readiness Status

## ✅ READY FOR IMPLEMENTATION

### Assessment Summary

| Assessment Area | Result | Issues |
|----------------|--------|--------|
| Document Inventory | ✓ All found | UX absent (expected) |
| PRD Analysis | ✓ 23 FRs + 9 NFRs extracted | Complete and unambiguous |
| FR Coverage | ✓ 100% (23/23 FRs mapped) | Zero gaps |
| NFR Coverage | ✓ 100% (9/9 NFRs mapped) | Zero gaps |
| UX Alignment | ✓ N/A — justified | No misalignments |
| Epic Quality | ✓ Pass | 0 critical, 0 major, 2 minor |

### Critical Issues Requiring Immediate Action

**None.** All artifacts are aligned, complete, and implementation-ready.

### Minor Items (non-blocking)

1. Stories 1.1 and 1.2 use "As a developer" persona — acceptable for single-developer tool, no action needed.
2. Story 1.2 creates all schema upfront — pragmatic for brownfield additive migrations, no action needed.

### Recommended Next Steps

1. **Proceed to Sprint Planning** — select stories for Sprint 1 (recommended: Epic 1 stories 1.1 → 1.2 → 1.3 → 1.4 in sequence)
2. **Create individual story tickets** from the epics document with acceptance criteria
3. **Begin implementation** following the architecture-specified order: config.py → matcher.py → database.py → parsers.py → web.py → templates/index.html

### Implementation Order (from Architecture)

| Order | File | Stories | Dependencies |
|-------|------|---------|-------------|
| 1 | config.py | 1.1 | None |
| 2 | matcher.py | 1.1 | config.py |
| 3 | database.py | 1.2, 1.4 | matcher.py |
| 4 | parsers.py | 1.3 | None (parallel with 1.1/1.2) |
| 5 | web.py | 2.1, 2.3 | database.py schema |
| 6 | templates/index.html | 2.2, 2.4 | web.py endpoints |

### Final Note

This assessment identified **0 critical issues** and **0 major issues** across 5 validation categories. The planning artifacts (PRD, Architecture, Epics) are well-aligned and comprehensive. All 23 FRs and 9 NFRs have traceable implementation paths through 2 epics and 8 stories with 41 acceptance criteria in proper Given/When/Then format. The project is ready to proceed to implementation.
