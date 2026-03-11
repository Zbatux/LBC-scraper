import hashlib
import random
import sqlite3
import time

from parsers import build_url, get_coords, parse_area, parse_price
from routing import drive_time


def get_existing_trajets(db_name: str = "lbc_data.db") -> dict:
    """Retourne un dict {unique_key: trajet} pour les annonces déjà en base avec un trajet calculé."""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT unique_key, trajet FROM annonces "
            "WHERE trajet IS NOT NULL AND trajet != 'N/A'"
        )
        result = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return result
    except sqlite3.OperationalError:
        return {}


def generate_unique_key(annonce):
    """Génère une clé unique pour une annonce basée sur son titre et sa superficie."""
    raw = f"{annonce.get('titre', '')}|{annonce.get('superficie', '')}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def process(raw: list) -> list:
    existing = get_existing_trajets()
    rows = []
    for i, ad in enumerate(raw, 1):
        titre = ad.get("subject", "").strip()
        prix = parse_price(ad)
        superficie = parse_area(ad)
        lien = ad.get("link") or build_url(ad)
        prix_m2 = round(prix / superficie, 2) if prix and superficie and superficie > 0 else None

        # Vérification si le trajet est déjà calculé en base
        key = hashlib.md5(f"{titre}|{superficie}".encode('utf-8')).hexdigest()
        if key in existing:
            trajet = existing[key]
            print(f"  [{i}/{len(raw)}] {titre[:55]} (trajet en cache : {trajet})")
        else:
            lat, lng = get_coords(ad)
            if lat and lng:
                print(f"  [{i}/{len(raw)}] {titre[:55]}")
                trajet = drive_time(lat, lng)
                time.sleep(random.uniform(0.8, 2.0))
            else:
                trajet = "N/A"

        rows.append({
            "titre": titre,
            "prix": prix,
            "superficie": superficie,
            "prix_m2": prix_m2,
            "trajet": trajet,
            "lien": lien,
        })
    return rows


def save_to_database(data, db_name="lbc_data.db"):
    """Enregistre les données extraites dans une base de données SQLite."""
    conn = sqlite3.connect(db_name)
    try:
        cursor = conn.cursor()

        # Création de la table si elle n'existe pas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS annonces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titre TEXT,
                prix REAL,
                superficie REAL,
                prix_m2 REAL,
                trajet TEXT,
                lien TEXT,
                unique_key TEXT UNIQUE,
                description TEXT
            )
        ''')

        # Migration : ajout des colonnes manquantes pour les bases existantes
        migrations = [
            "ALTER TABLE annonces ADD COLUMN description TEXT",
            "ALTER TABLE annonces ADD COLUMN viabilise INTEGER",
            "ALTER TABLE annonces ADD COLUMN emprise_sol REAL",
            "ALTER TABLE annonces ADD COLUMN partiellement_constructible INTEGER",
            "ALTER TABLE annonces ADD COLUMN partiellement_agricole INTEGER",
            "ALTER TABLE annonces ADD COLUMN analyse_faite INTEGER DEFAULT 0",
            "ALTER TABLE annonces ADD COLUMN nogo INTEGER DEFAULT 0",
            "ALTER TABLE annonces ADD COLUMN note INTEGER",
            "ALTER TABLE annonces ADD COLUMN lat REAL",
            "ALTER TABLE annonces ADD COLUMN lng REAL",
            "ALTER TABLE annonces ADD COLUMN status TEXT",
            "ALTER TABLE annonces ADD COLUMN first_seen TEXT",
            "ALTER TABLE annonces ADD COLUMN date_publication TEXT",
        ]
        for sql in migrations:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError:
                pass  # colonne déjà présente

        # Historique des snapshots de scraping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS annonces_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                annonce_id INTEGER,
                scraped_at TEXT,
                titre TEXT,
                prix REAL,
                superficie REAL,
                prix_m2 REAL,
                trajet TEXT,
                lien TEXT,
                unique_key TEXT,
                description TEXT,
                viabilise INTEGER,
                emprise_sol REAL,
                partiellement_constructible INTEGER,
                partiellement_agricole INTEGER,
                analyse_faite INTEGER DEFAULT 0,
                nogo INTEGER DEFAULT 0,
                note INTEGER,
                lat REAL,
                lng REAL,
                status TEXT,
                first_seen TEXT,
                date_publication TEXT
            )
        ''')

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_annonce_id "
            "ON annonces_history(annonce_id)"
        )

        nouvelles = 0
        for annonce in data:
            unique_key = generate_unique_key(annonce)
            try:
                cursor.execute('''
                    INSERT INTO annonces (titre, prix, superficie, prix_m2, trajet, lien, unique_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    annonce.get("titre"),
                    annonce.get("prix"),
                    annonce.get("superficie"),
                    annonce.get("prix_m2"),
                    annonce.get("trajet"),
                    annonce.get("lien"),
                    unique_key
                ))
                nouvelles += 1
            except sqlite3.IntegrityError:
                pass  # doublon, ignoré

        conn.commit()
    finally:
        conn.close()
    return nouvelles
