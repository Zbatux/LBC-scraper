# Architecture du projet LBC Scraper

## Vue d'ensemble

Pipeline en 4 étapes pour extraire, enrichir et analyser des annonces Leboncoin,
plus une interface web locale pour les éditer :

```
Leboncoin  ──(Playwright)──▶  SQLite  ──(Playwright)──▶  Ollama  ──▶  CSV
 (scraping)                  (stockage)   (descriptions)   (analyse IA)  (export)
                                ▲
                             Flask ──▶ Interface web
                              (--web)
```

Chaque étape est indépendante et se déclenche via un argument CLI dans `main.py`.

---

## Structure des modules

| Fichier                | Rôle                                              | Symboles clés                                                  |
|------------------------|---------------------------------------------------|----------------------------------------------------------------|
| `config.py`            | Constantes globales                               | `TOULOUSE_LAT`, `TOULOUSE_LNG`, `SEARCH_URL`, `MAX_PAGES`     |
| `parsers.py`           | Extraction des champs depuis les objets JSON LBC  | `parse_price`, `parse_area`, `get_coords`, `get_attr`, `build_url` |
| `routing.py`           | Calcul du temps de trajet vers Toulouse via OSRM  | `drive_time`, `_sess`                                          |
| `browser.py`           | Pilotage Playwright (scraping, anti-bot)          | `get_all_ads`, `scrape_page`, `accept_cookies`, `human_scroll` |
| `database.py`          | Persistance SQLite + calcul des trajets           | `save_to_database`, `process`, `generate_unique_key`           |
| `descriptions.py`      | Visite des pages annonces pour récupérer le texte | `fetch_all_descriptions`, `fetch_description`                  |
| `analyzer.py`          | Analyse IA locale des descriptions (Ollama)       | `analyze_all`, `analyze_description`, `OLLAMA_MODEL`           |
| `exporter.py`          | Export CSV depuis la base SQLite                  | `export_to_csv`                                                |
| `web.py`               | Serveur Flask — API REST + service des templates  | `app`, `get_annonces`, `delete_annonces`, `bulk_update`, `update_annonce`, `EDITABLE_FIELDS` |
| `templates/index.html` | Interface HTML/JS d'édition des annonces          | tableau interactif, filtres, actions bulk, édition inline      |
| `main.py`              | Point d'entrée CLI (argparse)                     | `main`                                                         |

---

## Diagramme des dépendances

```
config.py
   ├──▶ routing.py
   └──▶ browser.py

parsers.py
   └──▶ database.py

routing.py
   └──▶ database.py

browser.py
   └──▶ descriptions.py

database.py   ──┐
descriptions.py ├──▶ main.py
analyzer.py   ──┤
exporter.py   ──┘
config.py     ──┘
```

Aucune dépendance circulaire.

---

## Flux de données détaillé

### Étape 1 — `--scrape`
1. Playwright ouvre Chromium (mode visible, `slow_mo=120ms`)
2. Navigation sur `SEARCH_URL` page par page (max `MAX_PAGES`)
3. Extraction depuis `__NEXT_DATA__` (JSON embarqué Next.js) avec fallback DOM
4. `parsers.py` extrait : titre, prix, superficie, coordonnées GPS
5. `routing.py` calcule le temps de trajet Toulouse via OSRM (API publique)
6. `database.py` insère les nouvelles annonces dans `lbc_data.db` (dédoublonnage par `unique_key`)

### Étape 2 — `--get-description`
1. SQLite : sélection des annonces sans description
2. Playwright visite chaque page d'annonce
3. Clic automatique sur "Voir la suite" si présent
4. Mise à jour de la colonne `description` en base

### Étape 3 — `--analyze`
1. SQLite : sélection des annonces avec description et `analyse_faite = 0`
2. Chaque description est envoyée à Ollama (`gemma3:12b`, température 0)
3. Le LLM retourne un JSON structuré (viabilisé, emprise au sol, constructibilité partielle)
4. Mise à jour des colonnes IA en base (`viabilise`, `emprise_sol`, `partiellement_constructible`, `partiellement_agricole`)

### Étape 4 — `--export-csv`
1. Lecture de toutes les colonnes depuis SQLite
2. Écriture CSV (séparateur `;`, encoding UTF-8) avec formatage FR (virgule décimale, Oui/Non)
3. Colonnes incluses : titre, prix, superficie, prix_m2, trajet, lien, viabilisé, emprise au sol, partiellement constructible, partiellement agricole, **nogo**, **note**

