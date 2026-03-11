# LBC Scraper Project Architecture

## Overview

4-step pipeline to extract, enrich, and analyze Leboncoin listings,
plus a local web interface for editing:

```
Leboncoin  ──(Playwright)──▶  SQLite  ──(Playwright)──▶  Ollama  ──▶  CSV
 (scraping)                  (storage)   (descriptions)   (AI analysis)  (export)
                                ▲
                             Flask ──▶ Web interface
                              (--web)
```

Each step is independent and triggered via a CLI argument in `main.py`.

---

## Module Structure

| File                  | Role                                              | Key Symbols                                                  |
|-----------------------|---------------------------------------------------|-------------------------------------------------------------|
| `config.py`           | Global constants                                 | `TOULOUSE_LAT`, `TOULOUSE_LNG`, `SEARCH_URL`, `MAX_PAGES`   |
| `parsers.py`          | Field extraction from LBC JSON objects           | `parse_price`, `parse_area`, `get_coords`, `get_attr`, `build_url` |
| `routing.py`          | Travel time calculation to Toulouse via OSRM     | `drive_time`, `_sess`                                       |
| `browser.py`          | Playwright automation (scraping, anti-bot)       | `get_all_ads`, `scrape_page`, `accept_cookies`, `human_scroll` |
| `database.py`         | SQLite persistence + travel time calculation     | `save_to_database`, `process`, `generate_unique_key`        |
| `descriptions.py`     | Visits listing pages to retrieve text            | `fetch_all_descriptions`, `fetch_description`               |
| `analyzer.py`         | Local AI analysis of descriptions (Ollama)       | `analyze_all`, `analyze_description`, `OLLAMA_MODEL`        |
| `exporter.py`         | CSV export from SQLite database                  | `export_to_csv`                                             |
| `web.py`              | Flask server — REST API + template service       | `app`, `get_annonces`, `delete_annonces`, `bulk_update`, `update_annonce`, `EDITABLE_FIELDS` |
| `templates/index.html`| HTML/JS interface for editing listings           | interactive table, filters, bulk actions, inline editing    |
| `main.py`             | CLI entry point (argparse)                       | `main`                                                      |

---

## Dependency Diagram

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

No circular dependencies.

---

## Detailed Data Flow

### Step 1 — `--scrape`
1. Playwright opens Chromium (visible mode, `slow_mo=120ms`)
2. Navigates `SEARCH_URL` page by page (max `MAX_PAGES`)
3. Extracts from `__NEXT_DATA__` (embedded Next.js JSON) with DOM fallback
4. `parsers.py` extracts: title, price, area, GPS coordinates
5. `routing.py` calculates travel time to Toulouse via OSRM (public API)
6. `database.py` inserts new listings into `lbc_data.db` (deduplication by `unique_key`)

### Step 2 — `--get-description`
1. SQLite: selects listings without descriptions
2. Playwright visits each listing page
3. Automatically clicks "See more" if present
4. Updates the `description` column in the database

### Step 3 — `--analyze`
1. SQLite: selects listings with descriptions and `analyse_faite = 0`
2. Each description is sent to Ollama (`gemma3:12b`, temperature 0)
3. The LLM returns a structured JSON (serviced, ground coverage, partial constructibility)
4. Updates AI columns in the database (`viabilise`, `emprise_sol`, `partiellement_constructible`, `partiellement_agricole`)

### Step 4 — `--export-csv`
1. Reads all columns from SQLite
2. Writes CSV (delimiter `;`, UTF-8 encoding) with FR formatting (decimal comma, Yes/No)
3. Included columns: title, price, area, price_m2, travel time, link, serviced, ground coverage, partially constructible, partially agricultural, **nogo**, **note**

