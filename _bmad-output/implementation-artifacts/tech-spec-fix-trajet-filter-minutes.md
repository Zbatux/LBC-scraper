---
title: 'Fix du parsing des minutes dans le filtre trajet max'
slug: 'fix-trajet-filter-minutes'
created: '2026-03-15'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['JavaScript (frontend)', 'HTML']
files_to_modify: ['templates/index.html']
code_patterns: ['trajetToMin() regex parsing']
test_patterns: []
---

# Tech-Spec: Fix du parsing des minutes dans le filtre trajet max

**Created:** 2026-03-15

## Overview

### Problem Statement

La fonction `trajetToMin()` dans `templates/index.html` parse les durées de trajet avec la regex `/(\d+)min/` pour les minutes. Quand l'utilisateur saisit une valeur dans le filtre trajet max au format `Xh YY` (ex: `1h 30`), les minutes sont ignorées car la regex attend le suffixe "min". Résultat : `1h 30` est interprété comme 60 min au lieu de 90 min.

### Solution

Modifier la regex de `trajetToMin()` pour capturer les minutes même sans le suffixe "min", en acceptant le format `Xh YY` en plus du format existant `Xh YYmin`.

### Scope

**In Scope:**
- Fix de la regex dans `trajetToMin()` pour gérer le format `Xh YY` sans suffixe "min"
- Le format existant `Xh YYmin` doit continuer à fonctionner
- Le format `YYmin` seul doit continuer à fonctionner

**Out of Scope:**
- Nouveaux formats (`:`, minutes brutes, etc.)
- Modification du placeholder du champ filtre
- Modification du backend `routing.py`

## Context for Development

### Codebase Patterns

- Le parsing de durées est fait côté client en JavaScript dans la fonction `trajetToMin()`
- Les données backend sont au format `"Xh YYmin"` (ex: `"1h 30min"`) ou `"YYmin"` (ex: `"45min"`)
- L'input utilisateur du filtre accepte du texte libre avec placeholder `ex: 1h 30`
- La même fonction `trajetToMin()` est utilisée pour parser à la fois les valeurs du filtre ET les données stockées

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `templates/index.html:484-490` | Fonction `trajetToMin()` — cible du fix |
| `templates/index.html:331` | Input HTML du filtre trajet max |
| `templates/index.html:524-541` | Logique de filtrage qui appelle `trajetToMin()` |
| `routing.py:18` | Format de sortie backend (référence, pas à modifier) |

### Technical Decisions

- La regex doit accepter les minutes avec OU sans le suffixe "min" pour rester rétro-compatible
- Pas de changement de l'interface utilisateur (placeholder inchangé)

## Implementation Plan

### Tasks

- [x] Task 1: Fix regex minutes dans `trajetToMin()`
  - File: `templates/index.html:488`
  - Action: Remplacer la regex `/(\d+)min/` par `/(\d+)\s*min|(\d+)(?!\S)/` ou équivalent qui capture les chiffres après "h" même sans suffixe "min". Approche recommandée — modifier la ligne 488 pour utiliser une regex qui rend le suffixe "min" optionnel :
    ```javascript
    const mn = t.match(/(\d+)\s*min/); if (mn) m += parseInt(mn[1]);
    else if (h) { const rest = t.match(/h\s*(\d+)/); if (rest) m += parseInt(rest[1]); }
    ```
  - Notes: La regex doit continuer à matcher `"30min"`, `"1h 30min"` ET maintenant `"1h 30"`, `"2h 15"`. L'ordre de priorité : essayer d'abord avec "min", sinon capturer les chiffres après "h".

### Acceptance Criteria

- [ ] AC 1: Given input `"1h 30"`, when parsed by `trajetToMin()`, then returns `90`
- [ ] AC 2: Given input `"2h 15"`, when parsed by `trajetToMin()`, then returns `135`
- [ ] AC 3: Given input `"1h 30min"` (format backend), when parsed by `trajetToMin()`, then returns `90`
- [ ] AC 4: Given input `"45min"` (minutes seules), when parsed by `trajetToMin()`, then returns `45`
- [ ] AC 5: Given input `"2h"` (heures seules), when parsed by `trajetToMin()`, then returns `120`
- [ ] AC 6: Given input `"N/A"`, when parsed by `trajetToMin()`, then returns `Infinity`
- [ ] AC 7: Given input `""` ou `null`, when parsed by `trajetToMin()`, then returns `Infinity`
- [ ] AC 8: Given filter set to `"1h 30"` and annonce with trajet `"1h 25min"`, when filtering, then annonce is shown (25+60=85 < 90)
- [ ] AC 9: Given filter set to `"1h 30"` and annonce with trajet `"1h 35min"`, when filtering, then annonce is hidden (35+60=95 > 90)

## Additional Context

### Dependencies

Aucune dépendance externe.

### Testing Strategy

- **Tests manuels :** Saisir les valeurs suivantes dans le filtre trajet max et vérifier le filtrage :
  - `1h 30` → doit filtrer à 90 min
  - `2h 15` → doit filtrer à 135 min
  - `45min` → doit filtrer à 45 min
  - `2h` → doit filtrer à 120 min
- **Vérification du tri :** Trier par colonne trajet et vérifier que l'ordre est correct
- **Pas de tests unitaires existants** pour cette fonction — pas d'ajout requis (out of scope)

### Notes

- Le bug n'affecte que le parsing de l'input utilisateur du filtre (les données backend ont toujours le suffixe "min")
- Le tri par colonne trajet utilise la même fonction et bénéficiera du fix
- Le fix est rétro-compatible : tous les formats existants continuent de fonctionner

## Review Notes
- Adversarial review completed
- Findings: 8 total, 3 fixed, 5 skipped (pre-existing/out-of-scope)
- Resolution approach: auto-fix
- F1 (Critical) fixed: bare number input "30" now parsed as 30 minutes
- F5 (Medium) fixed: added radix 10 to new parseInt calls
- F8 (Low) fixed: improved readability with multi-line formatting
- F2, F3, F6 skipped: pre-existing issues hors scope de cette spec
- F7 skipped: undecided (NaN guard)
