import random
import re
import time

from playwright.sync_api import Page, TimeoutError as PWTimeout

from config import MAX_PAGES, SEARCH_URL


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
