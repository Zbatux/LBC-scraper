---
title: 'Détection et marquage des annonces désactivées lors du fetch description'
slug: 'mark-deactivated-listings'
created: '2026-03-13'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3', 'Playwright', 'SQLite3', 'Flask', 'Vanilla HTML/JS (single-file)']
files_to_modify: ['descriptions.py', 'templates/index.html']
code_patterns: ['status field (TEXT) with values: new/unchanged/price_changed/reposted', 'fetch_description() returns str|None', 'CSS status badges: .status-new/.status-changed/.status-reposted/.status-unchanged', 'Status filter via <select> in #filters bar', 'statusBadge() JS function for rendering']
test_patterns: ['No tests exist in the project']
---

# Tech-Spec: Détection et marquage des annonces désactivées lors du fetch description

**Created:** 2026-03-13

## Overview

### Problem Statement

When running `--get-description`, some listings no longer exist on Leboncoin (page displays "Cette annonce est désactivée"). These listings remain in the database with a NULL description, with no way to distinguish between "not yet fetched" and "sold/deleted".

### Solution

During description fetching, detect deactivated listings (by checking for "Cette annonce est désactivée" text on the page, OR by confirming the page loaded successfully but no description container exists) and mark them with `status = 'deleted'` in the database. Display this status in the web table with a badge and provide filtering/hiding capability.

### Scope

**In Scope:**
- Detection of deactivated listings in `fetch_description()`
- Mark listing with `status = 'deleted'` in the `annonces` table
- Clear logging of the marking
- Exclude `deleted` listings from future description fetch queries
- Display "supprimée" status badge in the web table
- Filter/hide deleted listings in the web interface

**Out of Scope:**
- Physical deletion of listings from the database
- Dedicated cleanup command

## Context for Development

### Codebase Patterns

- **Status field:** `annonces.status` is an **unconstrained TEXT column** — no enum, no CHECK constraint. Already supports: `'new'`, `'unchanged'`, `'price_changed'`, `'reposted'`. Adding `'deleted'` requires **no schema migration**.
- **fetch_description():** Returns `str | None`. Currently `None` is returned both when the page loads but no description container is found (timeout at line 23-24) AND on any exception (line 49, return at line 51). No distinction between "deactivated listing" and "scraping failure".
- **fetch_all_descriptions():** Queries `WHERE description IS NULL OR description = ''` (line 58). Must also exclude `status = 'deleted'` to avoid re-checking deleted listings.
- **Web status badges:** CSS classes `.status-new`, `.status-changed`, `.status-reposted`, `.status-unchanged` with corresponding JS `statusBadge()` function (index.html line 444).
- **Status filter:** `<select id="fStatus">` in index.html (line 348-355) with options for each status. Filter applied in `getFiltered()` (line 529).
- **DB connections:** `descriptions.py` opens/closes `sqlite3` connections inline per update (no shared connection object).
- **API contract:** `/api/annonces` (web.py line 110-124) returns ALL listings with `SELECT ... FROM annonces a ORDER BY a.id` — no server-side status filtering. Deleted listings will be included in the response and filtered client-side.

### Files to Reference

| File | Purpose | Key Lines |
| ---- | ------- | --------- |
| descriptions.py | Description fetching — detection & marking point | L9-51: `fetch_description()`, L54-108: `fetch_all_descriptions()` |
| templates/index.html | Web UI — badge, filter, rendering | L444-448: `statusBadge()`, L347-355: status filter `<select>`, L500-531: `getFiltered()`, L155-163: status CSS |
| web.py | API — confirms no server-side status filter | L110-124: `get_annonces()` returns all rows |

### Technical Decisions

- **Use `status = 'deleted'`** to stay consistent with existing status values. No schema migration needed (TEXT column).
- **Detection strategy (two-pronged):**
  1. **Primary:** Check for "Cette annonce est désactivée" text in the page after load. If found → deactivated.
  2. **Fallback:** If the deactivation text is NOT found AND the description container is also not found (after timeout), the page loaded successfully but has no listing content → treat as deactivated.
  3. **Exception = retry:** If `fetch_description()` throws an exception (network error, Playwright crash, `accept_cookies()` failure), it returns `None` via the existing except block. `None` means "retry next run", NOT "deleted".
