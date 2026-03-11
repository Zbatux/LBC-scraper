"""Tests for database.save_or_merge — Story 1.4."""
import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

import database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_db() -> str:
    """Create an empty temp SQLite file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def init_schema(db_path: str) -> None:
    """Initialize schema by calling save_or_merge with an empty list."""
    database.save_or_merge([], db_name=db_path)


def insert_existing(db_path: str, **overrides) -> int:
    """Insert a pre-existing listing directly (simulates rows from old save_to_database).

    Requires schema to be initialized first (call init_schema).
    Returns the inserted row's id.
    """
    defaults = {
        "titre": "Terrain existant",
        "prix": 50000.0,
        "superficie": 500.0,
        "prix_m2": 100.0,
        "trajet": "15 min",
        "lien": "https://www.leboncoin.fr/ad/1000001",
        "unique_key": "existing_key_001",
        "lat": 43.6044622,
        "lng": 1.4442469,
        "date_publication": "2024-01-01T10:00:00",
        "status": "new",
        "first_seen": "2024-01-01T10:00:00",
        "list_id": "1000001",
    }
    defaults.update(overrides)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO annonces
               (titre, prix, superficie, prix_m2, trajet, lien, unique_key,
                lat, lng, date_publication, status, first_seen, list_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            defaults["titre"], defaults["prix"], defaults["superficie"],
            defaults["prix_m2"], defaults["trajet"], defaults["lien"],
            defaults["unique_key"], defaults["lat"], defaults["lng"],
            defaults["date_publication"], defaults["status"],
            defaults["first_seen"], defaults["list_id"],
        ),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


# Incoming listing that fuzzy-matches the default existing row (same GPS + area)
MATCHING_INCOMING = {
    "titre": "Terrain existant",
    "prix": 50000.0,
    "superficie": 500.0,
    "prix_m2": 100.0,
    "trajet": "15 min",
    "lien": "https://www.leboncoin.fr/ad/1000001",
    "lat": 43.6044622,
    "lng": 1.4442469,
    "date_publication": "2024-01-01T10:00:00",
    "list_id": "1000001",
}


# ---------------------------------------------------------------------------
# AC3: New listing → INSERT with status='new'
# ---------------------------------------------------------------------------

def test_new_listing_inserted_with_status_new():
    db = make_db()
    try:
        row = {
            "titre": "Nouveau terrain",
            "prix": 80000.0,
            "superficie": 800.0,
            "prix_m2": 100.0,
            "trajet": "20 min",
            "lien": "https://www.leboncoin.fr/ad/9999",
            "lat": 44.0,
            "lng": 2.0,
            "date_publication": "2024-06-01T08:00:00",
            "list_id": "9999",
        }
        n = database.save_or_merge([row], db_name=db)
        assert n == 1

        conn = sqlite3.connect(db)
        r = conn.execute(
            "SELECT status, first_seen, list_id, lat, lng FROM annonces"
        ).fetchone()
        conn.close()

        assert r[0] == "new"
        assert r[1] is not None   # first_seen is set
        assert r[2] == "9999"
        assert r[3] == 44.0
        assert r[4] == 2.0
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# AC4 + AC3: lat, lng, date_publication, list_id all persisted on INSERT
# ---------------------------------------------------------------------------

def test_all_new_fields_persisted_on_insert():
    db = make_db()
    try:
        row = {
            "titre": "Terrain GPS",
            "prix": 60000.0,
            "superficie": 600.0,
            "prix_m2": 100.0,
            "trajet": "10 min",
            "lien": "https://www.leboncoin.fr/ad/7777",
            "lat": 43.5,
            "lng": 1.3,
            "date_publication": "2024-03-15T12:00:00",
            "list_id": "7777",
        }
        database.save_or_merge([row], db_name=db)

        conn = sqlite3.connect(db)
        r = conn.execute(
            "SELECT lat, lng, date_publication, list_id FROM annonces"
        ).fetchone()
        conn.close()

        assert r[0] == 43.5
        assert r[1] == 1.3
        assert r[2] == "2024-03-15T12:00:00"
        assert r[3] == "7777"
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# AC1: Fuzzy match + prix changed → price_changed + snapshot
# ---------------------------------------------------------------------------

def test_fuzzy_match_price_changed_creates_snapshot():
    db = make_db()
    try:
        init_schema(db)
        existing_id = insert_existing(db, prix=50000.0, list_id="1000001")

        incoming = {**MATCHING_INCOMING, "prix": 45000.0}
        n = database.save_or_merge([incoming], db_name=db)

        assert n == 0  # no new inserts — it's a match

        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status, prix FROM annonces WHERE id=?", (existing_id,)
        ).fetchone()
        snapshot = conn.execute("SELECT prix FROM annonces_history").fetchone()
        conn.close()

        assert row[0] == "price_changed"
        assert row[1] == 45000.0      # updated to new price
        assert snapshot is not None
        assert snapshot[0] == 50000.0  # snapshot captured OLD price
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# AC4: Fuzzy match + different list_id → reposted + snapshot
# ---------------------------------------------------------------------------

def test_fuzzy_match_reposted_via_list_id():
    db = make_db()
    try:
        init_schema(db)
        existing_id = insert_existing(db, list_id="1000001")

        incoming = {**MATCHING_INCOMING, "list_id": "9999999"}
        database.save_or_merge([incoming], db_name=db)

        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status, list_id FROM annonces WHERE id=?", (existing_id,)
        ).fetchone()
        snap_list_id = conn.execute(
            "SELECT list_id FROM annonces_history"
        ).fetchone()
        conn.close()

        assert row[0] == "reposted"
        assert row[1] == "9999999"         # updated to new list_id
        assert snap_list_id[0] == "1000001"  # snapshot has OLD list_id
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# AC2: Fuzzy match + identical data → unchanged, no snapshot
# ---------------------------------------------------------------------------

def test_fuzzy_match_unchanged_no_snapshot():
    db = make_db()
    try:
        init_schema(db)
        existing_id = insert_existing(db)

        database.save_or_merge([MATCHING_INCOMING], db_name=db)

        conn = sqlite3.connect(db)
        status = conn.execute(
            "SELECT status FROM annonces WHERE id=?", (existing_id,)
        ).fetchone()[0]
        history_count = conn.execute(
            "SELECT COUNT(*) FROM annonces_history"
        ).fetchone()[0]
        conn.close()

        assert status == "unchanged"
        assert history_count == 0
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# AC3: GPS=None → no match attempted → INSERT as new
# ---------------------------------------------------------------------------

def test_gps_none_listing_inserted_as_new():
    db = make_db()
    try:
        row = {
            "titre": "Terrain sans GPS",
            "prix": 30000.0,
            "superficie": 300.0,
            "prix_m2": 100.0,
            "trajet": "N/A",
            "lien": "https://www.leboncoin.fr/ad/5555",
            "lat": None,
            "lng": None,
            "date_publication": None,
            "list_id": "5555",
        }
        n = database.save_or_merge([row], db_name=db)

        assert n == 1

        conn = sqlite3.connect(db)
        status = conn.execute("SELECT status FROM annonces").fetchone()[0]
        conn.close()

        assert status == "new"
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# AC5: Atomicity — exception mid-loop → full rollback
# ---------------------------------------------------------------------------

def test_atomicity_rollback_on_exception():
    db = make_db()
    try:
        init_schema(db)
        existing_id = insert_existing(db, prix=50000.0)

        incoming1 = {**MATCHING_INCOMING, "prix": 45000.0}  # would create snapshot
        incoming2 = {
            "titre": "Row 2", "prix": 1.0, "superficie": 1.0,
            "prix_m2": 1.0, "trajet": "N/A", "lien": "",
            "lat": None, "lng": None, "date_publication": None, "list_id": "0",
        }

        # First call returns a match; second call raises
        with patch(
            "database.matcher.find_match",
            side_effect=[existing_id, RuntimeError("simulated crash")],
        ):
            with pytest.raises(RuntimeError):
                database.save_or_merge([incoming1, incoming2], db_name=db)

        conn = sqlite3.connect(db)
        history_count = conn.execute(
            "SELECT COUNT(*) FROM annonces_history"
        ).fetchone()[0]
        prix = conn.execute(
            "SELECT prix FROM annonces WHERE id=?", (existing_id,)
        ).fetchone()[0]
        conn.close()

        assert history_count == 0     # snapshot was rolled back
        assert prix == 50000.0        # update was rolled back
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# Idempotency: run save_or_merge twice → no OperationalError
# ---------------------------------------------------------------------------

def test_schema_migration_idempotency():
    db = make_db()
    try:
        row = {
            "titre": "Idem",
            "prix": 10000.0,
            "superficie": 100.0,
            "prix_m2": 100.0,
            "trajet": "5 min",
            "lien": "https://www.leboncoin.fr/ad/1",
            "lat": 43.0,
            "lng": 1.0,
            "date_publication": None,
            "list_id": "1",
        }
        database.save_or_merge([row], db_name=db)
        row2 = {**row, "lien": "https://www.leboncoin.fr/ad/2", "list_id": "2",
                "lat": 50.0, "lng": 2.0}
        # Should not raise
        database.save_or_merge([row2], db_name=db)
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# AC1: Fuzzy match + titre changed (prix and list_id identical) → price_changed + snapshot
# ---------------------------------------------------------------------------

def test_fuzzy_match_titre_changed_creates_snapshot():
    """titre changed while prix and list_id are identical → price_changed + snapshot."""
    db = make_db()
    try:
        init_schema(db)
        existing_id = insert_existing(db, titre="Ancien titre", list_id="1000001")

        # MATCHING_INCOMING has titre="Terrain existant" — different from "Ancien titre"
        incoming = {**MATCHING_INCOMING, "list_id": "1000001"}
        n = database.save_or_merge([incoming], db_name=db)

        assert n == 0  # match, not a new insert

        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status, titre FROM annonces WHERE id=?", (existing_id,)
        ).fetchone()
        snap_count = conn.execute("SELECT COUNT(*) FROM annonces_history").fetchone()[0]
        conn.close()

        assert row[0] == "price_changed"
        assert row[1] == "Terrain existant"  # updated to incoming titre
        assert snap_count == 1
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# M1: unchanged match with empty existing list_id → list_id populated, no repost
# ---------------------------------------------------------------------------

def test_unchanged_match_populates_list_id_when_existing_was_empty():
    """Existing row has no list_id; incoming has one. Should stay unchanged but persist list_id."""
    db = make_db()
    try:
        init_schema(db)
        existing_id = insert_existing(db, list_id="")  # migrated row: no list_id

        incoming = {**MATCHING_INCOMING, "list_id": "1000001"}
        database.save_or_merge([incoming], db_name=db)

        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status, list_id FROM annonces WHERE id=?", (existing_id,)
        ).fetchone()
        history_count = conn.execute("SELECT COUNT(*) FROM annonces_history").fetchone()[0]
        conn.close()

        assert row[0] == "unchanged"   # not flagged as repost — existing had no list_id
        assert row[1] == "1000001"     # list_id now populated
        assert history_count == 0      # no snapshot for unchanged
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# unique_key dedup for GPS-less listings (backward-compat fallback)
# ---------------------------------------------------------------------------

def test_unique_key_dedup_for_gps_less_listings():
    db = make_db()
    try:
        row = {
            "titre": "Terrain sans GPS dedup",
            "prix": 30000.0,
            "superficie": 300.0,
            "prix_m2": 100.0,
            "trajet": "N/A",
            "lien": "https://www.leboncoin.fr/ad/5555",
            "lat": None,
            "lng": None,
            "date_publication": None,
            "list_id": "5555",
        }
        database.save_or_merge([row], db_name=db)
        database.save_or_merge([row], db_name=db)  # second run — should be deduped

        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM annonces").fetchone()[0]
        conn.close()

        assert count == 1
    finally:
        os.unlink(db)


# ---------------------------------------------------------------------------
# Within-run duplicate guard: two GPS listings with same location in one run
# ---------------------------------------------------------------------------

def test_within_run_gps_dedup():
    """Two listings with same GPS+area in one scrape: second treated as match of first."""
    db = make_db()
    try:
        row1 = {
            "titre": "Terrain A",
            "prix": 50000.0,
            "superficie": 500.0,
            "prix_m2": 100.0,
            "trajet": "15 min",
            "lien": "https://www.leboncoin.fr/ad/111",
            "lat": 43.6044622,
            "lng": 1.4442469,
            "date_publication": "2024-01-01T10:00:00",
            "list_id": "111",
        }
        # same GPS+area, same list_id (same listing), different price
        row2 = {**row1, "titre": "Terrain B", "lien": "https://www.leboncoin.fr/ad/111",
                "list_id": "111", "prix": 45000.0}

        n = database.save_or_merge([row1, row2], db_name=db)

        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT titre, status FROM annonces").fetchall()
        history_count = conn.execute("SELECT COUNT(*) FROM annonces_history").fetchone()[0]
        conn.close()

        # row1 is inserted as new; row2 matches row1 (same GPS+area, same list_id) → price_changed
        assert n == 1  # only row1 is a new insert
        assert len(rows) == 1  # only one annonces row (row2 updated row1)
        assert rows[0][1] == "price_changed"
        assert history_count == 1  # snapshot of row1 created before row2 update
    finally:
        os.unlink(db)
