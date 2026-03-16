---
title: 'Commentaires sur les annonces'
slug: 'annonce-comments'
created: '2026-03-15'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3', 'Flask', 'SQLite3', 'Vanilla JS (ES6+)', 'CSS (no framework)']
files_to_modify: ['database.py', 'web.py', 'templates/index.html']
code_patterns: ['ALTER TABLE migration with try/except OperationalError', 'EDITABLE_FIELDS whitelist for column injection prevention', 'PATCH /api/annonces/<id> for single-field updates', 'Modal overlay pattern (overlay > dialog > header + body)', 'Conditional action buttons rendered inline in render()']
test_patterns: ['No automated tests in project']
---

# Tech-Spec: Commentaires sur les annonces

**Created:** 2026-03-15

## Overview

### Problem Statement

There is currently no way to add free-text notes or remarks on a listing. The existing `note` field is limited to a 1-10 integer score, which does not allow the user to capture qualitative observations or context about a listing.

### Solution

Add a single `commentaire` TEXT column to the `annonces` table, editable via a new button in the Actions column that opens a modal with a textarea. The comment is tied to the annonce itself (not to history snapshots).

### Scope

**In Scope:**

- New `commentaire` TEXT column in the `annonces` table
- New comment button in the Actions column of the main table
- Modal with textarea to read/edit the comment
- PATCH endpoint to save the comment

**Out of Scope:**

- Multiple/timestamped comments (thread-style)
- Bulk editing of comments
- Filtering by comment content
- Link with `annonces_history` table

## Context for Development

### Codebase Patterns

- **DB Migration**: `ALTER TABLE annonces ADD COLUMN <col> <type>` wrapped in try/except `sqlite3.OperationalError` (pass if column already exists). Applied in 3 locations: `save_to_database()`, `save_or_merge()` in database.py, and `ensure_columns()` in web.py.
- **Editable Fields Whitelist**: `EDITABLE_FIELDS` set in web.py gates all PATCH operations. Field names are interpolated into SQL only after whitelist validation.
- **PATCH Single Endpoint**: `update_annonce()` in web.py validates each field by type: `note` must be int 1-10 or null, boolean fields must be 0/1/null. **CRITICAL**: The boolean validation loop uses `EDITABLE_FIELDS - {"note"}` — any new non-boolean field MUST be excluded from this set to avoid false 400 errors.
- **Bulk Update Endpoint**: `bulk_update()` in web.py validates that `field` is in `EDITABLE_FIELDS` and `value` is 0 or 1. **CRITICAL**: Non-boolean fields must be excluded from `bulk_update()` to prevent data corruption.
- **API Response**: `get_annonces()` in web.py uses an explicit SELECT column list — `commentaire` must be added here.
- **Modal Pattern**: History modal and Compare modal follow the same structure: `.modal-overlay > .modal-dialog > .modal-header + .modal-body`. Close handlers via button click, overlay click, and Escape key. Existing modals cross-close each other (e.g., `openHistoryModal` calls `closeCompareModal()`).
- **Action Buttons**: Rendered inline in `render()` function with conditional display based on data availability. Each button has a CSS class and event binding in `bindRowEvents()`.

### Files to Reference

| File | Anchor | Purpose |
| ---- | ------ | ------- |
| `database.py` | `def save_to_database(` | Schema init + migrations list |
| `database.py` | `def save_or_merge(` | Schema init + migrations list |
| `web.py` | `EDITABLE_FIELDS =` | Whitelist of editable columns |
| `web.py` | `def ensure_columns():` | Web-side migration at Flask startup |
| `web.py` | `def get_annonces():` | SELECT query returning annonces JSON |
| `web.py` | `def update_annonce(` | PATCH handler for single annonce |
| `web.py` | `def bulk_update():` | PATCH handler for bulk toggle |
| `templates/index.html` | `.plu-btn:disabled` | Last action button CSS (insert after) |
| `templates/index.html` | `<th>Actions</th>` | Actions column header |
| `templates/index.html` | `<button class="plu-btn"` | Last action button in render() |
| `templates/index.html` | `// PLU download trigger` | Last binding block in bindRowEvents() |
| `templates/index.html` | `async function openHistoryModal` | History modal JS (reference for pattern) |
| `templates/index.html` | `async function patchOne` | API helper for PATCH |
| `templates/index.html` | `if (e.key === "Escape")` | Escape key handler for all modals |

### Technical Decisions