- **Module-level constant:** Define `DELETED_SENTINEL = "__DELETED__"` at the top of `descriptions.py` to avoid magic string typos. Both the return and the comparison use this constant.
- **No database.py changes needed:** The status UPDATE is a simple inline SQL in `descriptions.py`, same pattern as the existing description UPDATE (lines 94-100).
- **Hide deleted checkbox:** NOT checked by default — consistent with the existing "Masquer nogo" checkbox behavior.
- **Dropdown/checkbox interaction:** When the user selects "Supprimée" in the status dropdown, auto-uncheck "Masquer supprimées" to avoid conflicting filters showing an empty table.

## Implementation Plan

### Tasks

- [ ] Task 1: Define sentinel constant and add deactivation detection in `fetch_description()`
  - File: `descriptions.py`
  - Action:
    1. Add a module-level constant at the top of the file (after imports): `DELETED_SENTINEL = "__DELETED__"`
    2. After the page loads (line 12) and cookies are accepted (line 13), check if the page contains the deactivation text using `page.locator("text=Cette annonce est désactivée").count()`. If count > 0, return `DELETED_SENTINEL` immediately (skip description extraction).
    3. If the deactivation text is NOT found, proceed to the existing `wait_for_selector` (line 23). If the selector times out (existing `except PWTimeout: pass` at line 24-25) AND the description locator finds nothing (line 47: `desc_loc.count()` is 0), return `DELETED_SENTINEL` instead of `None`.
  - Notes: The deactivation text check MUST happen BEFORE `wait_for_selector` to avoid a useless 5-second wait. The fallback at step 3 handles deactivated pages that don't show the expected text (different layout, language, etc.). Exceptions still return `None` (retry).

- [ ] Task 2: Handle the `DELETED_SENTINEL` in `fetch_all_descriptions()`
  - File: `descriptions.py`
  - Action: In the loop at line 90-104, after calling `fetch_description()`, restructure the conditional as follows (ORDER IS CRITICAL):
    1. **First check:** `if description == DELETED_SENTINEL:` — execute `UPDATE annonces SET status = 'deleted', description = NULL WHERE id = ?`, print `"    🗑 Annonce désactivée, marquée comme supprimée"`, increment a new `deleted` counter (initialized to 0 before the loop).
    2. **Second check:** `elif description:` — update description as before (existing behavior, lines 94-100), increment `updated`.
    3. **Else (None):** do nothing (existing behavior — scraping failure, will retry next run).
  - Notes: The `DELETED_SENTINEL` check MUST come before `if description:` because the sentinel is a truthy non-empty string — if checked after, it would be written as literal description text. Use the same inline `sqlite3.connect` / `commit` / `close` pattern. Setting `description = NULL` ensures consistent DB state for deleted listings.

- [ ] Task 3: Exclude deleted listings from the description fetch query
  - File: `descriptions.py`
  - Action: Change the SQL query at line 58 from:
    `SELECT id, lien FROM annonces WHERE description IS NULL OR description = ''`
    to:
    `SELECT id, lien FROM annonces WHERE (description IS NULL OR description = '') AND (status IS NULL OR status != 'deleted')`
  - Notes: This prevents re-checking listings already marked as deleted. If a previously deleted listing is reposted, `save_or_merge()` in `database.py` will set its status to `'reposted'` and it will naturally re-enter the description fetch queue since `status != 'deleted'`.

- [ ] Task 4: Update the summary log line
  - File: `descriptions.py`
  - Action: Update the final print at line 108 to include deleted count:
    `print(f"  ✓ {updated}/{len(todo)} descriptions ajoutées, {deleted} annonce(s) supprimée(s).")`

- [ ] Task 5: Add CSS for the `deleted` status badge
  - File: `templates/index.html`
  - Action: Add a new CSS class after the existing status badge classes (after line 163):
    `.status-deleted { background: #fee2e2; color: #991b1b; }`
  - Notes: Red tones to visually distinguish deleted listings.

- [ ] Task 6: Add `'deleted'` case to `statusBadge()` JS function
  - File: `templates/index.html`
  - Action: In the `statusBadge()` function (line 444-448), add before the default return:
    `if (status === 'deleted') return '<span class="status-badge status-deleted">supprimée</span>';`

- [ ] Task 7: Add `'deleted'` option to the status filter dropdown
  - File: `templates/index.html`
  - Action: In the `<select id="fStatus">` (line 348-355), add a new option:
    `<option value="deleted">Supprimée</option>`

