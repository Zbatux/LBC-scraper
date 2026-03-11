---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
inputDocuments: ['product-brief-LBC-Scraper-2026-03-10.md', 'ARCHITECTURE.md', 'README.md', 'project-context.md']
workflowType: 'prd'
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 2
  projectContext: 1
classification:
  projectType: 'cli_tool + web_app (hybrid)'
  domain: 'general'
  complexity: 'low'
  projectContext: 'brownfield'
---

# Product Requirements Document - LBC-Scraper

**Author:** Bogoss
**Date:** 2026-03-10

## Executive Summary

LBC-Scraper is a personal CLI + web tool that scrapes Leboncoin for buildable land listings near Toulouse, enriches them with travel times and AI analysis, and provides a local web interface for review.

**This PRD covers the history tracking enhancement**: replacing the current MD5-based deduplication with GPS + area fuzzy matching, adding a full-column change history table, and surfacing status indicators (new / price changed / reposted) and a history modal in the web UI. The result transforms the tool from a point-in-time snapshot into a market intelligence system where price drops, re-listings, and evolving descriptions become actionable negotiation signals.

**Traceability chain**: Vision → Success Criteria → User Journeys (×3) → 23 Functional Requirements → 9 Non-Functional Requirements

---

## Success Criteria

### User Success

| Outcome | Criterion | Target |
|---------|-----------|--------|
| New listing visibility | After each scrape, new listings are visually flagged in the web UI | 100% of first-seen ads marked "new" |
| Price change detection | When price differs from the previous snapshot, the change is logged and the flag is visible in the main table | 100% detection rate |
| Republish detection | When GPS coordinates match (within ~50m) and area matches (within 10%), the system links the new post to the existing record | Correct match on all same-land reposts |
| Publication date coverage | Original Leboncoin publication date is scraped from `__NEXT_DATA__` and stored | Available on 100% of scraped ads |
| History completeness | The history modal shows every column change across every scraper run, with timestamps | No gaps in the change log |
| Time-to-action | User identifies actionable listings (new, price drop, repost) within 1 minute of opening the web UI | Status indicators visible in main table without clicking into individual ads |

**"Aha!" moment**: Opening the web UI after a scrape and seeing immediate status indicators — then clicking a price-drop listing and seeing it went from 45k€ → 38k€ → 32k€ over three months.

### Business Success

This is a solo personal tool — "business success" equals user value:

- **Negotiation leverage**: Price history turns guesswork into data-backed negotiation anchors
- **No missed opportunities**: New-listing flags ensure every relevant post is seen immediately
- **Market intelligence**: Repost and stale-listing detection reveals motivated sellers without manual tracking

### Technical Success

- Zero false merges — no two different lands are incorrectly linked by the fuzzy matcher
- All existing CLI pipeline steps (`--scrape`, `--get-description`, `--analyze`, `--export-csv`, `--web`) continue to function unchanged after the refactor
- History snapshots are atomic — no partial writes if a scrape run is interrupted
- Schema supports a clean-slate re-run (no complex legacy migration needed)

### Measurable Outcomes

| KPI | Measurement | Target |
|-----|-------------|--------|
| New ads flagged per scrape | Count of listings with `status = new` in results | 100% of first-seen ads |
| Price drops detected | Count of history entries where `price` decreased | 100% detection rate |
| Republish detection rate | Merged records confirmed as same land | ≥ 90% correct match rate |
| False merge rate | Merged records that are actually different lands | 0% |
| Publication date coverage | Ads with non-null `date_publication` | 100% |
| Pipeline compatibility | Existing CLI flags pass smoke test after changes | 5/5 flags working |

---

## Product Scope

**MVP Approach:** Problem-solving MVP — the minimum needed to transform the scraper from a point-in-time snapshot into a persistent market intelligence tracker. Success: after the first post-implementation scrape, the user can see exactly what changed vs. last time. Solo developer (Bogoss), local machine only, no deployment needed.

### MVP — Phase 1

