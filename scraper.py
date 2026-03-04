"""
Scraper Leboncoin - Terrains à vendre
======================================
Utilise Playwright (Chrome headless) pour extraire les annonces.
Calcule le temps de trajet vers Toulouse via OSRM (gratuit, sans clé API).
Exporte un CSV : titre, prix, superficie, prix/m², trajet, lien.

PRÉREQUIS :
  pip install playwright requests
  python -m playwright install chromium

USAGE :
  python scraper.py
"""

import csv
import random
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

TOULOUSE_LAT = 43.6044622
TOULOUSE_LNG = 1.4442469

SEARCH_URL = (
    "https://www.leboncoin.fr/recherche"
    "?category=9"
    "&text=constructible%20-%22non%20constructible%22%20-%22pas%20constructible%22"
    "&lat=43.6404224&lng=1.4548992&radius=100000"
    "&price=1000-50000"
    "&real_estate_type=3"
    "&owner_type=all"
    "&sort=time&order=desc"
)

OUTPUT_CSV = f"terrains_leboncoin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
MAX_PAGES = 30  # ~35 annonces/page → 30 pages = 1050 annonces max

# ──────────────────────────────────────────────────────────────────────────────
# Extraction __NEXT_DATA__ (JSON embarqué Next.js)
# ──────────────────────────────────────────────────────────────────────────────

def extract_next_data(page: Page) -> dict | None:
    try:
        return page.evaluate(
            "() => JSON.parse(document.getElementById('__NEXT_DATA__').textContent)"
        )
    except Exception:
        return None


def find_ads_in_next_data(data: dict) -> tuple:
    """Retourne (ads, total) depuis __NEXT_DATA__."""
    try:
        pp = data["props"]["pageProps"]
        search_data = pp.get("searchData", {})
        ads = (
            search_data.get("ads")
            or pp.get("ads")
            or pp.get("initialData", {}).get("ads")
            or []
        )
        total = (
            search_data.get("total")
            or pp.get("total")
            or 0
        )
        return ads, int(total)
    except (KeyError, TypeError):
        return [], 0


# ──────────────────────────────────────────────────────────────────────────────
# Parseurs de champs
# ──────────────────────────────────────────────────────────────────────────────

def get_attr(ad: dict, key: str) -> str | None:
    for a in ad.get("attributes", []):
        if a.get("key") == key:
            return a.get("value_label") or str(a.get("value", ""))
    return None


def parse_price(ad: dict) -> float | None:
    p = ad.get("price")
    if isinstance(p, list) and p:
        return float(p[0])
    if isinstance(p, (int, float)):
        return float(p)
    return None


def parse_area(ad: dict) -> float | None:
    for key in ("square", "land_surface", "surface"):
        val = get_attr(ad, key)
        if val:
            n = re.sub(r"[^\d.,]", "", val).replace(",", ".")
            try:
                return float(n)
            except ValueError:
                pass
    for text in (ad.get("subject", ""), ad.get("body", "")):
        m = re.search(r"(\d[\d\s]*)\s*m[²2]", text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(" ", ""))
            except ValueError:
                pass
    return None


def get_coords(ad: dict) -> tuple:
    loc = ad.get("location", {})
    return loc.get("lat"), loc.get("lng")


def build_url(ad: dict) -> str:
    return f"https://www.leboncoin.fr/ad/terrains/{ad.get('list_id', '')}"


# ──────────────────────────────────────────────────────────────────────────────
# Temps de trajet OSRM (open-source, gratuit, sans clé)
# ──────────────────────────────────────────────────────────────────────────────

_sess = requests.Session()
_sess.headers["User-Agent"] = "leboncoin-scraper/1.0"


