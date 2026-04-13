---
title: 'Persistance des filtres et tri — localStorage'
slug: 'persist-filters-localstorage'
created: '2026-04-13'
status: 'completed'
stepsCompleted: [1, 2, 3, 4, 5]
tech_stack: ['Flask', 'Vanilla JS', 'HTML', 'SQLite', 'localStorage API']
files_to_modify: ['templates/index.html']
code_patterns: ['module-level sort state (sortCol/sortDir)', 'render() called on every filter/sort change', 'DOM-driven filter reads in getFiltered()']
test_patterns: ['no JS tests - backend API tests only in tests/test_web_api.py']
---

# Tech-Spec: Persistance des filtres et tri — localStorage

**Created:** 2026-04-13

## Overview

### Problem Statement

Les filtres de recherche et l'état du tri se perdent à chaque rechargement de la page. L'utilisateur doit ressaisir ses critères à chaque session.

### Solution

Sauvegarder l'état complet des filtres et du tri dans `localStorage` sous la clé `lbc_filters` à chaque changement. Charger automatiquement cet état au démarrage de la page.

### Scope

**In Scope:**
- 14 filtres : `hideNogo`, `hideDeleted`, `fPrixMin`, `fPrixMax`, `fSurfMin`, `fSurfMax`, `fPm2Min`, `fPm2Max`, `fTrajetMax`, `fNoteMin`, `fViabilise`, `fConstruct`, `fAgricole`, `fStatus`
- État du tri actif (colonne + direction)
- Chargement automatique au démarrage
- Bouton "Réinitialiser" efface `localStorage` + remet les champs à vide

**Out of Scope:**
- Visibilité des colonnes (toggle-col)
- Persistance côté serveur

## Context for Development

### Codebase Patterns

- Vanilla JS monolithique dans `templates/index.html` — aucun framework, aucun bundler
- État du tri stocké dans variables module-level : `let sortCol = null; let sortDir = 1;` (lignes 496–497)
- Filtres lus depuis le DOM dans `getFiltered()` (lignes 572–606) via `document.getElementById(id).value` / `.checked`
- `render()` est le point d'entrée unique après tout changement filtre/tri — appelé par chaque event listener
- Le bouton "Réinitialiser" (ligne 1189) : clear DOM + `render()` — pas de state centralisé
- Le bouton "Map" (ligne 1200) sérialise déjà les filtres en query params — pattern de référence pour la sérialisation

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `templates/index.html` | Seul fichier à modifier — contient tout le JS inline |

### Technical Decisions

- **`saveFilters()`** appelé à la fin de `render()` — couvre automatiquement tous les cas (filtres + tri)
- **`loadFilters()`** appelé au démarrage avant `loadData()` — filtres actifs avant le premier render
- **Reset** : ajouter `localStorage.removeItem('lbc_filters')` dans le handler existant `resetFilters`
- **Clé localStorage** : `lbc_filters`
- **Structure JSON** : `{ hideNogo, hideDeleted, fPrixMin, fPrixMax, fSurfMin, fSurfMax, fPm2Min, fPm2Max, fTrajetMax, fNoteMin, fViabilise, fConstruct, fAgricole, fStatus, sortCol, sortDir }`
- Pas de tests JS à écrire — feature purement frontend, testée manuellement

## Implementation Plan

### Tasks

- [x] Task 1: Définir la fonction `saveFilters()`
  - File: `templates/index.html`
  - Action: Ajouter après la définition de `render()` (ligne ~668) la fonction suivante :
    ```js
    function saveFilters() {
      const v = id => document.getElementById(id).value;
      const state = {
        hideNogo:    document.getElementById("hideNogo").checked,
        hideDeleted: document.getElementById("hideDeleted").checked,
        fPrixMin:    v("fPrixMin"),
        fPrixMax:    v("fPrixMax"),
        fSurfMin:    v("fSurfMin"),
        fSurfMax:    v("fSurfMax"),
        fPm2Min:     v("fPm2Min"),
        fPm2Max:     v("fPm2Max"),
        fTrajetMax:  v("fTrajetMax"),
        fNoteMin:    v("fNoteMin"),
        fViabilise:  v("fViabilise"),
        fConstruct:  v("fConstruct"),
        fAgricole:   v("fAgricole"),
        fStatus:     v("fStatus"),
        sortCol:     sortCol,
        sortDir:     sortDir,
      };
      localStorage.setItem("lbc_filters", JSON.stringify(state));
    }
    ```
  - Notes: Utilise le même pattern `v = id => ...value` que le bouton Map (ligne 1203)

- [x] Task 2: Appeler `saveFilters()` à la fin de `render()`
  - File: `templates/index.html`
  - Action: Dans la fonction `render()`, ajouter `saveFilters();` comme dernière instruction avant la fermeture `}` (après `bindRowEvents(); updateToolbar();`)
  - Notes: `render()` est appelé par tous les event listeners filtres ET le tri — un seul point d'injection suffit

