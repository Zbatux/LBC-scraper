# Story 1.3: Parser Enrichment

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the scrape pipeline,
I want `parsers.py` to include `lat`, `lng`, and `date_publication` in each listing's output dict,
so that the database layer has all data needed for fuzzy matching and history tracking without additional scraping passes.

## Acceptance Criteria

### AC1: lat and lng present as floats when GPS data available

**Given** a Leboncoin listing JSON containing GPS coordinates in `location.lat` / `location.lng`
**When** the parser processes it
**Then** the output dict from `process()` includes `lat` and `lng` as Python `float` values

### AC2: lat and lng are None when GPS data absent or malformed

**Given** a Leboncoin listing where GPS data is absent or malformed (None, missing keys)
**When** the parser processes it
**Then** `lat` and `lng` are `None` in the output dict and no exception is raised (NFR9)

### AC3: date_publication present when available in ad JSON

**Given** a Leboncoin listing where `first_publication_date` is present in the ad dict
**When** the parser processes it
**Then** `date_publication` is a non-null string in the output dict

### AC4: date_publication is None when absent from ad JSON

**Given** a Leboncoin listing where `first_publication_date` is absent or empty
**When** the parser processes it
**Then** `date_publication` is `None` and no exception is raised (NFR8)

### AC5: All existing output fields remain unchanged

**Given** all existing output fields from `process()` (`titre`, `prix`, `superficie`, `prix_m2`, `trajet`, `lien`)
**When** `parsers.py` and `process()` are updated
**Then** all existing fields remain present and unchanged in the output dict (FR12)

## Tasks / Subtasks

