---
title: 'Comment Button Color States'
slug: 'comment-button-color-states'
created: '2026-04-13'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['HTML', 'CSS', 'Vanilla JS']
files_to_modify: ['templates/index.html']
code_patterns: ['CSS class toggle via JS render']
test_patterns: []
---

# Tech-Spec: Comment Button Color States

**Created:** 2026-04-13

## Overview

### Problem Statement

The comment button in the listings table has the same violet shade (`#8b5cf6`) whether or not a comment exists. The `.has-comment` variant is only slightly darker (`#7c3aed`) with a subtle ring — not visually distinct enough to communicate "comment present" at a glance.

### Solution

Invert the visual weight: the default (no comment) button becomes light violet (`#c4b5fd` with dark text), while the `.has-comment` state uses the current solid violet (`#8b5cf6`) — making the presence of a comment immediately obvious.

### Scope

**In Scope:**
- CSS rules for `.comment-btn` (default state — no comment)
- CSS rules for `.comment-btn.has-comment` (has comment state)
- CSS rules for hover variants of both states

**Out of Scope:**
- JS logic for applying `has-comment` class (already correct at line 652)
- Backend / API changes
- Any other button styles

## Context for Development

### Codebase Patterns

- All styles are inline in `<style>` block of `templates/index.html` (lines 303–313).
- The `has-comment` class is toggled via template literal at render time (line 652): `class="comment-btn${a.commentaire ? ' has-comment' : ''}"` — no JS change needed.
- No CSS framework (plain CSS). Color palette uses Tailwind-compatible violet values.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `templates/index.html` | Contains all CSS (lines 303–313) and the render template (line 652) |

### Technical Decisions

- **No comment state color:** `#c4b5fd` (violet-300) background with `#5b21b6` (violet-900) text for contrast and readability.
- **Has comment state color:** `#8b5cf6` (violet-500) — current default color, kept as-is (white text).
- **Hover for no-comment:** `#a78bfa` (violet-400) — one step darker than resting.
- **Hover for has-comment:** `#7c3aed` (violet-600) — current hover, kept as-is.
- **Box-shadow ring on `.has-comment`:** keep existing `0 0 0 2px #c4b5fd` ring — reinforces "active" state.

## Implementation Plan

### Tasks

- [x] Task 1: Update `.comment-btn` default state (no comment)
  - File: `templates/index.html` line 304
  - Action: Change `background: #8b5cf6` → `background: #c4b5fd` and change `color: #fff` → `color: #5b21b6`
  - Notes: Light violet background requires dark text for WCAG contrast compliance

- [x] Task 2: Update `.comment-btn:hover` default state (no comment hover)
  - File: `templates/index.html` line 308
  - Action: Change `background: #7c3aed` → `background: #a78bfa`
  - Notes: One step darker than resting `#c4b5fd`, stays in light range

- [x] Task 3: Update `.comment-btn.has-comment` state
  - File: `templates/index.html` lines 309–312
  - Action: Change `background: #7c3aed` → `background: #8b5cf6`; add `color: #fff` explicitly
  - Notes: Keep existing `box-shadow: 0 0 0 2px #c4b5fd` ring — reinforces active state

- [x] Task 4: Update `.comment-btn.has-comment:hover` state
  - File: `templates/index.html` line 313
  - Action: Change `background: #6d28d9` → `background: #7c3aed`
  - Notes: One step darker than resting `#8b5cf6`; aligns hover depth with has-comment resting color

### Acceptance Criteria

- [ ] AC 1: Given a listing with no comment, when the page renders, then the comment button has a light violet (`#c4b5fd`) background with dark (`#5b21b6`) text.
- [ ] AC 2: Given a listing with an existing comment (`a.commentaire` is truthy), when the page renders, then the comment button has solid violet (`#8b5cf6`) background with white text and a `#c4b5fd` ring.
- [ ] AC 3: Given a no-comment button, when hovered, then the background shifts to `#a78bfa`.
- [ ] AC 4: Given a has-comment button, when hovered, then the background shifts to `#7c3aed`.
- [ ] AC 5: Given a comment is saved via the modal, when `render()` is called, then the button for that listing switches from light violet to solid violet — no page reload needed (existing JS handles `has-comment` class toggle).

## Additional Context

### Dependencies

None. Pure CSS change, no runtime dependencies.

### Testing Strategy

Visual verification only:
- Load app, find listing without comment → button should be light violet
- Open comment modal, save a comment → button should switch to solid violet on re-render
- Verify both hover states

### Notes

The JS class toggle at line 652 already correctly drives the `has-comment` class based on `a.commentaire`. No JS changes required.

## Review Notes

- Adversarial review completed
- Findings: 8 total, 5 fixed, 3 skipped (undecided/noise)
- Resolution approach: auto-fix

**Fixes applied:**
- F1: Added `.comment-btn:focus-visible` (dark outline) and `.has-comment:focus-visible` (deeper violet outline) for keyboard accessibility
- F2: Contrast ratio `#5b21b6` on `#c4b5fd` verified ≈ 4.87:1 — passes WCAG AA (threshold 4.5:1)
- F3: Ring changed from `#c4b5fd` → `#7c3aed` so it is visible against default button background
- F4: Added `transition: background 0.15s, color 0.15s` to `.comment-btn` for smooth state change on comment save
- F6: `.has-comment` properties split to separate lines for formatting consistency

**Skipped:** F5 (dark mode — undecided), F7 (hover delta — undecided), F8 (disabled state — noise)
