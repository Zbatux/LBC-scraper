---
title: 'Scraping Improvements - Cookie Auto-dismiss & Timing Optimization'
slug: 'scraping-cookie-timing'
created: '2026-03-12'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: [python, playwright-sync-api, sqlite3]
files_to_modify: [browser.py, main.py, descriptions.py]
code_patterns: [playwright-sync-api, random-delay-anti-bot, webdriver-masking, human-scroll-simulation]
test_patterns: [no-existing-tests-for-scraping-modules, manual-testing-only]
---

# Tech-Spec: Scraping Improvements - Cookie Auto-dismiss & Timing Optimization

**Created:** 2026-03-12

## Overview

### Problem Statement

The scraping process is blocked when the cookie consent modal is not manually dismissed on the first page load. Additionally, excessive wait times throughout the scraping pipeline (slow_mo, inter-page pauses, post-navigation delays) unnecessarily extend the total scraping duration.

### Solution

1. Handle the cookie modal **before** waiting for page content — detect and dismiss it automatically on first page load, treating it as a modal overlay rather than a banner.
2. Moderate reduction of delays: lower `slow_mo`, reduce inter-page pauses and post-navigation waits, while preserving `human_scroll` and sufficiently "human" behavior to avoid DataDome detection.

### Scope

**In Scope:**
- Automatic cookie modal dismissal on first page load
- Reduce `slow_mo` from 120ms to 60ms (main.py) and from 80ms to 50ms (descriptions.py)
- Reduce inter-page pauses from 8-18s to 3-8s
- Reduce post-navigation `wait_for_timeout` by leveraging `wait_for_selector` where possible
- Apply same optimizations in descriptions.py

**Out of Scope:**
- Removing `human_scroll` behavior
- Aggressive delay reduction
- Headless mode
- Architectural changes to the scraper

## Context for Development

### Codebase Patterns

- Playwright sync API used throughout (no async)
- `accept_cookies()` in `browser.py:61-72` already handles cookie button clicks but is called after a 2.5-4.5s fixed wait — too late, modal blocks JS rendering
- Anti-bot measures: `webdriver` property masking, human-like user agent, locale/timezone spoofing, `slow_mo` on browser launch
- Random delays (via `random.randint` + `wait_for_timeout`) used at every stage to mimic human behavior
- `human_scroll()` simulates page scrolling with micro-pauses — to be preserved
- Two separate browser launch points: `main.py:56` (scraping) and `descriptions.py:55` (descriptions)

### Files to Reference

| File | Purpose | Key Lines |
| ---- | ------- | --------- |
| browser.py | Core scraping logic, cookie handling, human simulation | L61-72: accept_cookies, L99-127: scrape_page, L130-162: get_all_ads |
| main.py | Entry point, browser launch config for --scrape | L56-59: browser launch with slow_mo=120 |
| descriptions.py | Description fetching with its own browser instance | L55-57: browser launch with slow_mo=80, L9-37: fetch_description |
| config.py | Constants (SEARCH_URL, MAX_PAGES) | Not modified |

### Technical Decisions

- Cookie modal is a full modal overlay (not a banner), appears only on first page load
- Keep human_scroll intact — moderate optimization only
- Preserve anti-bot countermeasures while reducing unnecessary wait time
- Replace fixed `wait_for_timeout` post-navigation with `wait_for_selector` on actual content selectors where possible
- No existing tests for scraping modules — manual testing only
- The reduction is applied on two axes (slow_mo and pauses). In case of DataDome detection, increase inter-page pauses first (3-8s → 5-12s) before adjusting slow_mo
- The site is a Next.js app with JS hydration. `domcontentloaded` is sufficient because `wait_for_selector` waits for client-side rendering to complete. The 15s timeout covers hydration delay

## Implementation Plan

### Tasks

- [x] Task 1: Improve `accept_cookies()` to handle the modal proactively with `is_first_page` flag
  - File: `browser.py` — function `accept_cookies()` (L61-72)
  - Action: Rewrite `accept_cookies()` to accept a parameter `is_first_page: bool = False`. When `is_first_page=True`, attempt a `wait_for_selector` (timeout ~3s) on the cookie modal/button before clicking — this ensures the function waits for the modal to appear. When `is_first_page=False`, skip the `wait_for_selector` and only do an instant check (`btn.count()`) to avoid adding 3s of wasted timeout on every subsequent page. Add `button[aria-label*='accepter']` as an additional selector. Keep the existing text-based selectors (`"Tout accepter"`, `"Accepter et fermer"`, `button[id*='accept']`) as fallback.
  - After a successful click, add `print("  ✓ Modale cookies fermée")` for debugging visibility.
  - Notes: The function should be idempotent — safe to call even if no modal appears (timeout gracefully). Do NOT add speculative selectors like `#didomi-notice-agree-button` — verify actual selectors via browser inspector during implementation and add only confirmed ones.

- [x] Task 2: Restructure `scrape_page()` flow: cookies → scroll → wait_for_selector with debug screenshot
  - File: `browser.py` — function `scrape_page()` (L99-127)
  - Action: Restructure `scrape_page()` with the following exact order:
    1. `page.goto(url, wait_until="domcontentloaded", timeout=60_000)`
    2. `accept_cookies(page, is_first_page=...)` — pass `True` only when called for the first page
    3. `human_scroll(page)` — scroll BEFORE waiting for selectors, to trigger lazy-loading of ad cards
    4. `wait_for_selector` on the ad card selectors (same selectors already used in the existing code at L108-110: `[data-test-id='aditem_container'], article[data-qa-id], [data-testid='ad-card']`) with timeout 15s, wrapped in a `try/except PWTimeout` block that **preserves the debug screenshot logic** (`page.screenshot(path="debug_blocked.png")` + warning print) from the existing L113-116 block
  - Remove the fixed `wait_for_timeout(2500-4500)` at L102 (replaced by the flow above)
  - Remove the old `wait_for_selector` block at L107-116 (merged into step 4 above)
  - Add `is_first_page: bool = False` parameter to `scrape_page()` signature, passed through to `accept_cookies()`.
  - Update `get_all_ads()`: change the `scrape_page()` call at L136 to pass `is_first_page=(p == 1)` as argument.