### Step 5 — `--web`
1. `main.py` imports and starts the Flask server (`web.py`) on `127.0.0.1:5000`
2. The default browser is automatically opened via `webbrowser.open`
3. The server exposes 5 REST endpoints:

   | Method    | Route                    | Body / Parameters                          | Action                              |
   |-----------|--------------------------|--------------------------------------------|-------------------------------------|
   | `GET`     | `/`                      | —                                          | Serves `templates/index.html`       |
   | `GET`     | `/api/annonces`          | —                                          | Returns all listings in JSON        |
   | `DELETE`  | `/api/annonces`          | `{ ids: [int, …] }`                        | Bulk deletion                       |
   | `PATCH`   | `/api/annonces/bulk`     | `{ ids, field, value: 01 }`               | Bulk boolean toggle                 |
   | `PATCH`   | `/api/annonces/<id>`     | `{ note?: int, nogo?: 01, … }`            | Partial row update                  |

4. **Security**: the constant `EDITABLE_FIELDS` defines the whitelist of editable columns
   (`note`, `nogo`, `viabilise`, `partiellement_constructible`, `partiellement_agricole`).
   Any other column name sent by the client is rejected with `400` before being
   interpolated into an SQL query, preventing injection via column names.

5. The HTML interface (vanilla JS, no build step):
   - Loads the initial list via `GET /api/annonces`
   - Maintains a local `allData` table for client-side filtering/sorting (no reloads)
   - Sends a `PATCH /api/annonces/<id>` for each `note` edit or `nogo` toggle
   - Sends a `PATCH /api/annonces/bulk` for bulk actions on selected items
   - Sends a `DELETE /api/annonces` with the list of selected IDs

---

## Database Schema (`lbc_data.db`)

Table: `annonces`

| Column                        | Type    | Description                                         |
|-------------------------------|---------|---------------------------------------------------|
| `id`                          | INTEGER | Auto-incremented primary key                      |
| `titre`                       | TEXT    | Listing title                                      |
| `prix`                        | REAL    | Price in €                                         |
| `superficie`                  | REAL    | Area in m²                                         |
| `prix_m2`                     | REAL    | Calculated price per m²                           |
| `trajet`                      | TEXT    | Travel time to Toulouse (e.g., `1h 23min`)        |
| `lien`                        | TEXT    | Listing URL                                        |
| `unique_key`                  | TEXT    | MD5(title|area) — UNIQUE constraint               |
| `description`                 | TEXT    | Full listing text (filled by `--get-description`) |
| `viabilise`                   | INTEGER | 0/1/NULL — from AI analysis                       |
| `emprise_sol`                 | REAL    | Ground coverage % (100.0 if not mentioned)        |
| `partiellement_constructible` | INTEGER | 0/1/NULL — from AI analysis                       |
| `partiellement_agricole`      | INTEGER | 0/1/NULL — from AI analysis                       |
| `analyse_faite`               | INTEGER | 0/1 — AI processing flag                          |
| `nogo`                        | INTEGER | 0/1 — manually ignored listing                    |
| `note`                        | INTEGER | 1–10 — manual listing rating                      |

---

## Technical Choices

| Technology | Reason for Choice |
|------------|--------------------|
| **Playwright** (vs `requests`) | Leboncoin uses DataDome (anti-bot protection). Playwright simulates a real browser with random scrolling, human-like pauses, and `webdriver` masking. |
| **OSRM** (vs Google Maps API)  | Free public API, no key required, for route calculations. |
| **Ollama** (vs cloud API)      | 100% local inference — no cost, no data leaks, deterministic (`temperature=0`). |
| **SQLite** (vs CSV files)      | Native deduplication (`UNIQUE`), incremental migrations, SQL queries for filtering. |
| **`__NEXT_DATA__`**            | Leboncoin is a Next.js app: structured data is injected into the DOM as JSON, more reliable than HTML scraping. |
| **Flask** (vs FastAPI, Streamlit) | Minimal and lightweight for a local tool. Serves the UI in a single route and exposes 5 simple REST endpoints. No build step, no page reloads: JS handles client-side filtering/sorting.
