# LBC Scraper

Scraper for buildable land listings on Leboncoin (100 km radius around Toulouse).
Uses **Playwright** to bypass DataDome protection, calculates travel time
via **OSRM** (free, no API key required), stores everything in **SQLite**, enriches listings
with local AI analysis using **Ollama**, and provides a **web interface** (Flask) to edit,
filter, and annotate listings.

## Prerequisites

```bash
pip install -r requirements.txt
python -m playwright install chromium
ollama pull gemma3:12b   # only required for --analyze
```

Python 3.10+ required (`X | Y` annotations).

## Usage

```bash
# 1. Scrape listings and calculate travel times
python main.py --scrape

# 2. Retrieve full descriptions for each listing
python main.py --get-description

# 3. Analyze descriptions with the local LLM
python main.py --analyze

# 4. Export to CSV
python main.py --export-csv

# 5. Launch the web editing interface (http://localhost:5000)
python main.py --web
```

Steps 1 to 4 are independent and cumulative. The recommended order is 1 → 2 → 3 → 4.
Step 5 can be launched at any time to browse and edit the database.

## Arguments

| Argument            | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| `--scrape`          | Scrapes Leboncoin and saves new listings to `lbc_data.db`                  |
| `--get-description` | Visits each listing without a description and retrieves its full text       |
| `--analyze`         | Analyzes descriptions via Ollama and fills in AI fields (serviced…)        |
| `--export-csv`      | Exports all database data to a timestamped CSV file                        |
| `--web`             | Launches the web editing interface at `http://localhost:5000`              |

## Project Structure

```
main.py            CLI entry point
config.py          Constants (search URL, Toulouse coordinates…)
parsers.py         Field extraction from Leboncoin JSON objects
routing.py         Travel time calculation to Toulouse via OSRM
browser.py         Playwright automation (scraping, anti-bot)
database.py        SQLite persistence + deduplication
descriptions.py    Full description retrieval
analyzer.py        Local AI analysis (Ollama / gemma3:12b)
exporter.py        CSV export
web.py             Flask server — web editing interface
templates/
  index.html       HTML/JS listing editing interface
lbc_data.db        SQLite database generated at runtime
```

For a detailed description of the architecture, module dependencies, and the
database schema, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Disclaimer

Use of this scraper must comply with Leboncoin's terms of service.