- [x] Task 3: Définir la fonction `loadFilters()`
  - File: `templates/index.html`
  - Action: Ajouter après `saveFilters()` :
    ```js
    function loadFilters() {
      const raw = localStorage.getItem("lbc_filters");
      if (!raw) return;
      let state;
      try { state = JSON.parse(raw); } catch { return; }
      const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ""; };
      const setChk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };
      setChk("hideNogo",    state.hideNogo);
      setChk("hideDeleted", state.hideDeleted);
      set("fPrixMin",   state.fPrixMin);
      set("fPrixMax",   state.fPrixMax);
      set("fSurfMin",   state.fSurfMin);
      set("fSurfMax",   state.fSurfMax);
      set("fPm2Min",    state.fPm2Min);
      set("fPm2Max",    state.fPm2Max);
      set("fTrajetMax", state.fTrajetMax);
      set("fNoteMin",   state.fNoteMin);
      set("fViabilise", state.fViabilise);
      set("fConstruct", state.fConstruct);
      set("fAgricole",  state.fAgricole);
      set("fStatus",    state.fStatus);
      if (state.sortCol) {
        sortCol = state.sortCol;
        sortDir = state.sortDir ?? 1;
        const th = document.querySelector(`thead th[data-col="${sortCol}"]`);
        if (th) th.classList.add(sortDir === 1 ? "sorted-asc" : "sorted-desc");
      }
    }
    ```
  - Notes: Le `try/catch` protège contre un localStorage corrompu. Les `??` assurent qu'une valeur manquante donne `""` et non `"undefined"`

- [x] Task 4: Appeler `loadFilters()` avant `loadData()`
  - File: `templates/index.html`
  - Action: Trouver l'appel à `loadData()` au bas du script (après tous les event listeners). Ajouter `loadFilters();` sur la ligne précédente.
  - Notes: `loadFilters()` restaure l'état DOM + `sortCol`/`sortDir`. Quand `loadData()` appelle `render()`, les filtres sont déjà actifs.

- [x] Task 5: Modifier le handler `resetFilters` pour effacer le localStorage
  - File: `templates/index.html`
  - Action: Dans le handler `document.getElementById("resetFilters").addEventListener("click", ...)` (ligne 1189), ajouter `localStorage.removeItem("lbc_filters");` comme **première** instruction du callback, avant les `.forEach`.
  - Notes: L'ordre est important — effacer avant que `render()` (via la fin du callback) ne rappelle `saveFilters()`. Le `render()` final de `saveFilters()` sera déclenché, mais le localStorage aura déjà été supprimé donc `saveFilters()` re-sauvera un état vide — comportement correct.

### Acceptance Criteria

- [ ] AC 1: Given que l'utilisateur a défini des filtres (ex: Prix min 50000, Superficie max 2000), when il recharge la page, then les champs de filtres affichent les mêmes valeurs et le tableau est déjà filtré.

- [ ] AC 2: Given que l'utilisateur a trié le tableau par "Prix" (colonne ascending), when il recharge la page, then le tableau est trié par Prix ascending et la colonne affiche l'indicateur `▲`.

- [ ] AC 3: Given que des filtres sont actifs et sauvegardés, when l'utilisateur clique "Réinitialiser", then tous les champs sont vidés, le tri est réinitialisé, ET `localStorage.getItem("lbc_filters")` retourne `null`.

- [ ] AC 4: Given que le localStorage est vide ou absent, when la page se charge, then aucun filtre n'est appliqué (comportement identique à avant la feature).

- [ ] AC 5: Given que le localStorage contient une valeur JSON invalide (corrompue), when la page se charge, then la page s'affiche normalement sans erreur console (le `try/catch` absorbe l'erreur).

- [ ] AC 6: Given que des filtres sont actifs, when l'utilisateur change n'importe quel filtre ou tri, then `localStorage.getItem("lbc_filters")` reflète immédiatement le nouvel état.

## Additional Context

### Dependencies

- Aucune dépendance externe — `localStorage` est natif au navigateur
- Compatible avec tous les navigateurs modernes (Chrome, Firefox, Safari, Edge)
- Aucun changement côté serveur (Flask, Python, SQLite) requis

### Testing Strategy

- **Tests automatisés :** Aucun (pas de framework JS de test dans le projet)
- **Test manuel — Happy path :**
  1. Ouvrir l'app, définir Prix min = 50000, cocher "Masquer nogo", trier par "Prix"
  2. Recharger la page (F5)
  3. Vérifier : champ Prix min = 50000, case cochée, tri Prix actif
- **Test manuel — Reset :**
  1. Appliquer des filtres, recharger pour vérifier la persistance
  2. Cliquer "Réinitialiser"
  3. Recharger la page → tous les filtres doivent être vides
- **Test manuel — Edge case localStorage corrompu :**
  1. DevTools → Application → localStorage → modifier `lbc_filters` avec une valeur non-JSON (ex: `"broken"`)
  2. Recharger → la page doit s'afficher normalement, sans erreur

## Review Notes
- Revue adversariale complétée
- Findings : 10 total, 4 fixés (F1+F9+F2+F10), 6 skippés (noise/hors-scope)
- Approach : auto-fix
- Fixes supplémentaires : reset `sortCol`/`sortDir` + nettoyage classes visuelles dans resetFilters ; protection try/catch sur localStorage.setItem/getItem

### Notes

- **Risque :** Si `saveFilters()` est appelé dans `render()`, et que `render()` est aussi appelé lors du `loadData()` initial, alors au premier chargement avant `loadFilters()` un état vide serait sauvegardé — c'est pourquoi `loadFilters()` DOIT être appelé AVANT `loadData()` (Task 4).
- **Limite connue :** La persistance est par-navigateur et par-domaine. Si l'utilisateur ouvre l'app dans un autre navigateur, ses filtres ne sont pas portés.
- **Futur (hors scope) :** Persistance côté serveur pour synchronisation multi-appareils.
