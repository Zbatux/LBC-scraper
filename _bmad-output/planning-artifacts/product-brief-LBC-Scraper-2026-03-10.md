---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: ['ARCHITECTURE.md', 'README.md', '_bmad-output/project-context.md']
date: '2026-03-10'
author: 'Bogoss'
project_name: 'LBC-Scraper'
---

# Product Brief: LBC-Scraper

## Executive Summary

LBC-Scraper is an existing tool that scrapes Leboncoin for buildable land listings near Toulouse, enriches them with travel times and AI analysis, and provides a web interface for manual review. The proposed enhancement adds **ad history tracking** — the ability to detect republished or updated ads through GPS + area fuzzy matching, merge them into a single record, and maintain a full chronological history of all column changes. This transforms the tool from a point-in-time snapshot into a market intelligence system where price drops, re-listings, and evolving descriptions become actionable signals.

---

## Core Vision

### Problem Statement

When sellers on Leboncoin republish or update their land listings, the current scraper either silently drops them as duplicates (same title/area) or creates disconnected records (if the title changed). Price evolution, re-listing frequency, and description changes — critical signals for identifying motivated sellers and negotiation opportunities — are permanently lost.

### Problem Impact

Without historical tracking, users must manually remember previous prices, guess whether a listing is new or republished, and lose all the intelligence that comes from observing a listing's lifecycle. The most actionable market data — "this land dropped from 45k€ to 35k€ over 3 months" — is invisible.

### Why Existing Solutions Fall Short

The current deduplication uses `MD5(title|area)`, which is both too strict (misses re-posts with slight title changes) and too brittle (different lands with similar titles could theoretically collide). More importantly, the system has no concept of time — there's no publication date, no "first seen" date, and no mechanism to track changes between scraper runs.

### Proposed Solution

1. **Fuzzy matching via GPS + area**: Replace the MD5-based deduplication with a proximity match — same GPS coordinates (within ~50m) and similar area (within 10%) identifies the same physical land regardless of title or `list_id` changes.
2. **Merge strategy**: When a match is found, the existing record is updated with the latest data, and the previous state is preserved as a snapshot in a new `annonces_history` table (all columns).
3. **Chronological history**: Each scraper run that detects a change logs a full row snapshot with a timestamp, building a complete audit trail per listing.
4. **History modal in web UI**: A per-listing modal displays the full change log — price evolution, description changes, re-listing dates — as a simple chronological list.

### Key Differentiators

- **Zero external dependencies**: Matching uses already-available GPS and area data — no new API calls, no AI needed
- **Full-column snapshots**: History captures everything (price, description, AI fields, user annotations), not just price
- **Merge-based design**: Clean single-record-per-land model avoids duplicate clutter in the main view
- **Fresh-start friendly**: Designed for a clean DB re-run, no complex migration of legacy data

---

## Target Users

### Primary Users

**Bogoss — Solo Land Buyer Monitoring the Toulouse Market**

- **Context**: Individual buyer actively searching for buildable land within 100km of Toulouse, price range 1k–50k€. Uses LBC-Scraper as a personal market intelligence tool, running scrapes regularly to track the evolving landscape of available plots.
- **Motivation**: Find the best deal on buildable land by understanding not just what's available *now*, but how the market is moving — which listings are stale, which sellers are dropping prices, and which lands keep getting reposted (signaling difficulty selling).
- **Current workflow**: Runs the scraper, opens the web UI, scans listings — but today every session feels like starting fresh. No way to tell what's new since last run, whether a listing was seen before at a different price, or if a seller is getting desperate.
- **Desired workflow with history**:
  1. Run scraper → immediately see which listings are **new** (never seen before), which are **updated** (price or details changed), and which are **reposted** (deleted and re-listed)
  2. In the main table, visual indicators flag price drops, re-posts, and new listings at a glance
  3. Click a listing → history modal shows full timeline: first seen date, every price change, description changes
  4. Compare similar lands by area/location to evaluate if a price is competitive
  5. Spot a price drop → know it's time to negotiate

- **"Aha!" moment**: Opening the web UI after a scrape and instantly seeing "3 new listings, 2 price drops, 1 repost" — then clicking a price-drop listing and seeing it went from 45k€ → 38k€ → 32k€ over 2 months.

### Secondary Users

N/A — This is a personal tool with a single user.

### User Journey

1. **Scrape run**: User launches `python main.py --scrape`. The fuzzy matcher detects returning ads, merges updates, snapshots changes to history, and flags new/updated/reposted listings.
2. **Web UI scan**: User opens the web interface. The main table shows status indicators (new / price changed / reposted) so they can prioritize attention without clicking into each ad.
3. **Deep dive**: User spots a listing with a "price dropped" indicator → clicks to open the history modal → sees the full chronological log of all changes.
4. **Decision**: Armed with history data (time on market, price trajectory, re-listing count), the user decides whether to pursue the land and at what negotiation price.
5. **Ongoing monitoring**: Over days/weeks of repeated scrapes, the history builds up, and the tool becomes increasingly valuable as a market trend tracker.