| # | Feature | Purpose |
|---|---------|---------|
| 1 | **Fuzzy matching (GPS + area)** | Identity layer — replaces MD5 dedup; foundation for everything below |
| 2 | **`date_publication` scraping** | Extract from `__NEXT_DATA__`; store on `annonces` |
| 3 | **`first_seen` tracking** | Timestamp on first insert — enables "new" flag and days-on-market |
| 4 | **`annonces_history` table** | Full-column snapshot per detected change, with timestamp and annonce ID |
| 5 | **Merge-on-match** | On fuzzy match: snapshot current state → update main record with latest data |
| 6 | **`status` field** | Per-listing value: `new` / `price_changed` / `reposted` / `unchanged` |
| 7 | **Status indicators in web UI** | Visual badges in main table — the user-facing payoff |
| 8 | **History modal** | Per-listing chronological change log — the "aha!" moment |

All existing CLI flags (`--scrape`, `--get-description`, `--analyze`, `--export-csv`, `--web`) remain unchanged.

### Phase 2 — Growth

- Summary stats banner: "3 new, 2 price drops, 1 repost" above the main table
- Filter / sort the main table by status
- CSV export enriched with `first_seen`, `price_change_count`, `days_on_market`

### Phase 3 — Vision

- Price trend sparkline per listing in the history modal
- Price per m² comparison across nearby listings
- Automated scrape scheduling (cron-style)
- Multi-city support beyond Toulouse
- Price-drop notifications for flagged listings

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Fuzzy matcher produces false merges | Tight thresholds (50m GPS, 10% area); manual audit after first run; fall back to insert-as-new on missing GPS |
| Schema change breaks existing pipeline steps | Additive-only schema changes (new columns, new table); existing queries unaffected |
| History table slows down scrape run | Index `annonces_history` on `annonce_id`; O(n) match loop acceptable at <500 listings |
| Feature creep during implementation | MVP boundary fixed — no summary stats, filters, or CSV history until Phase 2 |

---

## User Journeys

### Journey 1: Bogoss — Weekly Market Check (Happy Path)

**Persona**: Bogoss is an individual buyer actively searching for buildable land near Toulouse (100km radius, 1k–50k€ budget). He treats land-hunting as a side project — not a full-time job — so he runs the scraper weekly and expects maximum signal with minimum effort per session.

**Opening Scene**: It's Sunday morning. Bogoss opens his laptop with coffee. Last week's web UI showed 47 listings, most of which he'd already assessed. He launches `python main.py --scrape` and waits.

**Rising Action**: The scraper runs. The fuzzy matcher fires — it finds 3 listings that GPS-match lands already in the database. One has a changed price (down 8k€), one has a new `list_id` (reposted after deletion), one is genuinely unchanged. Two brand-new listings are inserted with `status = new`. The scrape finishes; `annonces_history` now has 2 new rows.

**Climax**: Bogoss opens the web UI. He immediately sees the status column — two green "new" badges, one amber "price drop" badge, one blue "reposted" badge. He clicks the price-drop listing. The history modal opens: it went from 45k€ → 38k€ → 32k€ across three scrape sessions over 8 weeks. The seller is clearly motivated.

**Resolution**: Within 4 minutes of opening the web UI, Bogoss has identified his priority: the price-drop land. He notes the trend and decides to contact the seller today — armed with the knowledge that the price has fallen 29% in 2 months. This is the negotiation leverage he never had before.

**Capabilities revealed**: Fuzzy matcher, `annonces_history`, status flags, history modal, `first_seen` timestamp.

---

### Journey 2: Bogoss — Catching a Republished Listing (Edge Case)

**Opening Scene**: A seller listed a plot at 40k€ six weeks ago. Bogoss assessed it but passed. The seller deleted the listing and reposted it at 36k€ with a slightly different title.

**Rising Action**: The new `list_id` triggers a fresh insert candidate in the scraper. But the fuzzy matcher finds the existing record: GPS coordinates match within 30m, area matches within 5%. Instead of creating a duplicate, it snapshots the old record and updates the main row with the new `list_id` and new price.

**Climax**: In the web UI, the listing appears with a "reposted" badge. Bogoss recognizes it — but the key new information is in the history modal: original price 40k€, new price 36k€, reposted after 6 weeks on market. *This seller couldn't sell at 40k€ and is trying again at 36k€.* Classic motivated seller signal.

**Resolution**: Bogoss makes an offer at 30k€. Without the history, he'd have treated this as a fresh listing with no leverage.

**Capabilities revealed**: Fuzzy matcher (GPS + area), merge-on-match behavior, `reposted` status flag, history modal.

---