- `commentaire` is a TEXT field with a 2000-character limit enforced via `maxlength` on the HTML textarea (no server-side length validation, consistent with existing pattern, but bounded at UI level)
- PATCH validation: accept string or null (reject non-string types)
- The comment button is always visible (not conditional like PLU/Compare which require GPS coords)
- Modal follows existing pattern: dark header, white body, close via X/overlay/Escape
- Comment is persisted via the existing `patchOne()` JS helper (no new endpoint needed)
- All modals cross-close each other to prevent stacking
- `saveComment()` includes error handling with user feedback on failure and rollback of optimistic update
- Dirty-state protection: closing modal with unsaved changes triggers a confirmation prompt

## Implementation Plan

### Tasks

- [x] Task 1: Add `commentaire` column migration to `database.py` — `save_to_database()`
  - File: `database.py`
  - Anchor: Find the `migrations = [` list inside `def save_to_database(`
  - Action: Append `"ALTER TABLE annonces ADD COLUMN commentaire TEXT"` as the last entry in the `migrations` list (after the `list_id` line).
  - Notes: Follows existing pattern — try/except OperationalError silently passes if column already exists.

- [x] Task 2: Add `commentaire` column migration to `database.py` — `save_or_merge()`
  - File: `database.py`
  - Anchor: Find the `migrations = [` list inside `def save_or_merge(`
  - Action: Append `"ALTER TABLE annonces ADD COLUMN commentaire TEXT"` as the last entry in the `migrations` list (after the `list_id` line).
  - Notes: Same migration pattern as Task 1, duplicated here because both functions independently init the schema.

- [x] Task 3: Add `commentaire` column migration to `web.py` — `ensure_columns()`
  - File: `web.py`
  - Anchor: Find the `for sql in [` list inside `def ensure_columns():`
  - Action: Append `"ALTER TABLE annonces ADD COLUMN commentaire TEXT"` as the last entry in the migration list (after the `date_publication` line).
  - Notes: This runs at Flask startup to ensure the web UI can read/write the column immediately.

- [x] Task 4: Add `commentaire` to `EDITABLE_FIELDS` whitelist
  - File: `web.py`
  - Anchor: Find `EDITABLE_FIELDS = {`
  - Action: Add `"commentaire"` to the set: `{"note", "nogo", "viabilise", "partiellement_constructible", "partiellement_agricole", "commentaire"}`.
  - Notes: This allows the existing PATCH endpoint to accept `commentaire` updates.

- [x] Task 5: Add `commentaire` to the `get_annonces()` SELECT query
  - File: `web.py`
  - Anchor: Find the `SELECT` statement inside `def get_annonces():`
  - Action: Add `a.commentaire, ` to the SELECT column list, after `a.note, ` (before `a.lat`).
  - Notes: This ensures the comment is returned in the API response for the frontend to display.

- [x] Task 6: Add `commentaire` validation in `update_annonce()` AND fix boolean validation loop
  - File: `web.py`
  - Anchor: Find `def update_annonce(annonce_id):`
  - Action — TWO changes required:
    1. **Fix boolean validation loop**: Change `for bool_field in EDITABLE_FIELDS - {"note"}:` to `for bool_field in EDITABLE_FIELDS - {"note", "commentaire"}:` — this EXCLUDES `commentaire` from the boolean 0/1/null check. Without this fix, any string comment value will be rejected with a false 400 error.
    2. **Add commentaire validation**: Add a new validation block BEFORE the boolean loop:
       ```python
       # Validate commentaire (text field)
       if "commentaire" in updates:
           val = updates["commentaire"]
           if val is not None and not isinstance(val, str):
               return jsonify({"error": "commentaire must be a string or null"}), 400
       ```
  - Notes: This is the most critical task — getting the validation order wrong will break the entire feature.

- [x] Task 7: Protect `commentaire` from `bulk_update()` corruption
  - File: `web.py`
  - Anchor: Find `def bulk_update():`
  - Action: Add a guard at the beginning of the function, after the `field` validation against `EDITABLE_FIELDS`:
    ```python
    # Text fields cannot be bulk-toggled (only boolean fields support 0/1 toggle)
    if field == "commentaire":
        return jsonify({"error": "commentaire cannot be bulk-updated"}), 400
    ```
  - Notes: Without this, a bulk PATCH could set `commentaire = 0` or `commentaire = 1` (integer instead of text), corrupting data.

