# Story 1.1: Fuzzy Matcher Module

Status: done

## Story

As a developer,
I want a standalone haversine + area fuzzy matching utility in `matcher.py`,
so that GPS+area identity matching can be reused, independently tested, and tuned without touching the database layer.

## Acceptance Criteria (BDD)

### AC1: Positive match on GPS proximity + area similarity

**Given** two listings each with valid `lat`, `lng`, and `superficie`
**When** haversine distance ≤ 50m AND `abs(area1 - area2) / max(area1, area2)` ≤ 0.10
**Then** `find_match` returns the `annonce_id` of the matching candidate

### AC2: Graceful NULL handling (NFR9)

**Given** a listing where `lat`, `lng`, or `superficie` is `None` or malformed
**When** `find_match` is called
**Then** it returns `None` without raising any exception

### AC3: No match when thresholds exceeded

**Given** two listings where GPS distance > 50m OR area difference > 10%
**When** `find_match` is called
**Then** it returns `None`

### AC4: Config constants present

**Given** `config.py`
**When** the module is imported
**Then** `GPS_MATCH_THRESHOLD_M = 50` and `AREA_MATCH_THRESHOLD_PCT = 0.10` are present

### AC5: Import constraints

**Given** `matcher.py`
**When** the module is imported
**Then** it imports only `math` and `config` — no `sqlite3`, no `flask`, no new pip dependencies

## Tasks / Subtasks

- [x] Task 1: Add matcher threshold constants to config.py (AC: #4)
  - [x] Add `GPS_MATCH_THRESHOLD_M = 50` after existing constants
  - [x] Add `AREA_MATCH_THRESHOLD_PCT = 0.10` after GPS constant
- [x] Task 2: Create matcher.py with haversine implementation (AC: #1, #3)
  - [x] Implement `_haversine(lat1, lng1, lat2, lng2) -> float` returning metres
  - [x] Implement `find_match(lat, lng, area, candidates) -> int | None`
  - [x] Use `config.GPS_MATCH_THRESHOLD_M` and `config.AREA_MATCH_THRESHOLD_PCT` for thresholds
- [x] Task 3: Implement NULL/malformed data guards (AC: #2)
  - [x] Return `None` immediately if `lat`, `lng`, or `area` is `None`
  - [x] Return `None` immediately if any value fails numeric validation
  - [x] Skip candidates with missing `lat`, `lng`, or `superficie`
- [x] Task 4: Verify import constraints (AC: #5)
  - [x] Only `import math` and `import config` at top of matcher.py
  - [x] No `sqlite3`, `flask`, `requests`, or any pip-installed package

## Dev Notes

### Architecture Contract (MANDATORY)

The architecture document specifies this exact interface — do NOT deviate:

```python
# matcher.py — stateless, no DB access
def find_match(lat: float, lng: float, area: float, candidates: list[dict]) -> int | None:
    """Returns annonce_id of matched candidate, or None if no match / missing data."""
```

**Caller provides `candidates`** as `list[dict]` with keys: `id`, `lat`, `lng`, `superficie`.
The matcher NEVER opens a DB connection — the caller (database.py in Story 1.4) loads candidates and passes them in.

### Haversine Formula

Standard haversine using Python `math` stdlib:

```python
import math

EARTH_RADIUS_M = 6_371_000  # metres

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in metres between two GPS points."""
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
```

### Match Algorithm

```
match = haversine(lat1, lng1, lat2, lng2) <= GPS_MATCH_THRESHOLD_M
    AND abs(area1 - area2) / max(area1, area2) <= AREA_MATCH_THRESHOLD_PCT
```

Return the `id` of the **first** matching candidate, or `None`.

### NULL Policy (NFR9 — CRITICAL)

- If `lat`, `lng`, or `area` argument is `None` → return `None` immediately
- If a candidate dict is missing `lat`, `lng`, or `superficie` → skip that candidate
- NEVER force a merge on incomplete data

### Config Constants

Add to end of `config.py` (after `MAX_PAGES`):

```python
GPS_MATCH_THRESHOLD_M = 50         # metres — fuzzy GPS proximity threshold
AREA_MATCH_THRESHOLD_PCT = 0.10    # 10% — relative area difference threshold
```

### Project Structure Notes

- `config.py` is a flat constants file — no functions, no classes. Just add 2 lines at the bottom.
- `matcher.py` is a NEW file at project root (same level as `config.py`, `parsers.py`, `database.py`).
- Follow existing project conventions: pure functions, snake_case, `X | Y` type annotations (Python 3.10+).
- No docstring requirement beyond the function signature hint.

### What NOT to Do (Anti-Patterns)

- Do NOT import `sqlite3` or open any DB connection in matcher.py
- Do NOT import `flask` or any web framework
- Do NOT add any new pip dependencies — `math` is stdlib
- Do NOT hardcode threshold values — use `config.GPS_MATCH_THRESHOLD_M` and `config.AREA_MATCH_THRESHOLD_PCT`
- Do NOT use `datetime`, `json`, or any module not needed
- Do NOT modify any existing files besides adding 2 constants to `config.py`

### FRs and NFRs Covered

| Requirement | Description |
|-------------|-------------|
| FR1 | GPS proximity (~50m) + area similarity (10%) matching |
| FR2 | No GPS data → treat as new (return None) |
| NFR9 | Graceful NULL/malformed GPS handling |

### References

- [Architecture: Fuzzy Matcher Algorithm](..\\planning-artifacts\\architecture.md) — "Core Architectural Decisions > Fuzzy Matcher Algorithm"
- [Architecture: Matcher Interface Contract](..\\planning-artifacts\\architecture.md) — "Implementation Patterns > Matcher Interface Contract"
- [Architecture: Module Boundaries](..\\planning-artifacts\\architecture.md) — "Project Structure & Boundaries > Architectural Boundaries"
- [Epics: Story 1.1](..\\planning-artifacts\\epics.md) — "Epic 1 > Story 1.1: Fuzzy Matcher Module"
- [PRD: FR1-FR2, NFR9](..\\planning-artifacts\\prd.md) — "Functional Requirements > Ad Identity & Matching"

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation was straightforward.

### Completion Notes List

- Added `GPS_MATCH_THRESHOLD_M = 50` and `AREA_MATCH_THRESHOLD_PCT = 0.10` to `config.py` after `MAX_PAGES`.
- Created `matcher.py` at project root with `_haversine()` (standard haversine, stdlib math only) and `find_match()` implementing the exact architecture contract interface.
- NULL/malformed guards: immediate `None` return if caller args are None/non-numeric; bad candidates are silently skipped.
- Import constraint verified via AST parse: only `math` and `config`.
- 25 pytest tests covering AC1–AC5: positive match, NULL handling (13 cases), no-match thresholds, config constants, import smoke.
- All 25 tests pass in 0.08s, zero regressions.

### File List

- `config.py` — added 2 constants at end of file
- `matcher.py` — new file (project root)
- `tests/test_matcher.py` — new file (25 tests)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status updated to `review`