- [ ] Task 8: Add "Masquer supprimées" checkbox filter with dropdown interaction
  - File: `templates/index.html`
  - Action:
    1. Add a new checkbox in the `#filters` div, after the existing "Masquer nogo" checkbox (after line 308):
       `<label><input type="checkbox" id="hideDeleted" /> Masquer supprimées</label>`
       (NOT checked by default — consistent with "Masquer nogo")
    2. In `getFiltered()` function, add a filter line after the `hideNogo` check (after line 517):
       `const hideDeleted = document.getElementById("hideDeleted").checked;`
       `if (hideDeleted && a.status === 'deleted') return false;`
    3. Add `"hideDeleted"` to the filter event listeners array at line 994 (input) and line 996 (change).
    4. In the `resetFilters` handler (line 999-1006), reset this checkbox to unchecked (consistent with `hideNogo`):
       `document.getElementById("hideDeleted").checked = false;`
    5. Add dropdown/checkbox interaction: in the `fStatus` change listener, when the value is `"deleted"`, auto-uncheck `hideDeleted` and re-render. Add this logic in the existing change event for `fStatus`:
       ```js
       document.getElementById("fStatus").addEventListener("change", () => {
         if (document.getElementById("fStatus").value === "deleted") {
           document.getElementById("hideDeleted").checked = false;
         }
         render();
       });
       ```
       Note: this replaces the existing generic change listener for `fStatus` in the array at line 996 — extract `fStatus` from that array and bind it separately.

### Acceptance Criteria

- [ ] AC1: Given a listing that is deactivated on Leboncoin (page shows "Cette annonce est désactivée"), when `--get-description` processes it, then the listing's `status` is set to `'deleted'` in the database, `description` is set to `NULL`, and a log message "🗑 Annonce désactivée, marquée comme supprimée" is printed.

- [ ] AC2: Given a listing with `status = 'deleted'` in the database, when `--get-description` is run again, then this listing is NOT included in the fetch queue.

- [ ] AC3: Given a listing with `status = 'deleted'`, when the web interface loads, then a red "supprimée" badge is displayed in the Status column.

- [ ] AC4: Given the web interface with default settings, when the page loads, then listings with `status = 'deleted'` are visible (checkbox "Masquer supprimées" is unchecked by default).

- [ ] AC5: Given the web interface with "Masquer supprimées" checked, when viewing the table, then deleted listings are hidden.

- [ ] AC6: Given the status filter dropdown, when "Supprimée" is selected, then only listings with `status = 'deleted'` are shown AND the "Masquer supprimées" checkbox is automatically unchecked.

- [ ] AC7: Given a listing where `fetch_description()` throws an exception (network error, Playwright failure, `accept_cookies()` crash, detached frame), when `--get-description` processes it, then the listing is NOT marked as deleted (returns `None` via existing except block, will retry on next run).

- [ ] AC8: Given a listing where the page loads successfully, no "Cette annonce est désactivée" text is found, OR no description container is found (timeout), when `--get-description` processes it, then the listing IS marked as deleted (fallback detection).

## Additional Context

### Dependencies

None — uses existing infrastructure only. No new packages or services required. No schema migration needed (`status` is an unconstrained TEXT column).

### Testing Strategy

Manual testing:
1. Insert or identify a deactivated listing URL in the database (description NULL)
2. Run `python main.py --get-description`
3. Verify in the console log that the deactivated listing is detected and marked
4. Verify in the database: `SELECT id, status, description FROM annonces WHERE status = 'deleted'` — status should be `'deleted'`, description should be `NULL`
5. Run `--get-description` again → verify the deleted listing is NOT re-processed
6. Run `python main.py --web` → verify the badge, checkbox filter, dropdown filter, and dropdown/checkbox interaction work
7. Select "Supprimée" in dropdown → verify "Masquer supprimées" auto-unchecks

### Known Limitations

- **No retry cap:** Listings that perpetually return `None` (e.g., geo-blocked, CAPTCHA wall) will be retried on every `--get-description` run indefinitely. This is a pre-existing issue not addressed by this spec. A future enhancement could add a `fetch_attempts` counter or a `status = 'fetch_failed'` after N retries.

### Notes

- The user noted that keeping deleted listings is valuable because it can indicate the property was sold
- The screenshot shows the exact Leboncoin deactivation page with text "Cette annonce est désactivée"
- The deactivation page has no description container, so both detection methods (text check and container absence) converge
- If a previously deleted listing is reposted by the seller, `save_or_merge()` in `database.py` will set its status to `'reposted'`, which allows it to re-enter the description fetch queue naturally (since `status != 'deleted'`)
- The `DELETED_SENTINEL` constant prevents magic string typos — both the return point in `fetch_description()` and the comparison in `fetch_all_descriptions()` reference the same constant