def drive_time(lat: float, lng: float) -> str:
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{lng},{lat};{TOULOUSE_LNG},{TOULOUSE_LAT}?overview=false"
    )
    try:
        r = _sess.get(url, timeout=12)
        d = r.json()
        if d.get("code") == "Ok":
            secs = d["routes"][0]["duration"]
            h, m = divmod(int(secs // 60), 60)
            return f"{h}h {m:02d}min" if h else f"{m}min"
    except Exception as e:
        print(f"    OSRM: {e}")
    return "N/A"


# ──────────────────────────────────────────────────────────────────────────────
# Scraping Playwright
# ──────────────────────────────────────────────────────────────────────────────

def human_pause(min_ms: int = 4000, max_ms: int = 9000):
    """Pause aléatoire imitant la lecture humaine."""
    delay = random.randint(min_ms, max_ms)
    time.sleep(delay / 1000)


def human_scroll(page: Page):
    """Fait défiler la page lentement, comme un vrai utilisateur."""
    height = page.evaluate("() => document.body.scrollHeight")
    step = random.randint(300, 600)
    current = 0
    while current < height:
        current += step
        page.evaluate(f"window.scrollTo(0, {current})")
        page.wait_for_timeout(random.randint(120, 350))
    # Remonte un peu de temps en temps
    if random.random() < 0.4:
        page.evaluate(f"window.scrollTo(0, {random.randint(0, current // 2)})")
        page.wait_for_timeout(random.randint(400, 900))


def accept_cookies(page: Page):
    try:
        btn = page.locator(
            "button:has-text('Tout accepter'), "
            "button:has-text('Accepter et fermer'), "
            "button[id*='accept']"
        )
        if btn.count():
            btn.first.click()
            page.wait_for_timeout(random.randint(1500, 2500))
    except Exception:
        pass


def scrape_page(page: Page, url: str) -> tuple:
    print(f"  GET {url[:85]}...")
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(random.randint(2500, 4500))  # laisse le JS s'exécuter
    accept_cookies(page)
    human_scroll(page)  # simule lecture 

    # Attendre les annonces
    try:
        page.wait_for_selector(
            "[data-test-id='aditem_container'], article[data-qa-id], "
            "[data-testid='ad-card']",
            timeout=20_000,
        )
    except PWTimeout:
        # Peut-être une page captcha → screenshot pour debug
        page.screenshot(path="debug_blocked.png")
        print("  ⚠ Annonces non trouvées → screenshot: debug_blocked.png")

    data = extract_next_data(page)
    if data:
        ads, total = find_ads_in_next_data(data)
        if ads:
            print(f"  ✓ {len(ads)} annonce(s) (via __NEXT_DATA__, total: {total})")
            return ads, total

    # Fallback DOM
    print("  ⚠ __NEXT_DATA__ vide → extraction DOM...")
    return extract_dom_ads(page), 0


def extract_dom_ads(page: Page) -> list:
    cards = page.locator(
        "article[data-qa-id], [data-test-id='aditem_container'], [data-testid='ad-card']"
    ).all()
    print(f"  ~ {len(cards)} carte(s) DOM")
    ads = []
    for card in cards:
        try:
            title = card.locator("[data-qa-id='aditem_title'], h2, h3").first.inner_text()
            price_txt = card.locator("[data-qa-id='aditem_price'], [class*='price']").first.inner_text()
            link = card.locator("a").first.get_attribute("href") or ""
            if link.startswith("/"):
                link = "https://www.leboncoin.fr" + link
            pnum = re.sub(r"[^\d]", "", price_txt)
            ads.append({
                "subject": title,
                "price": [int(pnum)] if pnum else [],
                "link": link,
            })
        except Exception:
            pass
    return ads


def get_all_ads(page: Page) -> list:
    all_ads = []
    total_announced = 0

    for p in range(1, MAX_PAGES + 1):
        url = SEARCH_URL + (f"&page={p}" if p > 1 else "")
        ads, total = scrape_page(page, url)

        if not ads:
            print(f"  → Arrêt page {p} (aucune annonce)")
            break

        if p == 1 and total:
            total_announced = total
            pages_needed = -(-total // 35)  # arrondi supérieur
            print(f"  Total annoncé par Leboncoin: {total} ({pages_needed} pages estimées)")

        all_ads.extend(ads)
        print(f"  Cumulé: {len(all_ads)} / {total_announced or '?'}")

        # Arrêt si on a tout récupéré
        if total_announced and len(all_ads) >= total_announced:
            break
        # Arrêt si dernière page (page incomplète)
        if len(ads) < 35 and p > 1:
            break

        # Pause inter-page : 8-18 s aléatoires
        delay = random.randint(8000, 18000)
        print(f"  ⏳ Pause {delay/1000:.1f}s avant page suivante...")
        page.wait_for_timeout(delay)

    return all_ads


# ──────────────────────────────────────────────────────────────────────────────
# Traitement & export
# ──────────────────────────────────────────────────────────────────────────────

def process(raw: list) -> list:
    rows = []
    for i, ad in enumerate(raw, 1):
        titre = ad.get("subject", "").strip()
        prix = parse_price(ad)
        superficie = parse_area(ad)
        lien = ad.get("link") or build_url(ad)
        prix_m2 = round(prix / superficie, 2) if prix and superficie and superficie > 0 else None

        lat, lng = get_coords(ad)
        if lat and lng:
            print(f"  [{i}/{len(raw)}] {titre[:55]}")
            trajet = drive_time(lat, lng)
            time.sleep(random.uniform(0.8, 2.0))
        else:
            trajet = "N/A"

        rows.append({
            "titre": titre,
            "prix": f"{prix:.0f}" if prix is not None else "",
            "superficie": f"{superficie:.0f}" if superficie is not None else "",
            "prix_m2": f"{prix_m2:.2f}" if prix_m2 is not None else "",
            "trajet": trajet,
            "lien": lien,
        })
    return rows


def export_csv(rows: list, path: str):
    fields = [
        "titre",
        "prix (€)",
        "superficie (m²)",
        "prix au m² (€/m²)",
        "temps trajet Toulouse",
        "lien",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow({
                "titre": r["titre"],
                "prix (€)": r["prix"],
                "superficie (m²)": r["superficie"],
                "prix au m² (€/m²)": r["prix_m2"],
                "temps trajet Toulouse": r["trajet"],
                "lien": r["lien"],
            })
    abs_path = Path(path).resolve()
    print(f"\n✓ {len(rows)} annonces → {abs_path}")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Leboncoin – Terrains constructibles (rayon 100km Toulouse)")
    print("=" * 60)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,   # visible → meilleure chance de passer DataDome
            slow_mo=120,      # chaque action Playwright prend 120ms minimum
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        page = ctx.new_page()

        # Masque la propriété webdriver
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        print("\n[1/3] Récupération des annonces...")
        raw = get_all_ads(page)
        browser.close()

    if not raw:
        print(
            "\n✗ Aucune annonce récupérée.\n"
            "  Causes possibles :\n"
            "  • IP bloquée par DataDome (fréquent sur IPs datacenter/VPN)\n"
            "  • Désactivez VPN/proxy et relancez depuis votre réseau personnel\n"
            "  • Consultez debug_blocked.png si présent"
        )
        return

    print(f"\n[2/3] Calcul temps de trajet Toulouse ({len(raw)} annonces)...")
    rows = process(raw)

    print("\n[3/3] Export CSV...")
    export_csv(rows, OUTPUT_CSV)

    print(f"\n{'='*60}")
    print(f"  Total annonces    : {len(rows)}")
    print(f"  Avec superficie   : {sum(1 for r in rows if r['superficie'])}")
    print(f"  Avec trajet calc. : {sum(1 for r in rows if r['trajet'] != 'N/A')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
