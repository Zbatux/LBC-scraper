---
title: 'Column Visibility Toggle'
slug: 'column-visibility-toggle'
created: '2026-04-16'
status: 'completed'
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
tech_stack: ['Vanilla JS', 'HTML/CSS', 'localStorage API']
files_to_modify: ['templates/index.html']
code_patterns: ['single-file frontend', 'localStorage save/load pattern', 'querySelectorAll data-col', 'string template literal row rendering']
test_patterns: ['manual browser testing only — no frontend test framework']
---

# Tech-Spec: Column Visibility Toggle

**Created:** 2026-04-16

## Overview

### Problem Statement

Le tableau de la page principale est large (17 colonnes) et certaines colonnes sont rarement utiles selon le contexte. Il n'existe aucun moyen de masquer les colonnes non pertinentes, ce qui nuit à la lisibilité.

### Solution

Ajouter un bouton "Colonnes ⚙" dans la barre de filtres qui ouvre un dropdown avec une checkbox par colonne masquable. L'état de visibilité est persisté en `localStorage` sous la clé `lbc_col_visibility`.

### Scope

**In Scope:**
- Bouton "Colonnes ⚙" dans `#filters`
- Dropdown avec checkboxes pour les 14 colonnes masquables
- Masquage/affichage via `column.style.display = 'none'` / `''`
- Persistance en `localStorage` clé `lbc_col_visibility`
- Toutes les colonnes visibles par défaut (premier lancement)

**Out of Scope:**
- Réordonnancement des colonnes
- Responsive / breakpoints automatiques
- Colonnes toujours fixes : sel-cell (checkbox), Titre, Actions

## Context for Development

### Codebase Patterns

- Frontend monofichier : `templates/index.html` — 1351 lignes, HTML + CSS + JS inline, aucun framework ni bundler
- Les `<th>` triables ont `data-col="..."` (ex: `data-col="status"`) — les `<td>` n'en ont PAS encore
- Lignes générées par template literal dans `render()` (lignes 645–678) — chaque `<td>` est hardcodé en position
- `localStorage` pattern existant : `saveFilters()` / `loadFilters()` lignes 687–740, avec try/catch — à reproduire exactement
- Aucun dropdown existant — pattern à créer from scratch
- Fermeture au clic extérieur : absente du code — implémentée via `document.addEventListener('click', ...)` avec `closest('#colPickerPanel, #colPickerBtn')`
- Touche Escape : gestionnaire global ligne 1341–1343 — à étendre pour fermer le dropdown
- `resetFilters` (ligne 1290) efface `lbc_filters` mais NE DOIT PAS effacer `lbc_col_visibility`

### Mapping colonnes toggleables (14 colonnes, dans l'ordre du tableau)

| Index TD | data-col | Label affiché |
|---|---|---|
| 1 | `status` | Statut |
| 2 | `first_seen` | 1ère vue |
| 3 | `date_publication` | Publié le |
| 5 | `prix` | Prix € |
| 6 | `superficie` | Surf. m² |
| 7 | `prix_m2` | €/m² |
| 8 | `trajet` | Trajet |
| 9 | `viabilise` | Viabilisé |
| 10 | `partiellement_constructible` | Part. const. |
| 11 | `partiellement_agricole` | Part. agri. |
| 12 | `emprise_sol` | Emprise % |
| 13 | `note` | Note |
| 14 | `nogo` | Nogo |
| 15 | `a_visiter` | ★ |

Colonnes fixes (index 0 = sel-cell, 4 = titre, 16 = Actions) — pas de `data-col` à ajouter.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `templates/index.html` | Unique fichier frontend — HTML, CSS, JS tout-en-un |
| `tests/test_web_api.py` | Tests Flask API uniquement — pas de tests frontend |

### Technical Decisions

