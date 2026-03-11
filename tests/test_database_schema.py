import os
import sqlite3
import sys
import tempfile

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database


def _make_db():
    """Create a temporary SQLite database file and return (fd, path)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


# ---------------------------------------------------------------------------
# AC3 + AC5: Idempotent schema init
# ---------------------------------------------------------------------------

def test_schema_idempotent():
    """Running save_to_database twice must not raise OperationalError."""
    path = _make_db()
    try:
        database.save_to_database([], db_name=path)  # first init
        database.save_to_database([], db_name=path)  # second init — must not raise
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# AC1: New columns on annonces
# ---------------------------------------------------------------------------

def test_annonces_new_columns_exist():
    """All five new columns must be present on the annonces table."""
    path = _make_db()
    try:
        database.save_to_database([], db_name=path)
        conn = sqlite3.connect(path)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(annonces)")
            columns = {row[1] for row in cursor.fetchall()}
        finally:
            conn.close()
        assert "lat" in columns
        assert "lng" in columns
        assert "status" in columns
        assert "first_seen" in columns
        assert "date_publication" in columns
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# AC2: annonces_history table exists with all required columns
# ---------------------------------------------------------------------------

def test_annonces_history_table_exists():
    """annonces_history table must be created on first run."""
    path = _make_db()
    try:
        database.save_to_database([], db_name=path)
        conn = sqlite3.connect(path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='annonces_history'"
            )
            result = cursor.fetchone()
        finally:
            conn.close()
        assert result is not None, "annonces_history table not found"
    finally:
        os.unlink(path)


def test_annonces_history_columns():
    """annonces_history must mirror all annonces columns plus id, annonce_id, scraped_at."""
    path = _make_db()
    try:
        database.save_to_database([], db_name=path)
        conn = sqlite3.connect(path)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(annonces_history)")
            columns = {row[1] for row in cursor.fetchall()}
        finally:
            conn.close()
        required = {
            "id", "annonce_id", "scraped_at",
            "titre", "prix", "superficie", "prix_m2", "trajet", "lien",
            "unique_key", "description", "viabilise", "emprise_sol",
            "partiellement_constructible", "partiellement_agricole",
            "analyse_faite", "nogo", "note",
            "lat", "lng", "status", "first_seen", "date_publication",
        }
        missing = required - columns
        assert not missing, f"Missing columns in annonces_history: {missing}"
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# AC4: Index on annonce_id
# ---------------------------------------------------------------------------

def test_idx_history_annonce_id_exists():
    """idx_history_annonce_id index must exist on annonces_history."""
    path = _make_db()
    try:
        database.save_to_database([], db_name=path)
        conn = sqlite3.connect(path)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA index_list(annonces_history)")
            indexes = {row[1] for row in cursor.fetchall()}
        finally:
            conn.close()
        assert "idx_history_annonce_id" in indexes
    finally:
        os.unlink(path)
