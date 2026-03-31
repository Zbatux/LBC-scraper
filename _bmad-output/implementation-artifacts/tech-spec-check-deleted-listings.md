---
title: 'Check & Flag Deleted Listings'
slug: 'check-deleted-listings'
created: '2026-03-17'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.10+', 'Playwright', 'SQLite']
files_to_modify: ['main.py', 'descriptions.py', 'browser.py']
code_patterns: ['argparse CLI flags', 'Playwright anti-bot browser setup', 'raw SQLite with inline connections', 'DELETED_SENTINEL pattern']
test_patterns: ['none — no automated tests in project']
---

# Tech-Spec: Check & Flag Deleted Listings

**Created:** 2026-03-17

## Overview

### Problem Statement

Currently, detection of disabled/deleted listings on Leboncoin is coupled with description fetching (`--get-description`) and only checks listings that have no description yet. There is no way to verify whether already-processed listings are still online. Over time, the database accumulates stale listings that no longer exist on Leboncoin.

### Solution

Add a new CLI flag `--check-status` that iterates through all non-deleted listings, visits their URL via Playwright, and flags any listing displaying "Cette annonce est désactivée" with `status='deleted'`. The function must distinguish between a genuinely active listing and a page blocked by anti-bot (DataDome 403/captcha), to avoid silently treating blocked pages as "online."

### Scope

**In Scope:**
- New `--check-status` CLI flag in `main.py`
- New function to check all listings where `status != 'deleted'`
- Reuse of existing Playwright pattern (one-by-one, same anti-bot handling)
- Update `status` field in database to `'deleted'` when listing is disabled
- Extract shared Playwright browser setup into `browser.py` to eliminate duplication

**Out of Scope:**
- No batching or parallelism
- No notifications
- No web UI modifications
- No changes to existing `--get-description` flow
- No handling of re-listed ads (listings marked `'deleted'` stay deleted — a re-posted ad would appear as a new listing via `--scrape` with a different `list_id`)

## Context for Development

### Codebase Patterns

- CLI uses `argparse` in `main.py` with flags: `--scrape`, `--get-description`, `--analyze`, `--export-csv`, `--web`
- The "no flags" guard near the top of `main()` chains all flags with `and not` — if none are set, it prints help and returns
- Playwright browser setup is currently duplicated between `main.py` (inside `--scrape` block) and `descriptions.py` (`fetch_all_descriptions`) with near-identical parameters (headless=False, slow_mo=50/60, anti-bot user agent, webdriver masking)
- `browser.py` defines `accept_cookies()` which handles cookie modals (including "cookies solidaires" second modal)
- Deletion detection in `descriptions.py`: `fetch_description()` checks `page.locator("text=Cette annonce est désactivée").count()` and returns `DELETED_SENTINEL`
- Database uses inline `sqlite3.connect()` calls per operation (no shared connection pattern)
- Status field values: `'new'`, `'unchanged'`, `'price_changed'`, `'reposted'`, `'deleted'`, or `NULL` (legacy rows from before the status column migration)
- Progress logging pattern: `[i/total] url_truncated` then indented result line

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `main.py` | CLI entry point — add new `--check-status` flag, refactor to use shared browser setup |
| `descriptions.py` | Existing deletion detection + `fetch_all_descriptions` to reuse/reference, refactor to use shared browser setup |
| `browser.py` | `accept_cookies()` helper — add shared `create_browser_context()` helper here |
| `database.py` | Schema reference (status column migration) |

### Technical Decisions

- **Extract shared browser setup** into `browser.py` as `create_browser_context(pw)` → returns `(browser, context, page)`. Refactor `fetch_all_descriptions` and `main.py --scrape` to use it. This eliminates triple duplication (F3).
- Create `check_listing_status(page, url, is_first_page)` in `descriptions.py` — lightweight function that only checks for disabled banner
- Create `check_all_statuses(db_name)` in `descriptions.py` — orchestrator that uses a single SQLite connection for all updates (F8)
- **Anti-bot detection** (F10): `check_listing_status` must verify the page actually loaded a valid listing before concluding it's online. Check for known listing page markers (e.g., `[data-qa-id='adview_description_container']`, ad title selectors, or the disabled banner). If none are found, treat as "inconclusive" (log warning, skip — don't mark as deleted or as online).

## Implementation Plan