- **`data-col` sur les `<td>`** : ajouter l'attribut sur chaque `<td>` toggleable dans le template literal de `render()` — permet `querySelectorAll('[data-col="X"]')` pour cibler `<th>` + tous les `<td>` en une seule passe
- **Clé localStorage** : `lbc_col_visibility` — objet `{ status: true, first_seen: true, ... }`. Absent du storage = toutes visibles (défaut)
- **Fonctions** : `saveColVisibility()` / `loadColVisibility()` / `applyColVisibility()` — pattern calqué sur `saveFilters`/`loadFilters`
- **`applyColVisibility()`** appelée après chaque `render()` et après `loadData()`
- **Dropdown HTML** : `<div id="colPickerBtn">` + `<div id="colPickerPanel">` positionnés dans `#filters` avant le bouton `#resetFilters`
- **CSS dropdown** : `position: absolute`, `z-index` élevé, `display: none` par défaut, `.open` pour afficher
- **NE PAS toucher** `resetFilters` — il ne doit pas effacer `lbc_col_visibility`

## Implementation Plan

### Tasks

- [x] Task 1 : Déclarer la constante `TOGGLEABLE_COLS`
  - File: `templates/index.html`
  - Action: Ajouter dans la section `// ── State ───` (après ligne 512) la constante suivante :
    ```js
    const TOGGLEABLE_COLS = [
      { col: 'status',                       label: 'Statut' },
      { col: 'first_seen',                   label: '1ère vue' },
      { col: 'date_publication',             label: 'Publié le' },
      { col: 'prix',                         label: 'Prix €' },
      { col: 'superficie',                   label: 'Surf. m²' },
      { col: 'prix_m2',                      label: '€/m²' },
      { col: 'trajet',                       label: 'Trajet' },
      { col: 'viabilise',                    label: 'Viabilisé' },
      { col: 'partiellement_constructible',  label: 'Part. const.' },
      { col: 'partiellement_agricole',       label: 'Part. agri.' },
      { col: 'emprise_sol',                  label: 'Emprise %' },
      { col: 'note',                         label: 'Note' },
      { col: 'nogo',                         label: 'Nogo' },
      { col: 'a_visiter',                    label: '★' },
    ];
    let colVisibility = {}; // { col: true|false }
    ```
  - Notes: Doit être déclaré avant toute fonction qui l'utilise.

- [x] Task 2 : Ajouter les styles CSS du dropdown
  - File: `templates/index.html`
  - Action: Ajouter dans le bloc `<style>` (après le style de `#resetFilters:hover`, ligne ~55) :
    ```css
    /* ── Column picker ───────────────────────────────────────── */
    #colPickerWrap { position: relative; }
    #colPickerBtn {
      padding: 4px 10px; background: #f1f5f9; border: 1px solid #cbd5e1;
      border-radius: 4px; cursor: pointer; font-size: 12px;
    }
    #colPickerBtn:hover { background: #e2e8f0; }
    #colPickerPanel {
      display: none; position: absolute; top: calc(100% + 4px); left: 0;
      background: #fff; border: 1px solid #cbd5e1; border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,.12); padding: 8px 12px;
      z-index: 200; min-width: 160px;
    }
    #colPickerPanel.open { display: block; }
    .col-pick-label {
      display: flex; align-items: center; gap: 6px;
      padding: 3px 0; cursor: pointer; font-size: 12px; white-space: nowrap;
    }
    .col-pick-label input { cursor: pointer; }
    ```
  - Notes: `z-index: 200` suffit — aucun autre élément positionné n'interfère.

- [x] Task 3 : Ajouter le HTML du bouton et du panneau dans `#filters`
  - File: `templates/index.html`
  - Action: Dans le `<div id="filters">` (ligne ~356), ajouter juste avant `<button id="resetFilters">` :
    ```html
    <div id="colPickerWrap">
      <button id="colPickerBtn">Colonnes ⚙</button>
      <div id="colPickerPanel">
        <!-- Rempli dynamiquement par JS -->
      </div>
    </div>
    ```
  - Notes: Le `<div id="colPickerWrap">` est le conteneur relatif pour le positionnement absolu du panneau.