- [x] Task 8: Add comment button CSS
  - File: `templates/index.html`
  - Anchor: Find `.plu-btn:disabled {` block — insert AFTER its closing `}`
  - Action: Add the following CSS:
    ```css
    .comment-btn {
      padding: 3px 8px; background: #8b5cf6; color: #fff; border: none;
      border-radius: 4px; font-size: 11px; cursor: pointer; white-space: nowrap;
      font-weight: 600;
    }
    .comment-btn:hover { background: #7c3aed; }
    .comment-btn.has-comment {
      background: #7c3aed;
      box-shadow: 0 0 0 2px #c4b5fd;
    }
    ```
  - Notes: Purple color distinguishes from existing buttons (blue=history, teal=compare, orange=PLU). The `has-comment` variant uses a visible purple ring (`box-shadow`) instead of a barely-perceptible shade change to ensure clear visual distinction.

- [x] Task 9: Add comment modal CSS
  - File: `templates/index.html`
  - Anchor: Insert immediately after the `.comment-btn.has-comment` block from Task 8
  - Action: Add the following CSS:
    ```css
    .comment-textarea {
      width: 100%; min-height: 150px; padding: 10px;
      border: 1px solid #cbd5e1; border-radius: 6px;
      font-family: inherit; font-size: 13px; resize: vertical;
    }
    .comment-textarea:focus {
      outline: none; border-color: #8b5cf6;
      box-shadow: 0 0 0 3px rgba(139, 92, 246, .15);
    }
    .comment-actions {
      display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px;
    }
    .comment-save-btn {
      padding: 6px 16px; background: #8b5cf6; color: #fff; border: none;
      border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer;
    }
    .comment-save-btn:hover { background: #7c3aed; }
    .comment-cancel-btn {
      padding: 6px 16px; background: #f1f5f9; color: #64748b;
      border: 1px solid #cbd5e1; border-radius: 4px;
      font-size: 12px; cursor: pointer;
    }
    .comment-cancel-btn:hover { background: #e2e8f0; }
    ```
  - Notes: Purple accent matches the button color. Textarea limited visually by min-height.

- [x] Task 10: Add comment modal HTML
  - File: `templates/index.html`
  - Anchor: Find the closing `</div>` of the Compare modal (`id="compareModal"`) — insert AFTER it
  - Action: Add:
    ```html
    <!-- Comment modal -->
    <div id="commentModal" class="modal-overlay" style="display:none" role="dialog" aria-modal="true" aria-label="Commentaire">
      <div class="modal-dialog" style="max-width:560px">
        <div class="modal-header">
          <span id="commentTitle">Commentaire</span>
          <button id="commentClose" aria-label="Fermer">&#x2715;</button>
        </div>
        <div class="modal-body">
          <textarea id="commentTextarea" class="comment-textarea" placeholder="Ajouter un commentaire..." maxlength="2000"></textarea>
          <div class="comment-actions">
            <button class="comment-cancel-btn" id="commentCancel">Annuler</button>
            <button class="comment-save-btn" id="commentSave">Enregistrer</button>
          </div>
        </div>
      </div>
    </div>
    ```
  - Notes: Smaller max-width (560px) than history/compare modals. `maxlength="2000"` prevents excessively long comments from bloating the DB.

- [x] Task 11: Add comment button to render() Actions column
  - File: `templates/index.html`
  - Anchor: Find the `<td>` that contains action buttons in the `render()` function — look for the line with `hist-btn`
  - Action: Add a comment button as the FIRST button in the Actions `<td>`, before the history button:
    ```js
    `<button class="comment-btn${a.commentaire ? ' has-comment' : ''}" data-id="${a.id}" aria-label="Commentaire">${String.fromCodePoint(0x1F4AC)}</button> `
    ```
  - Notes: The button is always visible (no condition). The `has-comment` class provides a purple ring when a comment exists. `aria-label="Commentaire"` ensures screen reader accessibility.

