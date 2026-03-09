import random
import sqlite3

from playwright.sync_api import Page, sync_playwright

from browser import accept_cookies


def fetch_description(page: Page, url: str) -> str | None:
    """Visite une annonce et retourne sa description complète."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(random.randint(2000, 4000))
        accept_cookies(page)

        # Clic sur "Voir plus" / "Voir la suite" si présent
        voir_plus = page.locator(
            "button:has-text('Voir la suite'), "
            "button:has-text('Voir plus'), "
            "[data-qa-id='adview_description_more']"
        )
        if voir_plus.count():
            voir_plus.first.click()
            page.wait_for_timeout(random.randint(800, 1500))

        # Extraction du texte de description
        desc_loc = page.locator(
            "[data-qa-id='adview_description_container'], "
            "[data-testid='description'], "
            "[class*='Description'], "
            "div[itemprop='description']"
        )
        if desc_loc.count():
            return desc_loc.first.inner_text().strip()
    except Exception as e:
        print(f"    ⚠ Erreur description ({url[:60]}): {e}")
    return None


def fetch_all_descriptions(db_name: str = "lbc_data.db"):
    """Parcourt les annonces sans description et les complète via Playwright."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT id, lien FROM annonces WHERE description IS NULL OR description = ''")
    todo = cursor.fetchall()
    conn.close()

    if not todo:
        print("  Toutes les annonces ont déjà une description.")
        return

    print(f"  {len(todo)} annonce(s) sans description à traiter...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=80,
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
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        updated = 0
        for i, (ad_id, lien) in enumerate(todo, 1):
            print(f"  [{i}/{len(todo)}] {lien[:70]}")
            description = fetch_description(page, lien)
            if description:
                conn = sqlite3.connect(db_name)
                conn.execute(
                    "UPDATE annonces SET description = ? WHERE id = ?",
                    (description, ad_id)
                )
                conn.commit()
                conn.close()
                updated += 1
            # Pause entre les pages
            delay = random.randint(4000, 9000)
            page.wait_for_timeout(delay)

        browser.close()

    print(f"  ✓ {updated}/{len(todo)} descriptions ajoutées.")