- [x] Task 4 : Ajouter `data-col` sur les `<td>` dans `render()`
  - File: `templates/index.html`
  - Action: Dans le template literal `tr.innerHTML = \`` (lignes 650–677), modifier les 14 `<td>` toggleables pour ajouter `data-col="..."`. Les 3 fixes (`sel-cell`, `titre-cell`, `Actions`) restent inchangés. Résultat :
    ```js
    <td data-col="status">${statusBadge(a.status)}</td>
    <td data-col="first_seen">${fmtDate(a.first_seen)}</td>
    <td data-col="date_publication">${fmtDate(a.date_publication)}</td>
    <td class="titre-cell" ...>...</td>   <!-- inchangé -->
    <td data-col="prix">...</td>
    <td data-col="superficie">...</td>
    <td data-col="prix_m2">...</td>
    <td data-col="trajet">${a.trajet || "—"}</td>
    <td data-col="viabilise">${badge(a.viabilise)}</td>
    <td data-col="partiellement_constructible">${badge(a.partiellement_constructible)}</td>
    <td data-col="partiellement_agricole">${badge(a.partiellement_agricole)}</td>
    <td data-col="emprise_sol">...</td>
    <td data-col="note" class="note-cell" ...>...</td>
    <td data-col="nogo" class="nogo-cell">...</td>
    <td data-col="a_visiter" class="avisiter-cell" ...>...</td>
    ```
  - Notes: La `<td class="note-cell">` et `<td class="avisiter-cell">` conservent leurs classes existantes en plus du `data-col`.

- [x] Task 5 : Implémenter les fonctions localStorage col visibility
  - File: `templates/index.html`
  - Action: Ajouter dans la section `// ── Filter persistence ───` (après `loadFilters()`, ligne ~740) :
    ```js
    function saveColVisibility() {
      try { localStorage.setItem("lbc_col_visibility", JSON.stringify(colVisibility)); } catch { /* quota/private */ }
    }

    function loadColVisibility() {
      let raw;
      try { raw = localStorage.getItem("lbc_col_visibility"); } catch { return; }
      if (!raw) return;
      try { Object.assign(colVisibility, JSON.parse(raw)); } catch { /* ignore */ }
    }
    ```
  - Notes: `Object.assign` sur `colVisibility` préserve les défauts `true` pour les colonnes absentes du storage (colonnes ajoutées ultérieurement).

- [x] Task 6 : Implémenter `applyColVisibility()` et `initColPicker()`
  - File: `templates/index.html`
  - Action: Ajouter immédiatement après les fonctions de Task 5 :
    ```js
    function applyColVisibility() {
      TOGGLEABLE_COLS.forEach(({ col }) => {
        const visible = colVisibility[col] !== false; // défaut true
        const display = visible ? '' : 'none';
        document.querySelectorAll(`[data-col="${col}"]`).forEach(el => {
          el.style.display = display;
        });
      });
    }

    function initColPicker() {
      const panel = document.getElementById('colPickerPanel');
      panel.innerHTML = TOGGLEABLE_COLS.map(({ col, label }) => `
        <label class="col-pick-label">
          <input type="checkbox" class="col-pick-cb" data-col="${col}"
            ${colVisibility[col] !== false ? 'checked' : ''} />
          ${label}
        </label>
      `).join('');

      panel.querySelectorAll('.col-pick-cb').forEach(cb => {
        cb.addEventListener('change', () => {
          colVisibility[cb.dataset.col] = cb.checked;
          saveColVisibility();
          applyColVisibility();
        });
      });
    }
    ```
  - Notes: `colVisibility[col] !== false` garantit `true` par défaut même si la clé est absente.

- [x] Task 7 : Appeler `applyColVisibility()` après chaque `render()`
  - File: `templates/index.html`
  - Action: Dans la fonction `render()`, ajouter `applyColVisibility();` comme dernière ligne du corps de la fonction (après `saveFilters();` ligne ~683) :
    ```js
    saveFilters();
    applyColVisibility();   // ← ajouter ici
    ```
  - Notes: Garantit que les lignes nouvellement injectées par `tbody.innerHTML = ""` + `appendChild` héritent de la visibilité courante.

- [x] Task 8 : Brancher le bouton dropdown et la fermeture au clic extérieur
  - File: `templates/index.html`
  - Action: Ajouter dans la section `// ── Modal close handlers ───` (avant `loadFilters()` à la fin) :
    ```js
    // ── Column picker ────────────────────────────────────────────
    document.getElementById('colPickerBtn').addEventListener('click', (e) => {
      e.stopPropagation();
      document.getElementById('colPickerPanel').classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('#colPickerWrap')) {
        document.getElementById('colPickerPanel').classList.remove('open');
      }
    });
    ```
  - Notes: `e.stopPropagation()` sur le bouton empêche le document listener de fermer immédiatement le panneau qu'on vient d'ouvrir.

