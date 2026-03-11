import hashlib
import random
import sqlite3
import time
from datetime import datetime

import matcher
from parsers import build_url, get_coords, parse_area, parse_price, parse_date_publication
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

        lat, lng = get_coords(ad)
        date_publication = parse_date_publication(ad)
        list_id = str(ad.get("list_id") or "")

        # Vérification si le trajet est déjà calculé en base
        key = hashlib.md5(f"{titre}|{superficie}".encode('utf-8')).hexdigest()
        if key in existing:
            trajet = existing[key]
            print(f"  [{i}/{len(raw)}] {titre[:55]} (trajet en cache : {trajet})")
        else:
            if lat is not None and lng is not None:
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
            "lat": lat,
            "lng": lng,
            "date_publication": date_publication,
            "list_id": list_id,
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
            "ALTER TABLE annonces ADD COLUMN list_id TEXT",
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


def save_or_merge(data, db_name="lbc_data.db"):
    """Sauvegarde ou fusionne les annonces : matching GPS+area, snapshots et statuts atomiques."""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # --- Schema init (idempotent) ---
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
            "ALTER TABLE annonces ADD COLUMN list_id TEXT",
        ]
        for sql in migrations:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError:
                pass

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
                date_publication TEXT,
                list_id TEXT
            )
        ''')

        try:
            cursor.execute("ALTER TABLE annonces_history ADD COLUMN list_id TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_annonce_id "
            "ON annonces_history(annonce_id)"
        )

        # Load all GPS candidates ONCE before the loop (NFR4 — no O(n²))
        cursor.execute(
            "SELECT id, lat, lng, superficie FROM annonces "
            "WHERE lat IS NOT NULL AND lng IS NOT NULL"
        )
        candidates = [dict(row) for row in cursor.fetchall()]

        nouvelles = 0
        scraped_at = datetime.now().isoformat()

        for annonce in data:
            unique_key = generate_unique_key(annonce)
            lat = annonce.get("lat")
            lng = annonce.get("lng")
            area = annonce.get("superficie")

            matched_id = matcher.find_match(lat, lng, area, candidates)

            if matched_id is not None:
                cursor.execute("SELECT * FROM annonces WHERE id = ?", (matched_id,))
                existing = cursor.fetchone()

                if existing is None:
                    matched_id = None  # stale candidate — fall through to insert
                else:
                    incoming_list_id = annonce.get("list_id") or ""
                    existing_list_id = existing["list_id"] or ""

                    if incoming_list_id and existing_list_id and incoming_list_id != existing_list_id:
                        status = 'reposted'
                    elif existing["prix"] != annonce.get("prix"):
                        status = 'price_changed'
                    else:
                        changed = any(
                            existing[f] != annonce.get(f)
                            for f in ("titre", "superficie", "lien", "trajet")
                        )
                        status = 'price_changed' if changed else 'unchanged'

                    if status != 'unchanged':
                        cursor.execute('''
                            INSERT INTO annonces_history (
                                annonce_id, scraped_at,
                                titre, prix, superficie, prix_m2, trajet, lien,
                                unique_key, description, viabilise, emprise_sol,
                                partiellement_constructible, partiellement_agricole,
                                analyse_faite, nogo, note,
                                lat, lng, status, first_seen, date_publication, list_id
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            matched_id, scraped_at,
                            existing["titre"], existing["prix"], existing["superficie"],
                            existing["prix_m2"], existing["trajet"], existing["lien"],
                            existing["unique_key"], existing["description"],
                            existing["viabilise"], existing["emprise_sol"],
                            existing["partiellement_constructible"],
                            existing["partiellement_agricole"],
                            existing["analyse_faite"], existing["nogo"], existing["note"],
                            existing["lat"], existing["lng"], existing["status"],
                            existing["first_seen"], existing["date_publication"],
                            existing["list_id"],
                        ))

                        cursor.execute('''
                            UPDATE annonces SET
                                titre=?, prix=?, superficie=?, prix_m2=?, trajet=?, lien=?,
                                lat=?, lng=?, date_publication=?, status=?, list_id=?
                            WHERE id=?
                        ''', (
                            annonce.get("titre"), annonce.get("prix"),
                            annonce.get("superficie"), annonce.get("prix_m2"),
                            annonce.get("trajet"), annonce.get("lien"),
                            lat, lng, annonce.get("date_publication"),
                            status, annonce.get("list_id") or "", matched_id,
                        ))
                    else:
                        # No data change → mark as unchanged.
                        # Still persist list_id if the existing row had none (migration case).
                        if incoming_list_id and not existing_list_id:
                            cursor.execute(
                                "UPDATE annonces SET status=?, list_id=? WHERE id=?",
                                ('unchanged', incoming_list_id, matched_id),
                            )
                        else:
                            cursor.execute(
                                "UPDATE annonces SET status=? WHERE id=?",
                                ('unchanged', matched_id),
                            )

            if matched_id is None:
                try:
                    cursor.execute('''
                        INSERT INTO annonces (
                            titre, prix, superficie, prix_m2, trajet, lien,
                            unique_key, lat, lng, date_publication,
                            status, first_seen, list_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        annonce.get("titre"), annonce.get("prix"),
                        annonce.get("superficie"), annonce.get("prix_m2"),
                        annonce.get("trajet"), annonce.get("lien"),
                        unique_key, lat, lng,
                        annonce.get("date_publication"),
                        'new', datetime.now().isoformat(),
                        annonce.get("list_id") or "",
                    ))
                    nouvelles += 1
                    if lat is not None and lng is not None:
                        candidates.append({
                            "id": cursor.lastrowid,
                            "lat": lat,
                            "lng": lng,
                            "superficie": area,
                        })
                except sqlite3.IntegrityError:
                    pass  # unique_key collision (GPS-less dedup fallback)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return nouvelles