### Tasks

- [x] Task 1: Extract shared Playwright browser setup into `browser.py`
  - File: `browser.py`
  - Action: Add a new function at the end of the file:
    ```python
    def create_browser_context(pw, slow_mo: int = 50):
        """Create a Playwright browser + context + page with anti-bot settings."""
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=slow_mo,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return browser, ctx, page
    ```
  - Notes: `slow_mo` defaults to 50 (used by descriptions). `main.py --scrape` uses 60 and can pass `slow_mo=60`.

- [x] Task 2: Refactor `fetch_all_descriptions()` in `descriptions.py` to use `create_browser_context`
  - File: `descriptions.py`
  - Action: Replace the inline Playwright setup (the `pw.chromium.launch(...)` through `page.add_init_script(...)` block) with:
    ```python
    from browser import accept_cookies, create_browser_context
    # ...
    browser, ctx, page = create_browser_context(pw)
    ```
  - Notes: Also refactor to use a single SQLite connection for the entire loop instead of open/close per update. Open connection before the loop, commit after each update, close after the loop.

- [x] Task 3: Refactor `main.py --scrape` block to use `create_browser_context`
  - File: `main.py`
  - Action: Replace the inline Playwright setup in the `--scrape` block with:
    ```python
    from browser import create_browser_context
    # ...
    browser, ctx, page = create_browser_context(pw, slow_mo=60)
    ```

- [x] Task 4: Add `check_listing_status()` function to `descriptions.py`
  - File: `descriptions.py`
  - Action: Add a new function after `fetch_description()` that checks if a listing is disabled
  - Details:
    ```python
    def check_listing_status(page: Page, url: str, is_first_page: bool = False) -> str:
        """Visit a listing URL and check if it is disabled.

        Returns:
            'deleted'      — listing shows "Cette annonce est désactivée"
            'online'       — listing page loaded with valid content
            'inconclusive' — page did not load properly (anti-bot block, network error)
        """
    ```
  - Logic:
    1. `page.goto(url, wait_until="domcontentloaded", timeout=60_000)`
    2. `accept_cookies(page, is_first_page=is_first_page)`
    3. Check for disabled banner: `page.locator("text=Cette annonce est désactivée").count()` → if found, return `'deleted'`
    4. Check for valid listing markers: `page.locator("[data-qa-id='adview_description_container'], [data-testid='description'], [class*='Description'], div[itemprop='description'], [data-qa-id='adview_title']")` — if any found, return `'online'`
    5. If neither disabled banner nor valid markers → return `'inconclusive'`
  - Error handling: wrap in try/except, log error with `print(f"    ⚠ Erreur vérification ({url[:60]}): {e}")`, return `'inconclusive'`
  - Include random delay (800-1500ms) after page load like `fetch_description`

- [x] Task 5: Add `check_all_statuses()` function to `descriptions.py`
  - File: `descriptions.py`
  - Action: Add a new function after `check_listing_status()` that orchestrates the full check
  - Details:
    ```python
    def check_all_statuses(db_name: str = "lbc_data.db"):
        """Check all non-deleted listings and flag disabled ones as deleted."""
    ```
  - SQL query: `SELECT id, lien FROM annonces WHERE (status IS NULL OR status != 'deleted')`
  - Empty result handling: if no rows, print `"  Aucune annonce à vérifier."` and return
  - Playwright setup: use `create_browser_context(pw)`
  - SQLite: open a single connection before the loop, commit after each UPDATE, close after the loop
  - Loop pattern:
    - Call `check_listing_status(page, lien, is_first_page=(i == 1))`  — pass `is_first_page=True` only for the first iteration
    - If `'deleted'` → `UPDATE annonces SET status = 'deleted' WHERE id = ?`, increment `deleted` counter, log `🗑 Annonce désactivée, marquée comme supprimée`
    - If `'online'` → log `✓ En ligne`
    - If `'inconclusive'` → increment `skipped` counter, log `⚠ Page non vérifiable (anti-bot ou erreur), ignorée`
  - Progress logging: `[i/total] lien[:70]` then indented result line
  - Summary line: `✓ Vérification terminée : {deleted} supprimée(s), {skipped} ignorée(s) sur {total} vérifiée(s).`
  - Random delay between pages: `random.randint(2000, 5000)` ms

