import argparse
import webbrowser
from datetime import datetime

from playwright.sync_api import sync_playwright

from analyzer import analyze_all
from browser import create_browser_context, get_all_ads
from database import process, save_or_merge
from descriptions import check_all_statuses, fetch_all_descriptions
from exporter import export_to_csv


def main():
    parser = argparse.ArgumentParser(
        description="Scraper Leboncoin – Terrains constructibles.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Lance le scraping et sauvegarde les nouvelles annonces en base.",
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Exporte les données de la base SQLite vers un fichier CSV.",
    )
    parser.add_argument(
        "--get-description",
        action="store_true",
        help="Visite les annonces sans description et récupère leur texte descriptif.",
    )
    parser.add_argument(
        "--check-status",
        action="store_true",
        help="Vérifie si les annonces sont toujours en ligne et marque les désactivées.",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyse les descriptions via Ollama (gemma3:12b) et remplit les champs IA.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Lance l'interface web d'édition des annonces sur http://localhost:5000.",
    )
    args = parser.parse_args()

    if not args.scrape and not args.export_csv and not args.get_description and not args.check_status and not args.analyze and not args.web:
        parser.print_help()
        return

    print("=" * 60)
    print("  Leboncoin – Terrains constructibles (rayon 100km Toulouse)")
    print("=" * 60)

    if args.scrape:
        with sync_playwright() as pw:
            browser, ctx, page = create_browser_context(pw, slow_mo=60)

            print("\n[1/2] Récupération des annonces...")
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

        print(f"\n[2/2] Calcul temps de trajet Toulouse ({len(raw)} annonces)...")
        rows = process(raw)

        print("\nSauvegarde en base de données...")
        nouvelles = save_or_merge(rows)

        print(f"\n{'='*60}")
        print(f"  Total annonces    : {len(rows)}")
        print(f"  Nouvelles annonces: {nouvelles}")
        print(f"  Avec superficie   : {sum(1 for r in rows if r['superficie'])}")
        print(f"  Avec trajet calc. : {sum(1 for r in rows if r['trajet'] != 'N/A')}")
        print(f"{'='*60}")

    if args.export_csv:
        csv_file = f"terrains_leboncoin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        export_to_csv(csv_file=csv_file)

    if args.get_description:
        print("\nRécupération des descriptions manquantes...")
        fetch_all_descriptions()

    if args.check_status:
        print("\nVérification du statut des annonces...")
        check_all_statuses()

    if args.analyze:
        print("\nAnalyse IA des descriptions (Ollama)...")
        analyze_all()

    if args.web:
        from web import app
        print("\nInterface web disponible sur http://localhost:5000")
        webbrowser.open("http://localhost:5000")
        app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