### Étape 5 — `--web`
1. `main.py` importe et démarre le serveur Flask (`web.py`) sur `127.0.0.1:5000`
2. Le navigateur par défaut est ouvert automatiquement via `webbrowser.open`
3. Le serveur expose 5 endpoints REST :

   | Méthode   | Route                    | Corps / Paramètres                          | Action                              |
   |-----------|--------------------------|---------------------------------------------|-------------------------------------|
   | `GET`     | `/`                      | —                                           | Sert `templates/index.html`         |
   | `GET`     | `/api/annonces`          | —                                           | Retourne toutes les annonces en JSON |
   | `DELETE`  | `/api/annonces`          | `{ ids: [int, …] }`                         | Suppression bulk                    |
   | `PATCH`   | `/api/annonces/bulk`     | `{ ids, field, value: 0 1 }`                | Toggle booléen en bulk              |
   | `PATCH`   | `/api/annonces/<id>`     | `{ note?: int, nogo?: 0 1, … }`             | Mise à jour partielle d'une ligne   |

4. **Sécurité** : la constante `EDITABLE_FIELDS` définit la whitelist des colonnes éditables
   (`note`, `nogo`, `viabilise`, `partiellement_constructible`, `partiellement_agricole`).
   Tout autre nom de colonne transmis par le client est rejeté avec `400` avant d'être
   interpôlé dans une requête SQL, prévenant toute injection via nom de colonne.

5. L'interface HTML (JS vanilla, sans build step) :
   - Charge la liste initiale via `GET /api/annonces`
   - Maintient un tableau local `allData` pour le filtrage/tri côté client (sans rechargement)
   - Envoie un `PATCH /api/annonces/<id>` à chaque édition de `note` ou toggle de `nogo`
   - Envoie un `PATCH /api/annonces/bulk` pour les actions sélection multiple
   - Envoie un `DELETE /api/annonces` avec la liste des ids sélectionnés

---

## Schéma de la base de données (`lbc_data.db`)

Table : `annonces`

| Colonne                        | Type    | Description                                         |
|-------------------------------|---------|-----------------------------------------------------|
| `id`                          | INTEGER | Clé primaire auto-incrémentée                       |
| `titre`                       | TEXT    | Titre de l'annonce                                  |
| `prix`                        | REAL    | Prix en €                                           |
| `superficie`                  | REAL    | Surface en m²                                       |
| `prix_m2`                     | REAL    | Prix au m² calculé                                  |
| `trajet`                      | TEXT    | Temps de trajet vers Toulouse (ex: `1h 23min`)      |
| `lien`                        | TEXT    | URL de l'annonce                                    |
| `unique_key`                  | TEXT    | MD5(titre\|superficie) — contrainte UNIQUE          |
| `description`                 | TEXT    | Texte complet de l'annonce (rempli par `--get-description`) |
| `viabilise`                   | INTEGER | 0/1/NULL — issu de l'analyse IA                     |
| `emprise_sol`                 | REAL    | % d'emprise au sol (100.0 si non mentionné)         |
| `partiellement_constructible` | INTEGER | 0/1/NULL — issu de l'analyse IA                     |
| `partiellement_agricole`      | INTEGER | 0/1/NULL — issu de l'analyse IA                     |
| `analyse_faite`               | INTEGER | 0/1 — flag de traitement IA                         |
| `nogo`                        | INTEGER | 0/1 — annonce à ignorer (défini manuellement)       |
| `note`                        | INTEGER | 1–10 — note manuelle de l'annonce                   |

---

## Choix techniques

| Technologie | Raison du choix |
|---|---|
| **Playwright** (vs `requests`) | Leboncoin utilise DataDome (protection anti-bot). Playwright simule un vrai navigateur avec défilement aléatoire, pauses humaines et masquage de `webdriver`. |
| **OSRM** (vs Google Maps API) | API publique gratuite, sans clé, pour le calcul d'itinéraires routiers. |
| **Ollama** (vs API cloud) | Inférence 100% locale — pas de coût, pas de fuite de données, déterministe (`temperature=0`). |
| **SQLite** (vs fichiers CSV) | Dédoublonnage natif (`UNIQUE`), migrations incrémentales, requêtes SQL pour le filtrage. |
| **`__NEXT_DATA__`** | Leboncoin est une app Next.js : les données structurées sont injectées dans le DOM en JSON, plus fiable que le scraping HTML. |
| **Flask** (vs FastAPI, Streamlit) | Minimal et sans dépendances lourdes pour un outil local. Sert l'UI en une seule route et expose 5 endpoints REST simples. Pas de build step, pas de rechargement de page : le JS gère le filtrage/tri côté client. |