### Journey 3: Bogoss — Scraper Run After a Long Break (Data Integrity Edge Case)

**Opening Scene**: Bogoss hasn't run the scraper in 3 weeks. Some listings have expired from Leboncoin, others have changed significantly, and several are brand new.

**Rising Action**: The scrape returns 60 listings. The fuzzy matcher processes each against the existing DB. 15 exact GPS+area matches are found (same lands, re-scraped). Among those, 4 have changed prices. 8 are genuinely new (no match). 37 were already in the DB with no changes.

**Climax**: The web UI shows 8 "new" badges, 4 "price changed" badges. The rest are clean. No false merges — the matcher's proximity threshold prevents unrelated nearby plots from being conflated.

**Resolution**: A 3-week gap produced clean, actionable results. The history table has 4 new snapshots. The user can confidently scan a manageable set of flagged items rather than re-reviewing all 60.

**Capabilities revealed**: Batch fuzzy matching performance, no-change pass-through, false-merge prevention, status flag accuracy.

---

### Journey Requirements Summary

| Capability | Required by Journey |
|------------|---------------------|
| Fuzzy matcher (GPS ± 50m, area ± 10%) | 1, 2, 3 |
| `annonces_history` table with full snapshots | 1, 2, 3 |
| `status` flags: new / price changed / reposted | 1, 2, 3 |
| History modal (chronological change log) | 1, 2 |
| `first_seen` timestamp | 1, 3 |
| `date_publication` from `__NEXT_DATA__` | 1 |
| Merge-on-match (update main record, snapshot old) | 2, 3 |
| False-merge prevention (proximity threshold) | 2, 3 |
| All existing CLI flags unaffected | 1, 2, 3 |

---

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Physical-identity-based deduplication**
Most scrapers treat `list_id` or content hash as the canonical identity of a listing. LBC-Scraper replaces this with the real-world identity of the underlying asset — GPS coordinates + area — making the system resilient to re-posts, title edits, and `list_id` cycling. This approach is standard in real estate MLS data systems but uncommon in personal scraper tooling.

**2. Scraper-as-market-intelligence-system**
Rather than treating each scrape as an independent snapshot, the merge-on-change design builds a continuous temporal record. The scraper accumulates *market history*, not just current state — turning a data collection tool into an intelligence platform for a single user.

**3. Zero-dependency change detection**
Change detection requires no external services, no LLM calls, and no third-party APIs. All signals (price change, repost, new listing) are derived purely from data already collected during the normal scrape: GPS, area, and price. This is an intentional design constraint that keeps the tool robust and free.

### Validation Approach

- Manual spot-check: after first run with fuzzy matcher, verify 3–5 known re-listed plots are correctly merged (not duplicated)
- False-merge audit: review any merged records to confirm they represent the same physical land
- Pipeline smoke test: run all existing CLI flags after changes and confirm identical output for unchanged ads

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| False merge (two adjacent plots linked) | Keep GPS threshold tight (~50m); area threshold at 10% — unlikely two adjacent plots have the same area |
| GPS data missing or imprecise | Fall back to no-match (insert as new) — never force a merge on incomplete data |
| History table grows large over time | SQLite handles thousands of rows trivially; no action needed at personal-tool scale |

---

## CLI Tool + Web App — Specific Requirements

### Project-Type Overview

LBC-Scraper is a hybrid: a **CLI-driven pipeline** for scraping and enrichment, paired with a **local web app** for browsing results. The CLI is the engine; the web app is the display layer. Both run locally on the user’s machine against a local SQLite database. No hosting, no multi-user concerns, no SEO.

### CLI Architecture Considerations

**Command structure** — existing, must be preserved:

| Flag | Purpose |
|------|---------|
| `--scrape` | Fetch listings from Leboncoin, run fuzzy matching, update DB |
| `--get-description` | Enrich listings with AI-generated description analysis |
| `--analyze` | Run AI scoring on listings |
| `--export-csv` | Export current `annonces` table to CSV |
| `--web` | Launch local Flask web server |

New history tracking integrates **transparently into `--scrape`** — no new CLI flags required for MVP.

**Output format**: Console progress logging + SQLite DB writes. No structured output format needed.

**Config method**: `config.py` — hardcoded constants (search area, thresholds, API keys). No new config flags for MVP.

### Web App Architecture Considerations