- [x] Task 12: Add comment modal JS logic
  - File: `templates/index.html`
  - Anchor: Find `function closeCompareModal()` — insert the new functions AFTER the closing `}` of that function
  - Action: Add the following JS:
    ```js
    // ── Comment modal ──────────────────────────────────────────────
    let commentCurrentId = null;
    let commentOriginal = null;

    function openCommentModal(id) {
      closeHistoryModal();
      closeCompareModal();
      const ann = allData.find(x => x.id === id);
      commentCurrentId = id;
      commentOriginal = ann ? (ann.commentaire || "") : "";
      document.getElementById("commentTitle").textContent =
        ann ? `Commentaire — ${ann.titre || "annonce #" + id}` : `Commentaire #${id}`;
      document.getElementById("commentTextarea").value = commentOriginal;
      document.getElementById("commentModal").style.display = "flex";
      document.getElementById("commentTextarea").focus();
    }

    function closeCommentModal(force) {
      const textarea = document.getElementById("commentTextarea");
      if (!force && textarea.value !== commentOriginal) {
        if (!confirm("Fermer sans enregistrer les modifications ?")) return;
      }
      document.getElementById("commentModal").style.display = "none";
      textarea.value = "";
      commentCurrentId = null;
      commentOriginal = null;
    }

    async function saveComment() {
      const textarea = document.getElementById("commentTextarea");
      const raw = textarea.value.trim();
      const value = raw === "" ? null : raw;

      // Skip PATCH if value unchanged
      if (value === (allData.find(x => x.id === commentCurrentId)?.commentaire || null)) {
        closeCommentModal(true);
        return;
      }

      try {
        const res = await fetch(`/api/annonces/${commentCurrentId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ commentaire: value }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          alert(err.error || "Erreur lors de l'enregistrement du commentaire.");
          return;
        }
        const ann = allData.find(x => x.id === commentCurrentId);
        if (ann) ann.commentaire = value;
        closeCommentModal(true);
        render();
      } catch (err) {
        alert("Erreur réseau lors de l'enregistrement du commentaire.");
      }
    }
    ```
  - Notes: Key differences from original spec:
    - `commentOriginal` tracks initial value to detect dirty state
    - `closeCommentModal(force)` — prompts confirmation if textarea was modified (unless `force=true` from `saveComment`)
    - `saveComment()` skips PATCH if value unchanged, checks `res.ok`, shows error alert on failure, does NOT mutate `allData` until PATCH succeeds (no optimistic update)
    - Uses direct `fetch` instead of `patchOne()` to enable error handling

- [x] Task 13: Update `openHistoryModal` and `openCompareModal` to close comment modal
  - File: `templates/index.html`
  - Anchor: Find `async function openHistoryModal(id)` — find the `closeCompareModal()` call at the start of the function
  - Action: Add `closeCommentModal(true);` immediately after `closeCompareModal();` inside `openHistoryModal`.
  - Anchor: Find `async function openCompareModal(id)` — find the `closeHistoryModal()` call at the start of the function
  - Action: Add `closeCommentModal(true);` immediately after `closeHistoryModal();` inside `openCompareModal`.
  - Notes: This prevents modal stacking. `true` forces close without dirty-state prompt (switching modal is an intentional action).

- [x] Task 14: Bind comment button events in `bindRowEvents()`
  - File: `templates/index.html`
  - Anchor: Find the `.plu-btn` forEach binding block inside `function bindRowEvents()` — insert AFTER the closing `});` of that block, but still INSIDE `bindRowEvents()`
  - Action: Add:
    ```js
    // Comment trigger
    document.querySelectorAll(".comment-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openCommentModal(parseInt(btn.dataset.id));
      });
    });
    ```
  - Notes: Same pattern as `.hist-btn`, `.cmp-btn`, `.plu-btn` bindings.

- [x] Task 15: Bind comment modal close handlers
  - File: `templates/index.html`
  - Anchor: Find the `compareModal` click handler (the line `document.getElementById("compareModal").addEventListener("click"`) — insert AFTER its closing `);`
  - Action: Add:
    ```js
    document.getElementById("commentClose").addEventListener("click", () => closeCommentModal());
    document.getElementById("commentCancel").addEventListener("click", () => closeCommentModal());
    document.getElementById("commentSave").addEventListener("click", saveComment);
    document.getElementById("commentModal").addEventListener("click", function(e) {
      if (e.target === this) closeCommentModal();
    });
    ```
  - Anchor: Find the Escape key handler: `if (e.key === "Escape") { closeHistoryModal(); closeCompareModal(); }`
  - Action: Add `closeCommentModal();` inside the block: `if (e.key === "Escape") { closeHistoryModal(); closeCompareModal(); closeCommentModal(); }`
  - Notes: Close handlers use `() => closeCommentModal()` (no `force`) so dirty-state prompt triggers. Save button calls `saveComment` directly.

### Acceptance Criteria

- [ ] AC1: Given the database has no `commentaire` column, when the Flask server starts, then the column is created automatically via migration (no error).
- [ ] AC2: Given an annonce exists, when GET `/api/annonces` is called, then the response includes the `commentaire` field (null if empty).
- [ ] AC3: Given an annonce with id=1, when PATCH `/api/annonces/1` is called with `{"commentaire": "Terrain intéressant"}`, then the comment is saved and the response is `{"updated": 1}`.
- [ ] AC4: Given an annonce with id=1, when PATCH `/api/annonces/1` is called with `{"commentaire": null}`, then the comment is cleared and the response is `{"updated": 1}`.
- [ ] AC5: Given an annonce with id=1, when PATCH `/api/annonces/1` is called with `{"commentaire": 123}` (non-string), then the response is 400 with an error message.
- [ ] AC6: Given the main table is rendered, when the user sees the Actions column, then every row has a comment button (purple, with speech bubble emoji and `aria-label="Commentaire"`).
- [ ] AC7: Given an annonce has a non-null commentaire, when the table renders, then the comment button has the `has-comment` class (purple ring visible).
- [ ] AC8: Given the user clicks the comment button on a row, when the comment modal opens, then the modal title shows the annonce titre, the textarea contains the existing comment (or is empty), and any other open modal is closed.
- [ ] AC9: Given the comment modal is open with text in the textarea, when the user clicks "Enregistrer", then the comment is saved via PATCH, the modal closes, and the table re-renders. If the PATCH fails, an error alert is shown and the modal stays open.
- [ ] AC10: Given the comment modal is open with UNCHANGED text, when the user clicks Cancel/X/overlay/Escape, then the modal closes without prompt.
- [ ] AC11: Given the comment modal is open with MODIFIED text, when the user clicks Cancel/X/overlay/Escape, then a confirmation prompt appears. If confirmed, the modal closes without saving. If cancelled, the modal stays open.
- [ ] AC12: Given the comment modal is open with unchanged text, when the user clicks "Enregistrer", then no PATCH request is made and the modal closes silently.
- [ ] AC13: Given selected annonces, when the user attempts a bulk PATCH with `field: "commentaire"`, then the server returns 400 with error "commentaire cannot be bulk-updated".

## Additional Context

### Dependencies

- No new dependencies required. All changes use existing Flask, SQLite3, and vanilla JS.

### Testing Strategy

- **Manual testing steps:**
  1. Start the Flask server and verify no migration errors in console.
  2. Open the web UI and verify the comment button (purple speech bubble) appears on every row in the Actions column.
  3. Click the comment button — verify the modal opens with the correct title, an empty textarea, and focus on the textarea.
  4. Type a comment, click "Enregistrer" — verify the modal closes and the button now has a purple ring (`has-comment` style).
  5. Reopen the comment modal — verify the saved comment appears in the textarea.
  6. Clear the textarea and save — verify the comment is removed (button loses purple ring).
  7. Type text in the modal and click "Annuler" — verify a confirmation prompt appears. Click "Cancel" in the prompt — modal stays open. Click "OK" — modal closes, comment is NOT saved.
  8. Open the modal (no changes), press Escape — verify the modal closes without prompt.
  9. Open the modal, click the overlay background — verify same close behavior (with prompt if dirty).
  10. Open the comment modal, then click a History button on another row — verify the comment modal closes and the history modal opens.
  11. Verify that PATCH with a non-string value returns a 400 error: `curl -X PATCH http://localhost:5000/api/annonces/1 -H "Content-Type: application/json" -d '{"commentaire": 123}'`
  12. Verify bulk update protection: `curl -X PATCH http://localhost:5000/api/annonces/bulk -H "Content-Type: application/json" -d '{"ids": [1], "field": "commentaire", "value": 1}'` — should return 400.
  13. Verify that saving an unchanged comment does NOT trigger a network request (check DevTools Network tab).

### Notes

- The comment is a single text field per annonce, not linked to history snapshots
- User preference: modal UX consistent with existing History/Compare/PLU modals
- The purple color (#8b5cf6) was chosen to distinguish from existing action buttons and maintain visual hierarchy
- `commentaire` is NOT included in `annonces_history` snapshots — the scraper's `save_or_merge()` UPDATE does not touch user-set columns, so comments survive re-scrapes
- Known pre-existing issue: `ensure_columns()` in web.py has fewer migrations than `database.py` — this spec does NOT fix that (out of scope)