---

## Success Metrics

### User Success Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **New ad visibility** | After a scrape, user can instantly distinguish new listings from previously seen ones | 100% of new ads are flagged as "new" in the web UI |
| **Price change detection** | When an ad's price changes between scraper runs, the change is captured and visible | 100% of price changes detected and logged in history |
| **Republish detection** | When a seller deletes and re-posts the same land, the fuzzy matcher links them | Detected when GPS coordinates match (within ~50m) and area matches (within 10%) |
| **Publication date captured** | The original publication date from Leboncoin is scraped and stored | Available for every ad from `__NEXT_DATA__` |
| **History modal completeness** | Clicking an ad shows its full chronological change log | All column changes across all scraper runs displayed |
| **Time-to-action** | User can identify the most interesting ads (new, price dropped, stale) within the first minute of opening the web UI | Status indicators visible in main table without clicking into individual ads |

### Business Objectives

N/A — This is a personal tool. Success is measured purely in user value: faster identification of deals, better negotiation leverage from price history, and no missed opportunities from new listings.

### Key Performance Indicators

| KPI | Measurement | Why It Matters |
|-----|-------------|----------------|
| **New ads flagged per scrape** | Count of listings marked "new" after each run | Confirms the scraper + matcher are working — user sees what appeared since last run |
| **History entries per ad** | Average number of snapshots per listing over time | Shows the history is accumulating — more data = more negotiation leverage |
| **Price drops detected** | Count of ads where current price < first seen price | The primary actionable signal — directly tied to negotiation opportunities |
| **Stale listing age** | Days since first publication date for active listings | Listings on the market for weeks/months signal motivated sellers |
| **Fuzzy match accuracy** | Merged ads are genuinely the same land (verified by user) | The matcher must not merge unrelated ads — false merges corrupt data |

---

## MVP Scope

### Core Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Fuzzy matching (GPS + area)** | Replace `MD5(title\|area)` deduplication with proximity-based matching: same GPS coordinates (within ~50m) and similar area (within 10%). This is the foundation that enables all history tracking. |
| 2 | **Publication date scraping** | Extract the original publication date from Leboncoin's `__NEXT_DATA__` JSON during scraping. Store as `date_publication` on the `annonces` table. |
| 3 | **First-seen tracking** | Add `first_seen` column to `annonces` — set to the scraper run timestamp when a listing is first inserted. |
| 4 | **`annonces_history` table** | New table that stores a full-column snapshot of an ad's previous state every time a change is detected during a scrape. Each row includes a timestamp and the annonce ID it relates to. |
| 5 | **Merge-on-match behavior** | When the fuzzy matcher finds an existing ad: snapshot the current state to `annonces_history`, then update the main `annonces` record with the new data. |
| 6 | **Status flags in main table** | Each ad in the web UI main table shows a visual indicator: **new** (first seen in latest scrape), **price changed** (price differs from previous snapshot), **reposted** (new `list_id` matched to existing land). |
| 7 | **History modal in web UI** | Clicking a listing opens a modal showing the full chronological log of all recorded changes — every column, every snapshot, with timestamps. |

### Out of Scope for MVP

These ideas are deferred to post-MVP. They build on the MVP foundation and can be implemented incrementally.

| # | Feature | Rationale for Deferral |
|---|---------|----------------------|
| 1 | **Price comparison across similar lands** | Requires defining "similar" beyond exact match — area range, location radius, price bracket. Useful but adds complexity to the UI. |
| 2 | **Summary dashboard** | "3 new, 2 price drops, 1 repost" stats banner at top of web UI. Nice-to-have but indicators on individual rows deliver the core value. |
| 3 | **Filter/sort by history status** | Filter the main table by "only new", "only price drops", "only reposted". Powerful but requires the MVP indicators to be working first. |
| 4 | **CSV export of history data** | Export the `annonces_history` table or include history columns in the existing CSV export. Current CSV export works for the main snapshot. |
| 5 | **Price trend visualization** | Mini sparkline or chart showing price trajectory per ad. Requires a charting library — overkill for a simple log. |

### MVP Success Criteria

- Fuzzy matcher correctly identifies the same physical land across re-posts (verified manually on a few known cases)
- Every detected change produces a snapshot in `annonces_history`
- Publication date is captured for all scraped ads
- Web UI main table clearly shows new / price changed / reposted indicators
- History modal displays the complete chronological log for any ad
- No false merges (two different lands incorrectly linked)
- Existing pipeline steps (`--get-description`, `--analyze`, `--export-csv`, `--web`) continue to work unchanged

### Future Vision

After the MVP is stable:
1. **Filtering & sorting** by status flags — quickly surface actionable listings
2. **Summary stats** — at-a-glance count of new/changed/reposted after each scrape
3. **Similar land comparison** — compare price per m² across listings in the same area
4. **History in CSV export** — include first-seen date, price change count, and days-on-market in exports
5. **Price trend charts** — visual price trajectory per listing in the history modal
