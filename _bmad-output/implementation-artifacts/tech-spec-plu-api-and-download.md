---
title: 'PLU API and One-Click Download'
slug: 'plu-api-and-download'
created: '2026-03-14'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: [Python, Flask, requests, JavaScript, HTML, CSS]
files_to_modify: [config.py, plu.py, web.py, templates/index.html, tests/test_plu.py]
code_patterns: [dedicated-module-pattern, flask-route-pattern, requests-session-pattern, actions-column-button]
test_patterns: [pytest, integration-tests-with-real-apis, flask-test-client]
---

# Tech-Spec: PLU API and One-Click Download

**Created:** 2026-03-14

## Overview

### Problem Statement

When browsing land listings in the web UI, there is no way to access the PLU (Plan Local d'Urbanisme) document for a given plot's commune. Users must manually search government portals to find the applicable zoning document.

### Solution

Create a `plu.py` module that chains calls to 3 public APIs (geo.api.gouv.fr → geoportail-urbanisme documents → details) to resolve a commune's active PLU and its download URL. Expose a Flask route `GET /plu` in `web.py`. Add a "PLU" button in the web UI that calls this endpoint using the listing's GPS coordinates and triggers the ZIP file download.

### Scope

**In Scope:**
- Module `plu.py`: chained API calls to resolve commune → active PLU document → archiveUrl
- Flask route `GET /plu?lat=&lon=` and `GET /plu?commune=` in `web.py`
- Business rules: filter `document.production`, priority PLUi > PLU > POS > CC
- "PLU" button in web UI → calls endpoint → triggers ZIP download
- Error handling: commune without PLU (RNU), archiveUrl null, API unreachable
- Integration test verifying a downloadable link is returned (Nègrepelisse)

**Out of Scope:**
- Database storage of PLU data
- Filtering by PLU zone in the UI
- Response caching

## Context for Development

### Codebase Patterns

- **Dedicated modules**: each concern gets its own file (`routing.py` for OSRM travel time, `matcher.py` for GPS similarity, `parsers.py` for extraction). `plu.py` follows this pattern.
- **`requests.Session()`**: `routing.py` uses a module-level session with custom User-Agent and timeout. `plu.py` should follow the same pattern.
- **Flask routes**: `web.py` imports modules (e.g. `import matcher`) and calls their functions from route handlers. Routes return `jsonify()`. Errors return `jsonify({"error": "..."}), status_code`. Note: `web.py` does NOT import `routing` — that module is used by `database.py` during scraping. The precedent for `import plu` in `web.py` is `import matcher`.
- **Frontend**: vanilla JS in `templates/index.html`, no build step. Actions column has conditional buttons (`hist-btn`, `cmp-btn`). For PLU download, a simple button that calls `/plu?lat=&lon=` and redirects to `archive_url` on success.
- **Tests**: `tests/` directory, pytest, `test_web_api.py` uses Flask test client. PLU test will be a real API integration test.

### Files to Reference

| File | Purpose | Anchor |
| ---- | ------- | ------ |
| routing.py | Reference pattern for dedicated API module — `requests.Session()`, timeout, error handling | Full file (24 lines) |
| web.py | Flask app — where to add `/plu` route | search: `# Routes` |
| web.py | `app.run()` — confirms port 5000 | search: `if __name__` |
| templates/index.html | Frontend — actions column where PLU button goes | search: `cmp-btn` in render() |
| templates/index.html | `bindRowEvents()` — where PLU click handler goes | search: `function bindRowEvents` |
| tests/test_web_api.py | Test patterns — pytest fixtures, Flask test client | Full file |

### Technical Decisions

- **Flask** (not FastAPI): project already uses Flask, stay consistent
- **Dedicated module `plu.py`**: follows project pattern (routing.py, matcher.py, etc.)
- **Server-side API calls**: avoids CORS issues with government APIs, keeps logic testable in Python
- **Same port (5000)**: no separate service, just a new route on the existing Flask app
- **Download via hidden `<a>` click**: frontend calls `/plu?lat=&lon=`, gets `archive_url` in JSON, then creates a temporary `<a href="..." target="_blank">` element and clicks it programmatically. This avoids popup blocker issues that occur with `window.open()` after an async `fetch()` gap.
- **`requests.Session()`** with timeout: follows `routing.py` pattern for resilience

## Implementation Plan

### Tasks

- [x] Task 0: Add PLU API URLs to config
  - File: `config.py`
  - Action: Add constants at the end of the file:
    ```python
    GEO_API_COMMUNES_URL = "https://geo.api.gouv.fr/communes"
    GPU_DOCUMENT_URL = "https://www.geoportail-urbanisme.gouv.fr/api/document"
    ```
  - Notes: `plu.py` will import these and build full URLs from them. Follows existing pattern (`SEARCH_URL` in config.py, `TOULOUSE_LAT/LNG` imported by `routing.py`).

- [x] Task 1: Create `plu.py` module — commune resolution
  - File: `plu.py` (new)
  - Action: Create module with `requests.Session()` (User-Agent, timeout=12) and a function `resolve_commune(lat, lon, commune)` that:
    - If `lat` and `lon` provided (takes precedence): call `https://geo.api.gouv.fr/communes?lat={lat}&lon={lon}&fields=nom,code&limit=1`, extract `code` (INSEE) and `nom`
    - Else if `commune` provided: call `https://geo.api.gouv.fr/communes?nom={commune}&fields=nom,code&limit=1`, extract `code` and `nom`
    - Return `(code_insee, nom)` tuple
    - Raise `ValueError` if no commune found
  - Notes: Follow `routing.py` pattern — module-level `_sess = requests.Session()`. Import API base URLs from `config.py` (see Task 0).

- [x] Task 2: Add PLU document lookup function
  - File: `plu.py`
  - Action: Add function `find_active_plu(code_insee)` that:
    1. Calls `https://www.geoportail-urbanisme.gouv.fr/api/document?grid={code_insee}`
    2. Filters response for `status == "document.production"`
    3. Among active documents, selects by priority: PLUi > PLU > POS > CC (use ordered list `["PLUi", "PLU", "POS", "CC"]`, take first match)
    4. Returns the selected document dict (containing `id`, `type`, `datApprobation`, `datPublication`)
    5. Returns `None` if no active document found (commune at RNU)
  - Notes: The API returns a list of document objects. Each has `type`, `status`, `id` fields.

- [x] Task 3: Add archive URL resolution function
  - File: `plu.py`
  - Action: Add function `get_archive_url(document_id)` that:
    1. Calls `https://www.geoportail-urbanisme.gouv.fr/api/document/{document_id}/details`
    2. Extracts `archiveUrl` from the response JSON
    3. Returns the URL string or `None` if absent/null
  - Notes: The details endpoint returns a single document object with additional fields including `archiveUrl`

- [x] Task 4: Add main orchestration function
  - File: `plu.py`
  - Action: Add function `get_plu_info(lat=None, lon=None, commune=None)` that:
    1. Validates inputs: must have either (`lat` + `lon`) or `commune`, not neither. If both are provided, `lat`+`lon` takes precedence (GPS is more precise than commune name matching)
    2. Calls `resolve_commune()` to get `code_insee` and `nom`
    3. Calls `find_active_plu(code_insee)` — if None, return error dict `{"error": "Aucun PLU trouvé pour cette commune (commune au RNU)"}`
    4. Calls `get_archive_url(document_id)` — if None, return error dict `{"error": "Archive PLU non disponible pour ce document"}`
    5. Returns success dict:
       ```python
       {
           "commune": nom.upper(),
           "code_insee": code_insee,
           "type": document["type"],
           "date_approbation": document.get("datApprobation"),
           "date_publication": document.get("datPublication"),
           "archive_url": archive_url,
       }
       ```
    6. Wraps all external calls in try/except:
       - On `ValueError` (from `resolve_commune`): return `{"error": "Commune introuvable"}`
       - On `requests.RequestException`: return `{"error": "Erreur lors de la communication avec les APIs d'urbanisme"}`

- [x] Task 5: Add Flask route `GET /plu`
  - File: `web.py`
  - Action:
    1. Add `import plu` at top of file (after existing imports)
    2. Add route before the `# Startup` section:
       ```python
       @app.route("/plu", methods=["GET"])
       def get_plu():
           lat = request.args.get("lat", type=float)
           lon = request.args.get("lon", type=float)
           commune = request.args.get("commune")
           if not commune and (lat is None or lon is None):
               return jsonify({"error": "Provide lat+lon or commune parameter"}), 400
           result = plu.get_plu_info(lat=lat, lon=lon, commune=commune)
           if "error" in result:
               return jsonify(result), 404
           return jsonify(result)
       ```
  - Notes: Insert after the `update_annonce` route, before the `# Startup` comment block

- [x] Task 6: Add PLU button CSS
  - File: `templates/index.html` — inside `<style>` block, after `.cmp-worst` rule (last compare modal style, before `</style>`)
  - Action: Add CSS for `.plu-btn`:
    ```css
    .plu-btn {
      padding: 3px 8px; background: #d97706; color: #fff; border: none;
      border-radius: 4px; font-size: 11px; cursor: pointer; white-space: nowrap;
      font-weight: 600;
    }
    .plu-btn:hover { background: #b45309; }
    .plu-btn:disabled { opacity: .5; cursor: not-allowed; }
    ```

- [x] Task 7: Add PLU button in actions column
  - File: `templates/index.html` — inside `render()` function (search for `cmp-btn` in template literal)
  - Action: Add PLU button after the compare button, conditional on `lat` and `lng`:
    ```js
    ${a.lat != null && a.lng != null
      ? ` <button class="plu-btn" data-lat="${a.lat}" data-lng="${a.lng}">PLU</button>`
      : ""
    }
    ```
  - Notes: Use `data-lat` and `data-lng` attributes directly — no need for `data-id` lookup since we call `/plu` with coords

- [x] Task 8: Add PLU button click handler
  - File: `templates/index.html` — inside `bindRowEvents()` function, after the `.cmp-btn` listener block
  - Action: Add event listener for `.plu-btn` buttons:
    ```js
    document.querySelectorAll(".plu-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        btn.disabled = true;
        btn.textContent = "…";
        try {
          const res = await fetch(`/plu?lat=${btn.dataset.lat}&lon=${btn.dataset.lng}`);
          const data = await res.json();
          if (data.error) {
            alert(data.error);
          } else if (data.archive_url) {
            const a = document.createElement("a");
            a.href = data.archive_url;
            a.target = "_blank";
            a.rel = "noopener";
            document.body.appendChild(a);
            a.click();
            a.remove();
          } else {
            alert("Archive PLU non disponible");
          }
        } catch (err) {
          alert("Erreur lors de la récupération du PLU");
        } finally {
          btn.disabled = false;
          btn.textContent = "PLU";
        }
      });
    });
    ```
  - Notes: Button disabled during fetch to prevent duplicate requests. Hidden `<a>` element click avoids popup blocker issues with async `window.open()`.

- [x] Task 9: Create integration test
  - File: `tests/test_plu.py` (new)
  - Action: Create pytest test file with `@pytest.mark.integration` marker:
    1. **test_plu_by_commune_negrepelisse**: call `plu.get_plu_info(commune="Negrepelisse")`, assert response has `archive_url` starting with `https://`, `code_insee` == `"82134"`, `commune` == `"NEGREPELISSE"`, `type` in `["PLU", "PLUi", "POS", "CC"]`
    2. **test_plu_by_coords_negrepelisse**: call `plu.get_plu_info(lat=44.075, lon=1.522)`, assert same `code_insee` as commune test (`"82134"`), assert `archive_url` starts with `https://`
    3. **test_plu_commune_and_coords_same_result**: verify both methods return the same `archive_url`
    4. **test_plu_nonexistent_commune**: call with `commune="Zzzznotacommune"`, assert `"error"` key in response
    5. **test_plu_ocean_coords**: call with `lat=0.0, lon=0.0`, assert `"error"` key in response
    6. **test_archive_url_is_downloadable**: call `plu.get_plu_info(commune="Negrepelisse")`, then `requests.head(archive_url)` and assert HTTP status is 200 or 302
  - Notes: Mark all tests `@pytest.mark.integration`. Run with `pytest tests/test_plu.py -v -m integration`

### Acceptance Criteria

- [x] AC 1: Given valid GPS coordinates (lat=44.075, lon=1.522), when calling `GET /plu?lat=44.075&lon=1.522`, then response contains `commune`, `code_insee`, `type`, `date_approbation`, `date_publication`, and `archive_url` fields
- [x] AC 2: Given a valid commune name ("Negrepelisse"), when calling `GET /plu?commune=Negrepelisse`, then response returns the same PLU info as the GPS-based query for the same commune
- [x] AC 3: Given a commune at RNU (no urbanisme document), when calling `GET /plu?commune=<rnu_commune>`, then response returns `{"error": "Aucun PLU trouvé pour cette commune (commune au RNU)"}` with HTTP 404
- [x] AC 4: Given no parameters provided, when calling `GET /plu`, then response returns `{"error": "Provide lat+lon or commune parameter"}` with HTTP 400
- [x] AC 5: Given a listing with lat/lng in the web UI, when viewing the table, then a "PLU" button (amber/orange) is visible in the Actions column
- [x] AC 6: Given a listing without lat/lng (null), when viewing the table, then no PLU button is displayed for that row
- [x] AC 7: Given a listing with valid coords, when clicking the PLU button, then the button shows "…" and is disabled during loading, then the PLU ZIP file download is triggered in a new tab
- [x] AC 8: Given the external APIs are unreachable, when clicking the PLU button, then an alert displays an error message instead of crashing
- [x] AC 9: Given the archive_url returned by the API, when performing an HTTP HEAD request on it, then the server responds with 200 or 302 (confirming the file is downloadable)
- [x] AC 10: Given multiple active documents exist for a commune, when resolving the PLU, then the document with highest priority type is selected (PLUi > PLU > POS > CC)

## Additional Context

### Dependencies

- External API: `https://geo.api.gouv.fr/communes` (free, no key) — commune resolution
- External API: `https://www.geoportail-urbanisme.gouv.fr/api/document` (free, no key) — PLU document lookup
- External API: `https://www.geoportail-urbanisme.gouv.fr/api/document/{id}/details` (free, no key) — archive URL
- `requests` library (already in requirements.txt)
- No new dependencies needed

### Testing Strategy

- **Automated integration tests** (`tests/test_plu.py`):
  - Validates full PLU resolution chain with known commune (Nègrepelisse, code INSEE 82134)
  - Tests both input modes: GPS coordinates and commune name
  - Verifies archive_url is a real downloadable link (HTTP HEAD check)
  - Tests error cases: nonexistent commune, ocean coordinates
  - Marked `@pytest.mark.integration` — requires network access
  - Run with: `pytest tests/test_plu.py -v -m integration`

- **Manual browser testing:**
  1. Load web UI, verify PLU button appears on rows with GPS coordinates
  2. Click PLU on a listing — verify download triggers in new tab
  3. Verify button shows "…" and is disabled during loading
  4. Test with a commune known to be at RNU — verify alert with clear error
  5. Disconnect network — verify alert with error message

### Notes

- Priority order for document types: PLUi > PLU > POS > CC
- Only documents with `status == "document.production"` are active
- Some communes have no urbanisme document (RNU) — return clear error
- `archiveUrl` may be null in the details response
- The `geo.api.gouv.fr` API supports both `nom` (commune name) and `lat`/`lon` query parameters
- The geoportail-urbanisme document list may return documents with various statuses (`document.production`, `document.deleted`, etc.) — only `document.production` is relevant

## Review Notes
- Adversarial review completed
- Findings: 13 total, 6 fixed, 7 skipped (by design / existing pattern / out of scope)
- Resolution approach: auto-fix
- Fixed: F1 (encodeURIComponent), F3 (HTTP 502 for API errors), F6 (exception logging), F10 (URL scheme validation), F11 (fallback for unknown doc types), F12 (docstring updated)