- [x] Task 6: Add `--check-status` CLI flag to `main.py`
  - File: `main.py`
  - Action 1: Update import to add `check_all_statuses`:
    ```python
    from descriptions import fetch_all_descriptions, check_all_statuses
    ```
  - Action 2: Add argparse argument after the `--analyze` argument block:
    ```python
    parser.add_argument(
        "--check-status",
        action="store_true",
        help="Vérifie si les annonces sont toujours en ligne et marque les désactivées.",
    )
    ```
  - Action 3: Update the "no flags" guard (the `if not args.scrape and not args.export_csv and ...` condition) to include `and not args.check_status`
  - Action 4: Add execution block after the `--get-description` block and **before** the `--analyze` block:
    ```python
    if args.check_status:
        print("\nVérification du statut des annonces...")
        check_all_statuses()
    ```
  - Notes: Placed before `--analyze` so the execution order when combining flags is: scrape → get-description → **check-status** → analyze → web. This avoids double-visiting if `--get-description` already marked some as deleted (F14).

### Acceptance Criteria

- [ ] AC 1: Given a database with active listings, when running `python main.py --check-status`, then each listing URL is visited via Playwright and active listings remain unchanged in the database.
- [ ] AC 2: Given a database containing a listing that has been disabled on Leboncoin, when running `--check-status`, then that listing's status is updated to `'deleted'` in the database.
- [ ] AC 3: Given a database where some listings already have `status='deleted'`, when running `--check-status`, then those listings are skipped (not visited).
- [ ] AC 4: Given a network error or page load failure on one listing, when running `--check-status`, then the error is logged with a warning message, that listing is skipped (marked inconclusive), and processing continues with the next listing.
- [ ] AC 5: Given a database with no non-deleted listings (either empty or all deleted), when running `--check-status`, then the message "Aucune annonce à vérifier." is displayed and the program exits cleanly.
- [ ] AC 6: Given a DataDome anti-bot block (403/captcha) on a listing page, when running `--check-status`, then that listing is logged as inconclusive (not falsely marked as online or deleted) and processing continues.
- [ ] AC 7: Given `--get-description --check-status` combined, when running, then descriptions are fetched first (marking deleted ones), and `--check-status` runs after, skipping already-deleted listings.
- [ ] AC 8: Given the refactored `create_browser_context()` in `browser.py`, when running `--scrape` or `--get-description`, then they behave identically to before (no regression).

## Additional Context

### Dependencies

- Playwright (already installed)
- No new dependencies required

### Testing Strategy

- Manual testing:
  1. Run `--check-status` on a database with known active listings → verify they remain unchanged
  2. Run `--check-status` on a database with a known deleted listing on Leboncoin → verify `status` changes to `'deleted'`
  3. Run `--check-status` on an empty database → verify clean exit with "Aucune annonce à vérifier."
  4. Run `--check-status` then verify already-deleted listings are not re-visited on a second run
  5. Run `--get-description` then `--check-status` combined → verify no double visits for newly deleted
  6. Run `--scrape` after refactor → verify no regression in scraping behavior
  7. Run `--get-description` after refactor → verify no regression in description fetching

### Notes

- The `fetch_description` function already handles deleted detection but also does unnecessary description extraction. The new `check_listing_status` is deliberately lighter — it only checks for the disabled banner and returns immediately.
- The query uses `status IS NULL OR status != 'deleted'` to handle legacy rows with `NULL` status that predate the status column migration.
- **Re-listed ads**: Listings marked `'deleted'` stay deleted. If a seller re-posts the same property, it gets a new `list_id` and will appear as a new listing via `--scrape`. This is by design — the old listing genuinely was disabled.
- **Anti-bot resilience**: The three-state return (`deleted`/`online`/`inconclusive`) ensures that DataDome blocks or network errors never silently corrupt the database. Inconclusive listings are simply retried on the next run.
- Future consideration: if the number of listings grows large, a `--check-status --limit N` option could be added to process in batches. This is out of scope for now.

## Review Notes
- Adversarial review completed
- Findings: 8 total, 6 fixed, 2 skipped (F7 out of scope, F8 pre-existing pattern)
- Resolution approach: auto-fix
- Key fixes: try/finally for resource cleanup (F1/F2), multiple disabled text variants (F3), wait_for_selector before checks (F4), tightened CSS selectors (F6)
