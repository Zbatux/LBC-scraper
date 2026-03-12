"""
Tests for GET /api/annonces endpoint — Story 2.1.

Verifies:
- AC1: status, first_seen, date_publication present in response
- AC2: status is a lowercase string literal (e.g. 'new')
- AC3: date_publication=NULL in DB → null in JSON (no crash)
- AC4: All 14 pre-existing fields remain present (non-regression)
"""
import sqlite3

import pytest
import database
import web

SAMPLE_LISTING = {
    "titre": "Terrain test",
    "prix": 50000.0,
    "superficie": 500.0,
    "prix_m2": 100.0,
    "trajet": "15 min",
    "lien": "https://www.leboncoin.fr/ad/1",
    "lat": 43.6,
    "lng": 1.4,
    "date_publication": "2024-01-01T10:00:00",
    "list_id": "1000001",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    database.save_or_merge([], db_name=db_path)
    monkeypatch.setattr(web, "DB_NAME", db_path)
    web.app.config["TESTING"] = True
    with web.app.test_client() as c:
        yield c, db_path


def test_get_annonces_includes_new_fields(client):
    """AC1: status, first_seen, date_publication are present in each listing."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    response = c.get("/api/annonces")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    listing = data[0]
    assert "status" in listing
    assert "first_seen" in listing
    assert "date_publication" in listing


def test_get_annonces_status_is_lowercase_string(client):
    """AC2: status value is a lowercase string literal, not null or int."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    response = c.get("/api/annonces")
    data = response.get_json()
    listing = data[0]

    assert isinstance(listing["status"], str)
    assert listing["status"] == listing["status"].lower()
    assert listing["status"] == "new"


def test_get_annonces_null_date_publication_serializes_to_null(client):
    """AC3: date_publication=NULL in DB → JSON null (no crash, no key omission)."""
    c, db_path = client
    sample_no_date = {
        "titre": "Terrain sans date",
        "prix": 30000.0,
        "superficie": 300.0,
        "prix_m2": 100.0,
        "trajet": "20 min",
        "lien": "https://www.leboncoin.fr/ad/2",
        "lat": 43.7,
        "lng": 1.5,
        "date_publication": None,
        "list_id": "1000002",
    }
    database.save_or_merge([sample_no_date], db_name=db_path)

    response = c.get("/api/annonces")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    listing = data[0]
    assert "date_publication" in listing
    assert listing["date_publication"] is None


def test_get_annonces_non_regression_existing_fields(client):
    """AC4: All 14 pre-existing fields are still present in the response."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    response = c.get("/api/annonces")
    data = response.get_json()
    listing = data[0]

    pre_existing_fields = [
        "id",
        "titre",
        "prix",
        "superficie",
        "prix_m2",
        "trajet",
        "lien",
        "viabilise",
        "emprise_sol",
        "partiellement_constructible",
        "partiellement_agricole",
        "analyse_faite",
        "nogo",
        "note",
    ]
    for field in pre_existing_fields:
        assert field in listing, f"Pre-existing field missing from response: {field}"


# ---------------------------------------------------------------------------
# Story 2.3: GET /api/annonces/<id>/history
# ---------------------------------------------------------------------------

def test_history_returns_snapshots_ordered_asc(client):
    """AC1+AC2: History rows ordered by scraped_at ASC, all key columns present."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    annonce = conn.execute("SELECT id FROM annonces LIMIT 1").fetchone()
    annonce_id = annonce["id"]
    conn.execute(
        "INSERT INTO annonces_history (annonce_id, scraped_at, titre, prix, status, list_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (annonce_id, "2024-01-01T10:00:00", "Terrain test v1", 40000.0, "price_changed", "1000001")
    )
    conn.execute(
        "INSERT INTO annonces_history (annonce_id, scraped_at, titre, prix, status, list_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (annonce_id, "2024-02-01T10:00:00", "Terrain test v2", 45000.0, "price_changed", "1000001")
    )
    conn.commit()
    conn.close()

    response = c.get(f"/api/annonces/{annonce_id}/history")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    # AC1: chronological ASC order
    assert data[0]["scraped_at"] == "2024-01-01T10:00:00"
    assert data[1]["scraped_at"] == "2024-02-01T10:00:00"
    # AC2: all snapshot columns present (SELECT * returns all columns, NULLs included)
    all_history_columns = (
        "id", "annonce_id", "scraped_at", "titre", "prix", "superficie", "prix_m2",
        "trajet", "lien", "unique_key", "description", "viabilise", "emprise_sol",
        "partiellement_constructible", "partiellement_agricole", "analyse_faite",
        "nogo", "note", "lat", "lng", "status", "first_seen", "date_publication", "list_id",
    )
    for key in all_history_columns:
        assert key in data[0], f"Missing column in history response: {key}"


def test_history_returns_empty_for_listing_with_no_history(client):
    """AC3+AC5: Listing exists but has no history → empty bare array, status 200."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    annonce = conn.execute("SELECT id FROM annonces LIMIT 1").fetchone()
    annonce_id = annonce["id"]
    conn.close()

    response = c.get(f"/api/annonces/{annonce_id}/history")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)   # AC5: bare array, NOT a dict
    assert data == []               # AC3: empty, not 404


def test_history_returns_404_for_nonexistent_id(client):
    """AC4: Non-existent integer ID → 404 with {"error": ...}."""
    c, db_path = client

    response = c.get("/api/annonces/99999/history")

    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_history_noninteger_id_returns_404(client):
    """AC4: Non-integer path value → Flask auto-404 (regression guard for <int:> param type)."""
    c, db_path = client

    response = c.get("/api/annonces/abc/history")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Story 2.4: history_count field in GET /api/annonces
# ---------------------------------------------------------------------------

def test_get_annonces_includes_history_count(client):
    """AC5: history_count is present and equals number of history rows."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    annonce = conn.execute("SELECT id FROM annonces LIMIT 1").fetchone()
    annonce_id = annonce["id"]
    conn.execute(
        "INSERT INTO annonces_history (annonce_id, scraped_at, titre, prix, status, list_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (annonce_id, "2024-01-01T10:00:00", "Terrain v1", 40000.0, "price_changed", "1000001")
    )
    conn.execute(
        "INSERT INTO annonces_history (annonce_id, scraped_at, titre, prix, status, list_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (annonce_id, "2024-02-01T10:00:00", "Terrain v2", 45000.0, "price_changed", "1000001")
    )
    conn.commit()
    conn.close()

    response = c.get("/api/annonces")
    data = response.get_json()
    listing = data[0]

    assert "history_count" in listing
    assert listing["history_count"] == 2


def test_get_annonces_history_count_zero_for_no_history(client):
    """AC5: listing with no history rows → history_count == 0."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    response = c.get("/api/annonces")
    data = response.get_json()
    listing = data[0]

    assert "history_count" in listing
    assert listing["history_count"] == 0


def test_get_annonces_non_regression_after_history_count_addition(client):
    """Non-regression: all 18 expected fields still present after history_count added."""
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    response = c.get("/api/annonces")
    data = response.get_json()
    listing = data[0]

    expected_fields = [
        "id", "titre", "prix", "superficie", "prix_m2", "trajet", "lien",
        "viabilise", "emprise_sol", "partiellement_constructible", "partiellement_agricole",
        "analyse_faite", "nogo", "note", "status", "first_seen", "date_publication",
        "history_count",
    ]
    for field in expected_fields:
        assert field in listing, f"Field missing from GET /api/annonces response: {field}"


# ---------------------------------------------------------------------------
# Similar listings endpoint tests
# ---------------------------------------------------------------------------

# ~1 km north of SAMPLE_LISTING GPS
_NEARBY_LAT = 43.6 + 0.008983
_NEARBY_LNG = 1.4

NEARBY_LISTING = {
    "titre": "Terrain voisin",
    "prix": 45000.0,
    "superficie": 480.0,
    "prix_m2": 93.75,
    "trajet": "18 min",
    "lien": "https://www.leboncoin.fr/ad/2",
    "lat": _NEARBY_LAT,
    "lng": _NEARBY_LNG,
    "date_publication": "2024-01-02T10:00:00",
    "list_id": "1000002",
}

FAR_LISTING = {
    "titre": "Terrain loin",
    "prix": 40000.0,
    "superficie": 500.0,
    "prix_m2": 80.0,
    "trajet": "25 min",
    "lien": "https://www.leboncoin.fr/ad/3",
    "lat": 44.0,
    "lng": 1.4,
    "date_publication": "2024-01-03T10:00:00",
    "list_id": "1000003",
}


def _get_annonce_id(db_path, titre):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id FROM annonces WHERE titre = ?", (titre,)).fetchone()
    conn.close()
    return row["id"]


def test_similar_returns_nearby_listings(client):
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy(), NEARBY_LISTING.copy()], db_name=db_path)
    aid = _get_annonce_id(db_path, "Terrain test")

    response = c.get(f"/api/annonces/{aid}/similar")

    assert response.status_code == 200
    data = response.get_json()
    assert "target" in data
    assert "similar" in data
    assert "summary" in data
    assert len(data["similar"]) == 1
    assert data["summary"]["count"] == 1


def test_similar_nonexistent_id_returns_404(client):
    c, db_path = client

    response = c.get("/api/annonces/99999/similar")

    assert response.status_code == 404
    assert "error" in response.get_json()


def test_similar_no_gps_returns_400(client):
    c, db_path = client
    no_gps = SAMPLE_LISTING.copy()
    no_gps["lat"] = None
    no_gps["lng"] = None
    no_gps["list_id"] = "1000010"
    database.save_or_merge([no_gps], db_name=db_path)
    aid = _get_annonce_id(db_path, "Terrain test")

    response = c.get(f"/api/annonces/{aid}/similar")

    assert response.status_code == 400
    assert "GPS" in response.get_json()["error"]


def test_similar_no_results(client):
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy(), FAR_LISTING.copy()], db_name=db_path)
    aid = _get_annonce_id(db_path, "Terrain test")

    response = c.get(f"/api/annonces/{aid}/similar")

    assert response.status_code == 200
    data = response.get_json()
    assert data["similar"] == []
    assert data["summary"]["count"] == 0
    assert data["summary"]["min_prix_m2"] is None
    assert data["summary"]["max_prix_m2"] is None
    assert data["summary"]["median_prix_m2"] is None


def test_similar_summary_stats_correct(client):
    c, db_path = client
    nearby2 = NEARBY_LISTING.copy()
    nearby2["titre"] = "Terrain voisin 2"
    nearby2["prix_m2"] = 110.0
    nearby2["list_id"] = "1000004"
    nearby2["lat"] = _NEARBY_LAT + 0.001
    database.save_or_merge([SAMPLE_LISTING.copy(), NEARBY_LISTING.copy(), nearby2], db_name=db_path)
    aid = _get_annonce_id(db_path, "Terrain test")

    response = c.get(f"/api/annonces/{aid}/similar")

    data = response.get_json()
    summary = data["summary"]
    assert summary["count"] == 2
    assert summary["min_prix_m2"] == 93.75
    assert summary["max_prix_m2"] == 110.0
    # median of [93.75, 110.0] = 101.875
    assert summary["median_prix_m2"] == 101.875


def test_similar_includes_distance(client):
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy(), NEARBY_LISTING.copy()], db_name=db_path)
    aid = _get_annonce_id(db_path, "Terrain test")

    response = c.get(f"/api/annonces/{aid}/similar")

    data = response.get_json()
    assert len(data["similar"]) == 1
    assert "distance_m" in data["similar"][0]
    assert isinstance(data["similar"][0]["distance_m"], int)


def test_similar_sorted_by_distance(client):
    c, db_path = client
    nearby2 = NEARBY_LISTING.copy()
    nearby2["titre"] = "Terrain plus loin"
    nearby2["lat"] = 43.6 + 0.015  # ~1.7 km
    nearby2["list_id"] = "1000005"
    database.save_or_merge([SAMPLE_LISTING.copy(), NEARBY_LISTING.copy(), nearby2], db_name=db_path)
    aid = _get_annonce_id(db_path, "Terrain test")

    response = c.get(f"/api/annonces/{aid}/similar")

    data = response.get_json()
    assert len(data["similar"]) == 2
    assert data["similar"][0]["distance_m"] <= data["similar"][1]["distance_m"]


def test_similar_excludes_self(client):
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy(), NEARBY_LISTING.copy()], db_name=db_path)
    aid = _get_annonce_id(db_path, "Terrain test")

    response = c.get(f"/api/annonces/{aid}/similar")

    data = response.get_json()
    similar_ids = [s["id"] for s in data["similar"]]
    assert aid not in similar_ids


def test_similar_nogo_excluded_from_stats(client):
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy(), NEARBY_LISTING.copy()], db_name=db_path)
    # Mark nearby listing as nogo
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE annonces SET nogo = 1 WHERE titre = ?", ("Terrain voisin",))
    conn.commit()
    conn.close()
    aid = _get_annonce_id(db_path, "Terrain test")

    response = c.get(f"/api/annonces/{aid}/similar")

    data = response.get_json()
    assert data["summary"]["count"] == 1  # still counted
    # But stats are null because the only similar listing is nogo
    assert data["summary"]["min_prix_m2"] is None


def test_annonces_api_includes_lat_lng(client):
    c, db_path = client
    database.save_or_merge([SAMPLE_LISTING.copy()], db_name=db_path)

    response = c.get("/api/annonces")

    data = response.get_json()
    listing = data[0]
    assert "lat" in listing
    assert "lng" in listing
    assert listing["lat"] == 43.6
    assert listing["lng"] == 1.4
