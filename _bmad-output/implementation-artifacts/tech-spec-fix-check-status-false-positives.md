---
title: 'Fix Check-Status False Positives'
slug: 'fix-check-status-false-positives'
created: '2026-03-31'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.13', 'Playwright', 'SQLite']
files_to_modify: ['descriptions.py', 'debug_check.py']
code_patterns: ['Playwright text= selectors vs CSS selectors', 'three-state return pattern (deleted/online/inconclusive)', 'locator().count() for presence checks', 'wait_for_selector for CSS only']
test_patterns: ['manual testing with debug_check.py']
---

# Tech-Spec: Fix Check-Status False Positives

**Created:** 2026-03-31

## Overview

### Problem Statement

`check_listing_status()` mixes Playwright `text=` selectors with CSS selectors in a single `wait_for_selector` combined call, causing systematic timeouts. As a result, online listings are falsely classified as `deleted` (172 false positives in the last run). The function falls through to `return "deleted"` when no selector matches within 8 seconds, even though valid content markers appear shortly after.

### Solution

Separate the detection logic into two distinct steps: first check for explicit deletion markers (text "Cette annonce est desactivee", button "Retour a la page d'accueil"), then check for valid content markers. Only mark `deleted` if a deletion marker is explicitly found. If neither deletion nor valid content is found, return `inconclusive`.

### Scope

**In Scope:**
- Fix `check_listing_status()` in `descriptions.py`
- Add new deletion markers ("Retour a la page d'accueil")
- Separate `text=` selectors from CSS selectors to fix the `wait_for_selector` bug
- Improve `check_all_statuses()` logging: collect inconclusive listings and display them grouped at the end of execution for readability

**Out of Scope:**
- `fetch_description` and rest of pipeline
- Safety thresholds / circuit breakers
- UI / database modifications

## Context for Development

### Codebase Patterns

- `check_listing_status()` (descriptions.py:79-108) uses a three-state return: `deleted`, `online`, `inconclusive`
- Bug: line 92 concatenates `DISABLED_SELECTORS` (Playwright `text=` syntax) with `VALID_LISTING_SELECTORS` (CSS syntax) into one `wait_for_selector` call — Playwright's `wait_for_selector` does not handle `text=` pseudo-selectors in a CSS comma list, causing silent timeout
- Bug: line 104-105 falls through to `return "deleted"` when no selector matches — should be `"inconclusive"`
- Working pattern in `fetch_description()` (line 22): uses `page.locator("text=...")` separately from CSS `wait_for_selector` — this is the correct approach
- `DISABLED_SELECTORS` constant (line 65-69): three text-based checks using Playwright `text=` syntax
- `VALID_LISTING_SELECTORS` constant (line 71-76): four CSS selectors for valid listing content
- Anti-bot delay pattern: `page.wait_for_timeout(random.randint(800, 1500))` after page interactions

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `descriptions.py:65-108` | `DISABLED_SELECTORS`, `VALID_LISTING_SELECTORS`, `check_listing_status()` — the code to fix |
| `descriptions.py:11-62` | `fetch_description()` — reference for working deletion detection pattern |
| `browser.py:61-97` | `accept_cookies()` — called by `check_listing_status`, no changes needed |

### Technical Decisions

- **Use `page.locator().count()` for deletion markers** (not `wait_for_selector`) — Playwright `text=` selectors work with `locator()` but not reliably in `wait_for_selector` comma lists
- **Use `wait_for_selector` only for CSS selectors** — wait for valid listing content with CSS-only selectors
- **Deletion = explicit markers only** — only return `"deleted"` when a known deletion text is found on the page. Absence of content is `"inconclusive"`, not `"deleted"`
- **"Retour a la page d'accueil" is a secondary marker only** — this text can appear on generic error/maintenance pages, not just disabled listings. It only triggers `"deleted"` when no valid listing content is found, preventing false positives from transient error pages

## Implementation Plan

### Tasks

- [x] Task 1: Replace `DISABLED_SELECTORS` constant with a Python list of individual Playwright `text=` selectors
  - File: `descriptions.py`
  - Action: Replace the `DISABLED_SELECTORS` string constant (lines 65-69) with a list of individual selectors for use with `page.locator().count()`:
    ```python
    # Primary markers — each one alone is sufficient to confirm deletion
    DELETED_MARKERS = [
        "text=Cette annonce est désactivée",
        "text=Cette annonce n'est plus disponible",
        "text=Annonce introuvable",
    ]

    # Secondary marker — only confirms deletion when NO valid listing content is present
    # (this text can appear on error/maintenance pages too, so it's not sufficient alone)
    DELETED_MARKER_SECONDARY = "text=Retour à la page d'accueil"
    ```
  - Notes: Changed from a comma-joined string to a Python list so each marker can be checked individually via `page.locator(marker).count()`. "Retour a la page d'accueil" is separated as a secondary marker because it can appear on generic error pages — it only confirms deletion when combined with the absence of valid listing content.