- [x] Task 9 : Étendre le handler Escape existant pour fermer le dropdown
  - File: `templates/index.html`
  - Action: Modifier le handler Escape existant (ligne 1341) pour ajouter la fermeture du dropdown :
    ```js
    // Avant :
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") { closeHistoryModal(); closeCompareModal(); closeCommentModal(); }
    });

    // Après :
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") {
        closeHistoryModal(); closeCompareModal(); closeCommentModal();
        document.getElementById('colPickerPanel').classList.remove('open');
      }
    });
    ```

- [x] Task 10 : Initialiser au démarrage
  - File: `templates/index.html`
  - Action: Modifier le bloc `// ── Init ───` (lignes 1345–1347) :
    ```js
    // Avant :
    loadFilters();
    loadData();

    // Après :
    loadFilters();
    loadColVisibility();
    initColPicker();
    loadData();
    ```
  - Notes: `initColPicker()` doit être appelé après `loadColVisibility()` pour que les checkboxes reflètent l'état chargé. `applyColVisibility()` sera appelée par `render()` via `loadData()`.

### Acceptance Criteria

- [ ] AC 1 : Given la page chargée pour la première fois (pas de `lbc_col_visibility` en localStorage), when l'utilisateur clique sur "Colonnes ⚙", then le dropdown s'ouvre avec 14 checkboxes toutes cochées.

- [ ] AC 2 : Given le dropdown ouvert, when l'utilisateur décoche "Surf. m²", then la colonne `<th data-col="superficie">` et tous les `<td data-col="superficie">` passent à `display: none` immédiatement.

- [ ] AC 3 : Given une colonne masquée, when l'utilisateur recoche sa checkbox, then la colonne redevient visible immédiatement.

- [ ] AC 4 : Given des colonnes masquées (ex: "Surf. m²" décochée), when l'utilisateur recharge la page, then les mêmes colonnes sont masquées (état persisté en localStorage clé `lbc_col_visibility`).

- [ ] AC 5 : Given le dropdown ouvert, when l'utilisateur clique ailleurs sur la page, then le dropdown se ferme.

- [ ] AC 6 : Given le dropdown ouvert, when l'utilisateur appuie sur Échap, then le dropdown se ferme.

- [ ] AC 7 : Given des colonnes masquées, when l'utilisateur clique sur "Réinitialiser" (resetFilters), then les colonnes masquées restent masquées (lbc_col_visibility non affecté).

- [ ] AC 8 : Given une colonne masquée, when un filtre change et `render()` régénère les lignes, then la colonne reste masquée dans les nouvelles lignes.

- [ ] AC 9 : Given le dropdown ouvert, when l'utilisateur ouvre une modale (historique, comparaison, commentaire), then le dropdown se ferme (géré par le click-outside sur le overlay de la modale).

## Review Notes
- Adversarial review completed
- Findings: 10 total, 3 fixed (F1, F2, F8), 7 skipped (noise)
- Resolution approach: auto-fix

## Additional Context

### Dependencies

Aucune dépendance externe — vanilla JS et localStorage natifs.

### Testing Strategy

Aucun framework de test frontend. Tests manuels dans le navigateur :

1. Ouvrir la page → vérifier que "Colonnes ⚙" apparaît dans la barre de filtres
2. Cliquer le bouton → vérifier ouverture du dropdown avec 14 cases cochées
3. Décocher "Surf. m²" → vérifier masquage immédiat colonne + `display: none` dans le DOM (DevTools)
4. Recharger la page → vérifier persistance du masquage
5. Cocher à nouveau → vérifier réapparition
6. Filtrer les annonces → vérifier que les nouvelles lignes respectent la visibilité
7. Cliquer "Réinitialiser" → vérifier que les colonnes masquées le restent
8. Ouvrir dropdown → cliquer ailleurs → vérifier fermeture
9. Ouvrir dropdown → appuyer Échap → vérifier fermeture

### Notes

- **Risque principal** : `applyColVisibility()` appelée après `render()` — si un futur render oubliait l'appel, les lignes ne respecteraient pas la visibilité. Toujours vérifier après modification de `render()`.
- **Limitation connue** : La colonne `Actions` n'est pas toggleable (contient des boutons fonctionnels critiques).
- **Future consideration (hors scope)** : Un bouton "Tout afficher" dans le panneau pour reset rapide de la visibilité.