- [ ] Task 1: Add `parse_date_publication(ad)` to `parsers.py` (AC: #3, #4)
  - [ ] Extract `date_publication` from `ad.get("first_publication_date")`
  - [ ] Return the value as-is (string) if present and truthy
  - [ ] Return `None` if absent, empty, or any exception occurs (NFR8 guard)

- [ ] Task 2: Update `process()` in `database.py` to include lat, lng, date_publication in output dict (AC: #1, #2, #3, #4, #5)
  - [ ] Import `parse_date_publication` from `parsers` (add to existing import line)
  - [ ] Call `get_coords(ad)` unconditionally before the routing branch (not just inside `else`)
  - [ ] Call `parse_date_publication(ad)` for each ad
  - [ ] Add `lat`, `lng`, `date_publication` keys to the returned dict in `rows.append({...})`
  - [ ] Preserve all existing keys: `titre`, `prix`, `superficie`, `prix_m2`, `trajet`, `lien`

- [ ] Task 3: Write tests in `tests/test_parser_enrichment.py` (AC: #1, #2, #3, #4, #5)
  - [ ] Test `parse_date_publication()` — returns string when key present
  - [ ] Test `parse_date_publication()` — returns None when key absent
  - [ ] Test `parse_date_publication()` — returns None when value is empty string/None
  - [ ] Test `get_coords()` — returns (float, float) when lat/lng present
  - [ ] Test `get_coords()` — returns (None, None) when location absent
  - [ ] Test `get_coords()` — returns (None, None) when lat/lng keys missing from location
  - [ ] Test `process()` output dict includes `lat`, `lng`, `date_publication` keys (mock `drive_time`)
  - [ ] Test `process()` output dict still includes all existing keys (mock `drive_time`)

## Dev Notes

### What This Story Does and Does NOT Include

This story enriches the scrape pipeline output dict with `lat`, `lng`, and `date_publication`. It does NOT:
- Persist these fields to the DB (Story 1.4 writes them in `save_or_merge`)
- Implement `save_or_merge` (Story 1.4)
- Modify `main.py`
- Modify `web.py` or `templates/index.html`

**Files to touch:** `parsers.py` and `database.py` (only the `process()` function and its import line). Tests go in `tests/test_parser_enrichment.py`.

### Critical: Current State of process() in database.py

`process()` currently calls `get_coords(ad)` ONLY inside the `else` branch (when the listing is not cached). The lat/lng values are used only for routing and then discarded from the output dict.

Current output dict:
```python
rows.append({
    "titre": titre,
    "prix": prix,
    "superficie": superficie,
    "prix_m2": prix_m2,
    "trajet": trajet,
    "lien": lien,
})
```

Target output dict (after this story):
```python
rows.append({
    "titre": titre,
    "prix": prix,
    "superficie": superficie,
    "prix_m2": prix_m2,
    "trajet": trajet,
    "lien": lien,
    "lat": lat,
    "lng": lng,
    "date_publication": date_publication,
})
```

### Critical: get_coords() Must Be Called Unconditionally

Currently `get_coords(ad)` is called inside the cache `else` branch. After this story it must be called for every listing so `lat`/`lng` can be included in the output dict. Refactor pattern:

```python
# Extract lat/lng unconditionally (needed for output dict)
lat, lng = get_coords(ad)

# Routing with cache check (unchanged logic)
key = hashlib.md5(f"{titre}|{superficie}".encode('utf-8')).hexdigest()
if key in existing:
    trajet = existing[key]
    print(f"  [{i}/{len(raw)}] {titre[:55]} (trajet en cache : {trajet})")
else:
    if lat and lng:
        print(f"  [{i}/{len(raw)}] {titre[:55]}")
        trajet = drive_time(lat, lng)
        time.sleep(random.uniform(0.8, 2.0))
    else:
        trajet = "N/A"
```

### date_publication Field Path in LBC JSON

LBC ads in `__NEXT_DATA__` have `first_publication_date` as a top-level field on each ad dict (alongside `subject`, `price`, `location`, `attributes`, etc.). It is a string like `"2024-01-15T10:30:00+02:00"`.

Parser function to add to `parsers.py`:
```python
def parse_date_publication(ad: dict) -> str | None:
    val = ad.get("first_publication_date")
    if not val:
        return None
    return str(val)
```

Keep it minimal — just extract and coerce to string. Do NOT reformat or parse the date (NFR8: graceful handling means return as-is or None). Story 1.4 will store it as TEXT in SQLite.

### Import Line Update in database.py

Current import line in `database.py`:
```python
from parsers import build_url, get_coords, parse_area, parse_price
```

Updated import line:
```python
from parsers import build_url, get_coords, parse_area, parse_price, parse_date_publication
```

### Testing Approach

**Pure function tests** — test `parse_date_publication()` and `get_coords()` directly in `tests/test_parser_enrichment.py` (no mocking needed):

```python
import parsers

def test_parse_date_publication_present():
    ad = {"first_publication_date": "2024-06-15T10:00:00+02:00"}
    assert parsers.parse_date_publication(ad) == "2024-06-15T10:00:00+02:00"

def test_parse_date_publication_absent():
    assert parsers.parse_date_publication({}) is None

def test_parse_date_publication_none_value():
    assert parsers.parse_date_publication({"first_publication_date": None}) is None

def test_parse_date_publication_empty_string():
    assert parsers.parse_date_publication({"first_publication_date": ""}) is None

def test_get_coords_present():
    ad = {"location": {"lat": 43.6, "lng": 1.44}}
    lat, lng = parsers.get_coords(ad)
    assert lat == 43.6
    assert lng == 1.44

def test_get_coords_missing_location():
    lat, lng = parsers.get_coords({})
    assert lat is None
    assert lng is None

def test_get_coords_missing_lat_lng():
    lat, lng = parsers.get_coords({"location": {}})
    assert lat is None
    assert lng is None
```

**Integration test for process()** — use `unittest.mock.patch` to mock `drive_time` and test output dict shape:

```python
from unittest.mock import patch
import database

def test_process_output_includes_new_fields():
    raw = [{
        "subject": "Terrain test",
        "price": [50000],
        "location": {"lat": 43.6044622, "lng": 1.4442469},
        "attributes": [{"key": "land_surface", "value_label": "500"}],
        "link": "https://www.leboncoin.fr/ad/1",
        "first_publication_date": "2024-06-15T10:00:00+02:00",
    }]
    with patch("database.drive_time", return_value="15 min"):
        with patch("database.get_existing_trajets", return_value={}):
            result = database.process(raw)
    assert len(result) == 1
    row = result[0]
    assert "lat" in row
    assert "lng" in row
    assert "date_publication" in row
    assert row["lat"] == 43.6044622
    assert row["lng"] == 1.4442469
    assert row["date_publication"] == "2024-06-15T10:00:00+02:00"
    # Existing fields preserved
    for key in ("titre", "prix", "superficie", "prix_m2", "trajet", "lien"):
        assert key in row

def test_process_output_null_gps():
    raw = [{
        "subject": "Terrain sans GPS",
        "price": [30000],
        "location": {},
        "attributes": [{"key": "land_surface", "value_label": "200"}],
        "link": "https://www.leboncoin.fr/ad/2",
    }]
    with patch("database.drive_time", return_value="N/A"):
        with patch("database.get_existing_trajets", return_value={}):
            result = database.process(raw)
    row = result[0]
    assert row["lat"] is None
    assert row["lng"] is None
    assert row["date_publication"] is None
```

### Architecture Compliance

Per the architecture document:
- `parsers.py` responsibility: "Field extraction from raw LBC JSON" — `parse_date_publication()` belongs here ✓
- `database.py` responsibility: "All SQLite operations: schema, save, merge, history" — but `process()` also lives here (existing pattern, not changed)
- `lat`/`lng` gap: "lat/lng fields are currently parsed but NOT persisted — both parsers.py output dict and database.py schema must be updated to store them" → this story fixes the dict gap; Story 1.4 handles persistence

**Do NOT:**
- Move `process()` out of `database.py` — it stays where it is
- Change `get_coords()` signature — it already returns the right tuple
- Add any new pip dependencies — `re` is already the only stdlib import needed
- Format or parse `date_publication` — store raw string as-is

### Previous Story Intelligence

**Story 1.1 (done):**
- `config.py` has `GPS_MATCH_THRESHOLD_M = 50` and `AREA_MATCH_THRESHOLD_PCT = 0.10`
- `matcher.py` at project root with `find_match(lat, lng, area, candidates) -> int | None`
- Pattern: pure functions, `snake_case`, `X | Y` type annotations (Python 3.10+)
- Tests live in `tests/` folder, pytest runner

**Story 1.2 (done):**
- `database.py` schema is complete: `annonces` has `lat`, `lng`, `status`, `first_seen`, `date_publication` columns
- `annonces_history` table exists with index on `annonce_id`
- The `save_to_database()` INSERT statement still only writes `titre, prix, superficie, prix_m2, trajet, lien, unique_key` — Story 1.4 will replace it with `save_or_merge`
- 35 tests total pass (25 matcher + 5 schema + 5 from previous runner)
- Test file: `tests/test_database_schema.py` with `tempfile.mkstemp()` pattern for isolated SQLite

**Git context (last commits):**
- `4b19125 implementation de la story 1-1` — matcher.py created
- `6d90f52 State before sprint start` — baseline

### Project Structure Notes

Only files to modify:
- `parsers.py` — add `parse_date_publication(ad)` function
- `database.py` — update import line + refactor `process()` to call `get_coords()` unconditionally + add 3 keys to output dict

New test file:
- `tests/test_parser_enrichment.py`

No other files touched. `main.py` must NOT be changed (FR12).

### FRs and NFRs Covered

| Requirement | Description |
|-------------|-------------|
| FR7 | `date_publication` extracted from LBC listing JSON |
| FR12 | All existing pipeline steps unchanged — no new CLI flags |
| NFR8 | `date_publication` gracefully handles absent `__NEXT_DATA__` date → `None`, no crash |
| NFR9 | GPS NULL handling already in `get_coords()` — output dict propagates `None` correctly |

### References

- [Architecture: Data Architecture](../../planning-artifacts/architecture.md#data-architecture) — lat/lng gap description
- [Architecture: Decision Impact Analysis](../../planning-artifacts/architecture.md#decision-impact-analysis) — implementation order step 4: parsers.py
- [Architecture: Module Boundaries](../../planning-artifacts/architecture.md#architectural-boundaries) — parsers.py responsibility
- [Epics: Story 1.3](../../planning-artifacts/epics.md#story-13-parser-enrichment) — Acceptance criteria
- [Story 1.1 completion notes](1-1-fuzzy-matcher-module.md#completion-notes-list) — config.py and matcher.py done
- [Story 1.2 completion notes](1-2-database-schema-migration.md#completion-notes-list) — schema columns done

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