- [x] Task 2: Rewrite `check_listing_status()` to separate deletion checks from content checks
  - File: `descriptions.py`
  - Action: Replace the entire function body (lines 79-108) with the following logic:
    1. `page.goto(url, wait_until="domcontentloaded", timeout=60_000)`
    2. `accept_cookies(page, is_first_page=is_first_page)`
    3. `page.wait_for_timeout(random.randint(800, 1500))` — anti-bot delay, let page render
    4. **Check primary deletion markers FIRST** (fast path — avoids 10s timeout on deleted listings): iterate over `DELETED_MARKERS`, if any `page.locator(marker).count() > 0` → return `"deleted"` immediately
    5. **Wait for valid content** using CSS-only selectors: `page.wait_for_selector(VALID_LISTING_SELECTORS, timeout=15_000)` — wrapped in try/except PWTimeout (pass on timeout). 15s accounts for `accept_cookies()` cumulative delay (up to 12s on first page)
    6. **Check valid content**: if `page.locator(VALID_LISTING_SELECTORS).count() > 0` → return `"online"`
    7. **Check secondary deletion marker**: if `page.locator(DELETED_MARKER_SECONDARY).count() > 0` → return `"deleted"` (only reached when no valid content found, so safe from false positives)
    8. **Neither found** → return `"inconclusive"`
    9. Outer try/except for any exception → log and return `"inconclusive"`
  - Notes: Key changes vs current code: (a) deletion markers checked FIRST via `locator().count()`, following the same pattern as `fetch_description()` — this avoids wasting the full timeout on deleted listings; (b) `wait_for_selector` uses only CSS selectors, fixing the mixed-syntax bug; (c) timeout increased from 8s to 15s — `accept_cookies()` can consume up to 12s on the first page (8s wait + click delays + second modal), so 10s would be insufficient for pages where cookies are handled; (d) fallback is `"inconclusive"` instead of `"deleted"`, eliminating false positives

- [x] Task 3: Update `debug_check.py` to use renamed `DELETED_MARKERS` constant
  - File: `debug_check.py`
  - Action: Replace `from descriptions import DISABLED_SELECTORS, VALID_LISTING_SELECTORS` with `from descriptions import DELETED_MARKERS, VALID_LISTING_SELECTORS`. Update the disabled selectors test loop to iterate over `DELETED_MARKERS` list instead of splitting the old comma-joined string.
  - Notes: Without this change, `debug_check.py` will raise `ImportError` immediately after Task 1 renames the constant.

- [x] Task 4: Defer inconclusive logs to end of execution in `check_all_statuses()`
  - File: `descriptions.py`
  - Action: In `check_all_statuses()` (lines 111-160), collect inconclusive listings in a list instead of logging them inline. Print them grouped at the end, after the summary line.
  - Details:
    1. Add `inconclusive_list = []` before the loop
    2. In the `inconclusive` branch, replace the inline `print(...)` with `inconclusive_list.append(lien)`
    3. After the summary line, if `inconclusive_list` is not empty, print a grouped block:
       ```
       ⚠ Annonces non vérifiables (anti-bot ou erreur) :
         - https://www.leboncoin.fr/ad/...
         - https://www.leboncoin.fr/ad/...
       ```
  - Notes: The inline `[i/total]` progress line still prints for every listing. Only the warning detail is deferred. `deleted` and `online` results still log inline as before.

### Acceptance Criteria

- [ ] AC 1: Given a listing that is online on Leboncoin, when running `--check-status`, then the listing is detected as `"online"` (not falsely marked deleted).
- [ ] AC 2: Given a listing that displays "Cette annonce est desactivee" on Leboncoin, when running `--check-status`, then the listing is detected as `"deleted"`.
- [ ] AC 3: Given a listing page that displays "Retour a la page d'accueil" (disabled listing page), when running `--check-status`, then the listing is detected as `"deleted"`.
- [ ] AC 4: Given a page that loads but shows neither deletion markers nor valid content (e.g., anti-bot block), when running `--check-status`, then the listing is marked `"inconclusive"` and skipped.
- [ ] AC 5: Given a network error or page load timeout, when running `--check-status`, then the listing is marked `"inconclusive"` and processing continues with the next listing.
- [ ] AC 6: Given the URL https://www.leboncoin.fr/ad/ventes_immobilieres/3171369139 (known online listing that was a false positive), when running `debug_check.py` or `--check-status`, then it is correctly detected as `"online"`.
- [ ] AC 7: Given several inconclusive listings during a `--check-status` run, when the run completes, then their URLs are displayed grouped at the end of execution (not inline during processing).

## Additional Context

### Dependencies

- Playwright (already installed)
- No new dependencies required

### Testing Strategy

- Run `debug_check.py` (adapted to use new logic) on the known false-positive URL — must return `"online"`
- Run `--check-status` on full database and verify:
  - No mass false positives (deleted count should be reasonable, not 170+)
  - Known deleted listings are still correctly detected
  - Inconclusive count visible in summary output
- Manually visit a few listings marked `"deleted"` to confirm they are genuinely disabled

### Notes

- The `DISABLED_SELECTORS` constant name changes to `DELETED_MARKERS` to better reflect its purpose and new type (list vs string)
- `VALID_LISTING_SELECTORS` remains unchanged — it is pure CSS and works correctly with both `wait_for_selector` and `locator()`
- `check_all_statuses()` is modified only for logging: inconclusive results are collected and displayed at the end instead of inline
- "Retour a la page d'accueil" is a secondary-only marker — it confirms deletion only when no valid listing content is present, because this text can also appear on generic error/maintenance pages
