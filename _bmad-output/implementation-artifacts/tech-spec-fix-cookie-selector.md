---
title: 'Fix cookie modal selector for updated Leboncoin consent text'
slug: 'fix-cookie-selector'
created: '2026-03-13'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack: [python, playwright-sync-api]
files_to_modify: [browser.py]
code_patterns: [playwright-sync-api, css-selector-has-text]
test_patterns: [no-existing-tests-for-scraping-modules, manual-testing-only]
---

# Tech-Spec: Fix cookie modal selector for updated Leboncoin consent text

**Created:** 2026-03-13

## Overview

### Problem Statement

The `accept_cookies()` function in `browser.py` uses text-based selectors (`"Tout accepter"`, `"Accepter et fermer"`) that no longer match Leboncoin's updated cookie consent modal, which now displays **"Accepter & Fermer →"**. This causes the cookie modal to remain as an overlay, blocking DOM interaction during `--get-description` (description text extraction, "Voir plus" clicks). The `--scrape` flow is unaffected because it extracts data from the `__NEXT_DATA__` JSON script tag, which doesn't require DOM interaction through the modal.

### Solution

Add `button:has-text('Accepter & Fermer')` to the selector list in `accept_cookies()` so the function matches the updated button text.

### Scope

**In Scope:**
- Update the cookie button selector in `accept_cookies()` to match "Accepter & Fermer"

**Out of Scope:**
- Refactoring `accept_cookies()` logic or timing
- Changing the second modal ("cookies solidaires") handling
- Any timing/delay adjustments

## Context for Development

### Codebase Patterns

- Playwright sync API used throughout
- `accept_cookies()` in `browser.py:61-96` handles cookie dismissal with `has-text()` CSS pseudo-selectors
- The function is shared between `--scrape` (via `scrape_page`) and `--get-description` (via `fetch_description`)
- Selectors use comma-separated CSS with Playwright's `:has-text()` extension

### Files to Reference

| File | Purpose | Key Lines |
| ---- | ------- | --------- |
| browser.py | `accept_cookies()` — cookie modal dismissal logic | L61-96: selector definition at L63-67, click logic at L78-82 |
| descriptions.py | `fetch_description()` — calls `accept_cookies()`, blocked by modal | L19: `accept_cookies(page, is_first_page=is_first_page)` |

### Technical Decisions

- Use `has-text('Accepter & Fermer')` (without the `→` arrow) — Playwright's `has-text` does substring matching, so this covers the button even if the arrow character changes
- Keep existing selectors as fallback — Leboncoin may serve different modal variants (A/B testing, locale)
- Add the new selector as the **first** entry in the list, since it matches the currently observed modal text

## Implementation Plan

### Tasks

- [x] Task 1: Add "Accepter & Fermer" selector to `accept_cookies()`
  - File: `browser.py` — L63-67
  - Action: Add `"button:has-text('Accepter & Fermer'), "` as the first entry in the `selector` string at L63. The resulting selector becomes:
    ```python
    selector = (
        "button:has-text('Accepter & Fermer'), "
        "button:has-text('Tout accepter'), "
        "button:has-text('Accepter et fermer'), "
        "button[id*='accept'], "
        "button[aria-label*='accepter']"
    )
    ```
  - Notes: No other code changes needed — the rest of `accept_cookies()` (wait logic, click, second modal handling) works unchanged with the updated selector.

### Acceptance Criteria

- [x] AC 1: Given the scraper is launched with `--get-description`, when Leboncoin displays the cookie consent modal with button text "Accepter & Fermer →", then the modal is automatically dismissed and description scraping proceeds normally.
- [x] AC 2: Given the scraper is launched with `--scrape`, when the cookie consent modal appears with the new button text, then the modal is also dismissed (no regression).
- [x] AC 3: Given Leboncoin serves an older modal variant with "Tout accepter" or "Accepter et fermer", then the existing fallback selectors still match and dismiss the modal.
- [x] AC 4: Given no cookie modal appears (e.g., cookies already accepted), then `accept_cookies()` completes without error (idempotent behavior preserved).

## Additional Context

### Dependencies

- playwright (existing dependency, no new dependencies required)

### Testing Strategy

- **Manual test 1:** Run `python main.py --get-description` — verify the cookie modal is auto-dismissed on the first description page and descriptions are fetched successfully.
- **Manual test 2:** Run `python main.py --scrape` — verify no regression, cookie modal still dismissed on listing pages.

### Notes

- Leboncoin may continue to change their consent modal text over time. If `accept_cookies()` stops working again, inspect the modal button text in the browser and update the selector list accordingly.
- The `button[id*='accept']` and `button[aria-label*='accepter']` attribute selectors provide additional resilience against text changes, but they depend on Leboncoin's HTML attributes remaining stable.
