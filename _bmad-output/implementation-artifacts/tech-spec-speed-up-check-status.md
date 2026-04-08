---
title: 'Speed Up Check-Status Inter-Page Delays'
slug: 'speed-up-check-status'
created: '2026-03-31'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.13', 'Playwright', 'SQLite']
files_to_modify: ['descriptions.py']
code_patterns: ['random.randint for delays', 'is_first_page flag for cookie handling']
test_patterns: ['manual testing']
---

# Tech-Spec: Speed Up Check-Status Inter-Page Delays

**Created:** 2026-03-31

## Overview

### Problem Statement

`--check-status` takes too long to process all listings. Each page currently incurs ~5-7s of delays: 800-1500ms anti-bot delay after page load (line 97) + 2000-5000ms inter-page delay (line 174). For ~450 listings, this adds up to ~50 minutes of waiting.

### Solution

Reduce delays to ~2s total per page. Keep longer delays only on the first page where cookie acceptance requires time. On subsequent pages, the browser session is already established and cookies are accepted, so shorter delays are safe.

### Scope

**In Scope:**
- Reduce anti-bot delay in `check_listing_status()` for non-first pages
- Reduce inter-page delay in `check_all_statuses()` for non-first pages

**Out of Scope:**
- Everything else (detection logic, logging, database, UI)

## Context for Development

### Codebase Patterns

- `check_listing_status(page, url, is_first_page)` already receives an `is_first_page` flag — it can be used to branch delay durations
- Anti-bot delay (descriptions.py:97): `page.wait_for_timeout(random.randint(800, 1500))` — same for all pages
- Inter-page delay (descriptions.py:174): `random.randint(2000, 5000)` — same for all pages
- `accept_cookies()` only does meaningful work on `is_first_page=True` — subsequent pages skip the cookie modal wait

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `descriptions.py:84-127` | `check_listing_status()` — anti-bot delay to reduce |
| `descriptions.py:130-185` | `check_all_statuses()` — inter-page delay to reduce |

### Technical Decisions

- **First page keeps current delays** — cookie acceptance needs time (up to 12s), so we keep `random.randint(800, 1500)` anti-bot delay and `random.randint(2000, 5000)` inter-page delay
- **Subsequent pages use ~2s total** — anti-bot delay reduced to `random.randint(300, 600)` ms, inter-page delay reduced to `random.randint(1000, 1500)` ms
- **`is_first_page` flag reused** — already passed through to `check_listing_status`, no new parameter needed

## Implementation Plan

### Tasks

- [x] Task 1: Reduce anti-bot delay in `check_listing_status()` for non-first pages
  - File: `descriptions.py`
  - Action: Replace line 97:
    ```python
    page.wait_for_timeout(random.randint(800, 1500))
    ```
    With:
    ```python
    page.wait_for_timeout(random.randint(800, 1500) if is_first_page else random.randint(300, 600))
    ```

- [x] Task 2: Reduce inter-page delay in `check_all_statuses()` for non-first pages
  - File: `descriptions.py`
  - Action: Replace line 174:
    ```python
    delay = random.randint(2000, 5000)
    ```
    With:
    ```python
    delay = random.randint(2000, 5000) if i == 1 else random.randint(1000, 1500)
    ```
  - Notes: `i` starts at 1 (from `enumerate(rows, 1)`), so `i == 1` matches the first page only.

### Acceptance Criteria

- [ ] AC 1: Given the first listing in a `--check-status` run, when processed, then the anti-bot delay is 800-1500ms and the inter-page delay is 2000-5000ms (unchanged).
- [ ] AC 2: Given any subsequent listing (not the first), when processed, then the anti-bot delay is 300-600ms and the inter-page delay is 1000-1500ms.
- [ ] AC 3: Given a full `--check-status` run on ~450 listings, when completed, then total runtime is significantly reduced compared to before (target: ~20min vs ~50min).

## Additional Context

### Dependencies

- None

### Testing Strategy

- Run `--check-status` on a few listings and observe timing in console output
- Compare total runtime before/after on a full run

### Notes

- These delays are a trade-off between speed and anti-bot detection risk. If LeBonCoin starts blocking more aggressively after this change, the delays can be increased again.
- The `wait_for_selector` timeout (15s) is NOT reduced — that's a page load timeout, not an artificial delay.

## Review Notes
- Adversarial review completed
- Findings: 5 total, 3 fixed, 2 skipped
- Resolution approach: auto-fix (real findings only)
- F-01 fixed: in-page delay widened from 300-600ms to 500-1000ms for consistency
- F-02 fixed: inter-page delay widened from 1000-1500ms to 1000-3000ms for variance
- F-03 fixed: added guard to skip delay after last iteration
