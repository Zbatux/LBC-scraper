---
title: 'Clickable Title Link — Remove Lien Column'
slug: 'clickable-title-link'
created: '2026-03-11'
status: 'Implementation Complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['HTML', 'CSS', 'Vanilla JavaScript']
files_to_modify: ['templates/index.html']
code_patterns: ['Inline HTML row template via template literals', 'escHtml() for XSS-safe output', 'CSS classes per cell type (titre-cell, lien-cell)']
test_patterns: ['No automated tests for HTML template']
---

# Tech-Spec: Clickable Title Link — Remove Lien Column

**Created:** 2026-03-11

## Overview

### Problem Statement

The listings table has a dedicated "Lien" column that shows an "Ouvrir ↗" link for each listing. This wastes horizontal space and creates a redundant UX pattern — the user has to look away from the title to find the link.

### Solution

Remove the "Lien" column entirely and make the "Titre" cell a clickable hyperlink pointing to `a.lien`. If no link is available, the title renders as plain text (unchanged behavior).

### Scope

**In Scope:**
- Remove `<th>Lien</th>` from `thead`
- Transform `titre-cell` `<td>` to render title as `<a href>` when `a.lien` exists
- Remove `lien-cell` `<td>` from the row template in `render()`
- Remove `td.lien-cell` CSS rules (2 rules)
- Add link styling to `.titre-cell a` so the link is visually clear but not garish

**Out of Scope:**
- The "🔗 Ouvrir liens" bulk toolbar button — it reads `a.lien` directly from data, unaffected
- Backend/API changes — `lien` field still returned by `/api/annonces`
- History modal — unrelated

## Context for Development

### Codebase Patterns

- **Single-file frontend**: All HTML, CSS and JS live in `templates/index.html`. No build system, no framework.
- **Row rendering**: Rows are built via `tr.innerHTML = \`...\`` template literals inside `render()` (around line 501–522).
- **XSS safety**: All user-supplied values go through `escHtml()` before insertion into innerHTML. The `href` attribute on links also uses `escHtml(a.lien)`.
- **Cell CSS classes**: Each logical cell type has a class (e.g. `titre-cell`, `lien-cell`, `note-cell`). The `<td class="titre-cell">` already has `overflow: hidden; white-space: nowrap; text-overflow: ellipsis` set. However, `text-overflow` does not cascade to child elements — the `<a>` tag must itself be made `display: block` with the same overflow properties to preserve truncation behavior.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `templates/index.html` | Only file to modify — contains all HTML, CSS, and JavaScript |

### Technical Decisions

- Title link opens in `target="_blank" rel="noopener"` (same pattern as current "Ouvrir ↗" link).
- When `a.lien` is null/empty, the title renders as plain escaped text — no `<a>` tag — same as today.
- Link color on titre-cell: use `#2563eb` (same blue as current lien-cell) with `text-decoration: none` on default, underline on hover.
- Font-size: deliberately NOT set to `11px` (the old `lien-cell` value). The `<a>` inherits the body font-size (13px) which is correct for the titre column. Setting `11px` would shrink the title text.
- The `<a>` element must be `display: block` to allow `text-overflow: ellipsis` to work (see Codebase Patterns above).
- The `title` tooltip attribute on the `<td>` (shows full title on hover) is preserved.
- The truthy check `a.lien ? ... : ...` treats `null`, `undefined`, and `""` as "no link" — this is correct. A whitespace-only string `" "` would be treated as a valid link; this edge case is acceptable given the data comes from the scraper which never produces such values.

## Implementation Plan

### Tasks

**Task 1 — Remove CSS for lien-cell**

File: `templates/index.html`
Location: Lines 135–138

Remove these two CSS rules:
```css
td.lien-cell a {
  color: #2563eb; text-decoration: none; font-size: 11px;
}
td.lien-cell a:hover { text-decoration: underline; }
```

Add link styling inside `titre-cell`:
```css
td.titre-cell a {
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: #2563eb;
  text-decoration: none;
}
td.titre-cell a:hover { text-decoration: underline; }
```

**Reason for `display: block` + overflow rules:** `text-overflow: ellipsis` on the parent `<td>` does not cascade to `<a>` elements. The `<a>` must explicitly carry these properties or the title will overflow its cell.

---

**Task 2 — Remove `<th>Lien</th>` from thead**

File: `templates/index.html`
Location: Line 348 (inside `<thead><tr>`)

Remove:
```html
<th>Lien</th>
```

---

**Task 3 — Update titre-cell in render() template literal**

File: `templates/index.html`
Location: Line 506 (inside the `tr.innerHTML = \`...\`` block in `render()`)

Current:
```js
<td class="titre-cell" title="${escHtml(a.titre || "")}">${escHtml(a.titre || "—")}</td>
```

Replace with:
```js
<td class="titre-cell" title="${escHtml(a.titre || "")}">
  ${a.lien
    ? `<a href="${escHtml(a.lien)}" target="_blank" rel="noopener">${escHtml(a.titre || "—")}</a>`
    : escHtml(a.titre || "—")}
</td>
```

---

**Task 4 — Remove lien-cell `<td>` from render() template literal**

File: `templates/index.html`
Location: Line 517 (inside the same `tr.innerHTML` block)

Remove:
```js
<td class="lien-cell">${a.lien ? `<a href="${escHtml(a.lien)}" target="_blank" rel="noopener">Ouvrir ↗</a>` : "—"}</td>
```

### Acceptance Criteria

**AC1 — Title is clickable when lien exists**
- Given an annonce with a non-null `lien` field
- When the table renders
- Then the titre cell contains an `<a>` tag with `href` equal to the annonce URL, opening in a new tab

**AC2 — Title is plain text when lien is null**
- Given an annonce with a null or empty `lien` field
- When the table renders
- Then the titre cell contains plain escaped text (no `<a>` tag)

**AC3 — Lien column is gone**
- Given any state of the table
- When the page loads
- Then no `<th>` with text "Lien" exists in the thead, and no `<td class="lien-cell">` exists in any row

**AC4 — Bulk "Ouvrir liens" still works**
- Given rows selected in the table
- When user clicks "🔗 Ouvrir liens" in the toolbar
- Then each selected annonce URL opens in a new tab (behavior unchanged)

**AC5 — Title tooltip preserved**
- Given an annonce with a long titre
- When the user hovers over the titre cell
- Then the full title text appears as a browser tooltip

## Additional Context

### Dependencies

None — pure HTML/CSS/JS change in a single file.

### Testing Strategy

- Manual visual test: load the app, verify titles are clickable links.
- Manual test: verify no "Lien" column header exists.
- Manual test: verify an annonce with no `lien` shows plain text title.
- Manual test: select rows and confirm "🔗 Ouvrir liens" still opens tabs.

### Notes

- No backend changes required.
- No other templates exist in the project.
- The column count in `<thead>` drops by 1 (from 17 to 16 columns). This has no other side-effects since there is no colspan/column-index logic in the JS.