- [x] Task 3: Reduce `slow_mo` in main.py
  - File: `main.py` — L58
  - Action: Change `slow_mo=120` to `slow_mo=60`

- [x] Task 4: Reduce inter-page pause in `get_all_ads()`
  - File: `browser.py` — function `get_all_ads()` (L157-160)
  - Action: Change `random.randint(8000, 18000)` to `random.randint(3000, 8000)`. Update the print message accordingly.

- [x] Task 5: Optimize `fetch_description()` timing with preserved anti-bot delay
  - File: `descriptions.py` — function `fetch_description()` (L9-37)
  - Action: Replace `wait_for_timeout(random.randint(2000, 4000))` at L13 with a `wait_for_selector` on the description container selectors (`[data-qa-id='adview_description_container'], [data-testid='description'], [class*='Description'], div[itemprop='description']`) with timeout 10s, wrapped in try/except to handle pages without description gracefully. **After** the `wait_for_selector` resolves, add a `wait_for_timeout(random.randint(800, 1500))` to preserve a human-like reading delay as anti-bot measure.
  - Add `is_first_page: bool = False` parameter to `fetch_description()` signature. Forward it to `accept_cookies(page, is_first_page=is_first_page)` at L14.
  - Update `fetch_all_descriptions()`: change the `fetch_description()` call at L78 to pass `is_first_page=(i == 1)` as argument.
  - Notes: The anti-bot delay is intentionally kept after selector resolution to maintain human-like behavior without the excessive fixed wait.

- [x] Task 6: Reduce `slow_mo` and inter-annonce pause in descriptions.py
  - File: `descriptions.py` — L57 and L89
  - Action: Change `slow_mo=80` to `slow_mo=50`. Change inter-annonce pause from `random.randint(4000, 9000)` to `random.randint(2000, 5000)`.

### Acceptance Criteria

- [ ] AC 1: Given the scraper is launched with `--scrape`, when the Leboncoin page loads and displays the cookie consent modal, then the modal is automatically dismissed without manual intervention and scraping proceeds normally.
- [ ] AC 2: Given the cookie modal has already been dismissed on page 1, when subsequent pages are loaded, then `accept_cookies()` performs an instant check only (no 3s wait) and does not cause errors or unnecessary delays.
- [ ] AC 3: Given the scraper is running with `--scrape`, when navigating between listing pages, then the inter-page pause is between 3-8 seconds (reduced from 8-18s).
- [ ] AC 4: Given the scraper is running with `--scrape`, when a listing page loads, then the scraper proceeds as soon as ad card selectors are found (via `wait_for_selector`) rather than waiting a fixed 2.5-4.5s timeout. If ads are not found within 15s, a debug screenshot is saved to `debug_blocked.png`.
- [ ] AC 5: Given the scraper is launched with `--get-description`, when fetching individual listing descriptions, then the inter-annonce pause is between 2-5 seconds (reduced from 4-9s), page readiness is detected via selector rather than fixed timeout, and a short anti-bot delay (800-1500ms) is applied after selector resolution.
- [ ] AC 6: Given all timing optimizations are applied, when running a full scrape cycle, then ads are retrieved on at least 90% of pages (no consecutive empty pages caused by HTTP 403, captcha redirect, or empty ad list).

## Additional Context

### Dependencies

- playwright (existing dependency, no new dependencies required)

### Testing Strategy

- **Manual test 1:** Run `python main.py --scrape` — verify the cookie modal is auto-dismissed on first page load without manual click
- **Manual test 2:** Observe scraping logs — verify inter-page pauses are visibly shorter (3-8s range)
- **Manual test 3:** Verify ads are still retrieved successfully (no DataDome blocks, no empty results)
- **Manual test 4:** Run `python main.py --get-description` — verify descriptions are fetched with reduced pauses and cookie modal is handled on first URL only
- **Manual test 5:** If DataDome blocks occur, increase delays back toward original values incrementally

### Rollback Strategy

If DataDome detection rate increases after deployment:
1. **First:** Increase inter-page pauses back to 5-12s (`random.randint(5000, 12000)`)
2. **Second:** If still blocked, restore original inter-page pauses (8-18s)
3. **Third:** If still blocked, restore `slow_mo` to original values (120 for main.py, 80 for descriptions.py)
4. A "block" is defined as: HTTP 403 response, captcha page redirect, or 3+ consecutive pages returning 0 ads

### Notes

- Monitor for DataDome blocks after timing reduction — may need to adjust delays upward if detection rate increases
- The cookie modal selectors may change over time as Leboncoin updates their consent management platform — if `accept_cookies()` stops working, verify actual selectors via browser inspector and update accordingly
- Future consideration: could add a `--fast` flag to toggle between moderate and aggressive timing profiles (out of scope)

## Review Notes
- Adversarial review completed
- Findings: 7 total, 6 fixed, 1 skipped (F7: pre-existing SQLite pattern, out of scope)
- Resolution approach: auto-fix
- Key adjustments post-review: inter-page pause raised to 5-12s (from spec's 3-8s) per rollback strategy, added post-navigation delay (800-1500ms), restored 20s selector timeout, reduced description timeout to 5s, added error logging in accept_cookies, fixed race condition on non-first-page cookie check