**Architecture**: Single-page Flask app served locally. All listing data loaded on page load from SQLite. No routing, no server-side pagination needed at personal-tool scale.

**Browser support**: Latest Chrome or Firefox on the user’s local machine only.

**Real-time updates**: Not required. The web UI reflects DB state at page load time. User refreshes manually after a scrape.

**History modal**: New `/history/<id>` endpoint or inline JavaScript fetch — returns `annonces_history` rows for a given annonce ID as JSON, rendered client-side.

---

## Functional Requirements

### Ad Identity & Matching

- **FR1**: The system can identify when a scraped listing corresponds to a previously seen physical land parcel using GPS proximity (within ~50m) and area similarity (within 10%)
- **FR2**: The system can handle listings with no GPS data by treating them as new records (no forced match)
- **FR3**: The system can detect when the same physical land is re-listed under a new `list_id` and link it to the existing record

### History Tracking

- **FR4**: The system can record a full-column snapshot of a listing’s previous state to the history table whenever a change is detected during a scrape
- **FR5**: The system can timestamp each history snapshot with the scrape run date/time
- **FR6**: The system can preserve multiple history snapshots per listing, building a complete chronological change log over time
- **FR7**: The system can capture the original Leboncoin publication date (`date_publication`) for each listing from `__NEXT_DATA__` during scraping
- **FR8**: The system can record the date a listing was first inserted into the database (`first_seen`)

### Listing State Management

- **FR9**: The system can assign a status to each listing after each scrape: `new`, `price_changed`, `reposted`, or `unchanged`
- **FR10**: The system can update the main listing record with the latest scraped data when a fuzzy match is found
- **FR11**: The system can reset the `status` field to `unchanged` for listings that matched but had no data differences

### Scrape Pipeline

- **FR12**: The scraper can run all existing pipeline steps (`--scrape`, `--get-description`, `--analyze`, `--export-csv`, `--web`) without modification to their interfaces or outputs
- **FR13**: The `--scrape` step can execute fuzzy matching, history snapshotting, and status assignment transparently as part of its existing run
- **FR14**: The system can initialize the `annonces_history` table on first run alongside the existing `annonces` table

### Web UI — Main Table

- **FR15**: The user can see a status indicator (new / price changed / reposted) for each listing in the main table
- **FR16**: The user can distinguish at a glance which listings appeared since the last scrape (status = new)
- **FR17**: The user can see `date_publication` and `first_seen` dates in the listing view

### Web UI — History Modal

- **FR18**: The user can open a history modal for any listing that has at least one history snapshot
- **FR19**: The user can view the full chronological list of all recorded snapshots for a listing, ordered oldest to newest
- **FR20**: The user can see which specific fields changed between each snapshot (price, description, list_id, etc.)
- **FR21**: The user can see the timestamp of each history snapshot

### Data Integrity

- **FR22**: The system can guarantee that a scrape interruption does not produce partial or corrupt history snapshots (atomic writes)
- **FR23**: The system can support a full database drop-and-recreate workflow without losing schema correctness on the next run

---

## Non-Functional Requirements

### Performance

- **NFR1**: The `--scrape` step must complete within the same order of magnitude time as before the fuzzy matching changes — no visible regression for a typical run of <500 listings
- **NFR2**: The web UI main table must load within 2 seconds on localhost for up to 500 listings
- **NFR3**: The history modal must open and display snapshots within 500ms of user click
- **NFR4**: The fuzzy matching loop must not cause an O(n²) query pattern — matching must use indexed DB lookups, not full table scans per listing

### Reliability

- **NFR5**: History snapshots must be written atomically — a crash or keyboard interrupt during a scrape run must not leave partial or corrupt rows in `annonces_history`
- **NFR6**: The schema initialization must be idempotent — running `--scrape` on an existing database must not fail if `annonces_history` or the new columns already exist
- **NFR7**: A full database drop and re-creation must result in a valid, consistent schema on the very next `--scrape` run with no manual intervention

### Integration

- **NFR8**: The `date_publication` extraction must gracefully handle Leboncoin listings where `__NEXT_DATA__` does not include a publication date — defaulting to `NULL` without crashing the scrape
- **NFR9**: The fuzzy matcher must gracefully handle listings where GPS coordinates are absent or malformed — treating them as new records (no match attempted)
