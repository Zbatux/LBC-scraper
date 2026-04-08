import random
import sqlite3

from playwright.sync_api import Page, TimeoutError as PWTimeout, sync_playwright

from browser import accept_cookies, create_browser_context

DELETED_SENTINEL = "__DELETED__"


def fetch_description(page: Page, url: str, is_first_page: bool = False) -> str | None:
    """Visite une annonce et retourne sa description complète.

    Retourne DELETED_SENTINEL si l'annonce est désactivée sur Leboncoin.
    Retourne None en cas d'erreur (retry au prochain run).
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        accept_cookies(page, is_first_page=is_first_page)

        # Détection d'annonce désactivée (avant le wait_for_selector pour éviter 5s d'attente)
        if page.locator("text=Cette annonce est désactivée").count():
            page.wait_for_timeout(random.randint(800, 1500))
            return DELETED_SENTINEL

        # Attendre le conteneur de description plutôt qu'un délai fixe
        desc_selector = (
            "[data-qa-id='adview_description_container'], "
            "[data-testid='description'], "
            "[class*='Description'], "
            "div[itemprop='description']"
        )
        try:
            page.wait_for_selector(desc_selector, timeout=5_000)
        except PWTimeout:
            pass  # Page sans description, on continue

        # Délai anti-bot après résolution du sélecteur
        page.wait_for_timeout(random.randint(800, 1500))

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


# Primary markers — each one alone is sufficient to confirm deletion
DELETED_MARKERS = [
    "text=Cette annonce est désactivée",
    "text=Cette annonce n'est plus disponible",
    "text=Annonce introuvable",
]

# Secondary marker — only confirms deletion when NO valid listing content is present
# (this text can appear on error/maintenance pages too, so it's not sufficient alone)
DELETED_MARKER_SECONDARY = "text=Retour à la page d'accueil"

VALID_LISTING_SELECTORS = (
    "[data-qa-id='adview_description_container'], "
    "[data-testid='description'], "
    "div[itemprop='description'], "
    "[data-qa-id='adview_title']"
)


def check_listing_status(page: Page, url: str, is_first_page: bool = False) -> str:
    """Visit a listing URL and check if it is disabled.

    Returns:
        'deleted'      — listing shows explicit deletion markers
        'online'       — listing page loaded with valid content
        'inconclusive' — could not determine status (anti-bot, error, etc.)
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        accept_cookies(page, is_first_page=is_first_page)

        # Anti-bot delay, let page render
        page.wait_for_timeout(random.randint(800, 1500) if is_first_page else random.randint(500, 1000))

        # 1) Check primary deletion markers FIRST (fast path)
        for marker in DELETED_MARKERS:
            if page.locator(marker).count() > 0:
                return "deleted"

        # 2) Wait for valid content using CSS-only selectors
        try:
            page.wait_for_selector(VALID_LISTING_SELECTORS, timeout=15_000)
        except PWTimeout:
            pass

        # 3) Check valid content
        if page.locator(VALID_LISTING_SELECTORS).count() > 0:
            return "online"

        # 4) Re-check primary deletion markers (may have rendered during the 15s wait)
        for marker in DELETED_MARKERS:
            if page.locator(marker).count() > 0:
                return "deleted"

        # 5) Check secondary deletion marker (only when no valid content found)
        if page.locator(DELETED_MARKER_SECONDARY).count() > 0:
            return "deleted"

        # 6) Neither deletion markers nor valid content found
        return "inconclusive"
    except Exception as e:
        print(f"    ⚠ Erreur vérification ({url[:60]}): {e}")
        return "inconclusive"


def check_all_statuses(db_name: str = "lbc_data.db"):
    """Check all non-deleted listings and flag disabled ones as deleted."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, lien FROM annonces WHERE (status IS NULL OR status != 'deleted')"
    )
    rows = cursor.fetchall()

    if not rows:
        print("  Aucune annonce à vérifier.")
        conn.close()
        return

    total = len(rows)
    print(f"  {total} annonce(s) à vérifier...")

    deleted = 0
    skipped = 0
    inconclusive_list = []

    try:
        with sync_playwright() as pw:
            browser, ctx, page = create_browser_context(pw)
            try:
                for i, (ad_id, lien) in enumerate(rows, 1):
                    print(f"  [{i}/{total}] {lien[:70]}")
                    result = check_listing_status(page, lien, is_first_page=(i == 1))

                    if result == "deleted":
                        conn.execute(
                            "UPDATE annonces SET status = 'deleted' WHERE id = ?",
                            (ad_id,)
                        )
                        conn.commit()
                        deleted += 1
                        print("    🗑 Annonce désactivée, marquée comme supprimée")
                    elif result == "online":
                        print("    ✓ En ligne")
                    else:
                        skipped += 1
                        inconclusive_list.append(lien)
                        print("    ⚠ Ignorée")

                    if i < total:
                        delay = random.randint(2000, 5000) if i == 1 else random.randint(1000, 3000)
                        page.wait_for_timeout(delay)
            finally:
                browser.close()
    finally:
        conn.close()

    print(f"  ✓ Vérification terminée : {deleted} supprimée(s), {skipped} ignorée(s) sur {total} vérifiée(s).")
    if inconclusive_list:
        print("  ⚠ Annonces non vérifiables (anti-bot ou erreur) :")
        for lien in inconclusive_list:
            print(f"    - {lien}")


def fetch_all_descriptions(db_name: str = "lbc_data.db"):
    """Parcourt les annonces sans description et les complète via Playwright."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, lien FROM annonces "
        "WHERE (description IS NULL OR description = '') "
        "AND (status IS NULL OR status != 'deleted')"
    )
    todo = cursor.fetchall()
    conn.close()

    if not todo:
        print("  Toutes les annonces ont déjà une description.")
        return

    print(f"  {len(todo)} annonce(s) sans description à traiter...")

    conn = sqlite3.connect(db_name)
    try:
        with sync_playwright() as pw:
            browser, ctx, page = create_browser_context(pw)
            try:
                updated = 0
                deleted = 0
                for i, (ad_id, lien) in enumerate(todo, 1):
                    print(f"  [{i}/{len(todo)}] {lien[:70]}")
                    description = fetch_description(page, lien, is_first_page=(i == 1))
                    if description == DELETED_SENTINEL:
                        conn.execute(
                            "UPDATE annonces SET status = 'deleted', description = NULL WHERE id = ?",
                            (ad_id,)
                        )
                        conn.commit()
                        deleted += 1
                        print("    🗑 Annonce désactivée, marquée comme supprimée")
                    elif description:
                        conn.execute(
                            "UPDATE annonces SET description = ? WHERE id = ?",
                            (description, ad_id)
                        )
                        conn.commit()
                        updated += 1
                    # Pause entre les pages
                    delay = random.randint(2000, 5000)
                    page.wait_for_timeout(delay)
            finally:
                browser.close()
    finally:
        conn.close()

    print(f"  ✓ {updated}/{len(todo)} descriptions ajoutées, {deleted} annonce(s) supprimée(s).")
