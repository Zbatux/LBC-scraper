"""
Tests for GET /api/annonces endpoint — Story 2.1.

Verifies:
- AC1: status, first_seen, date_publication present in response
- AC2: status is a lowercase string literal (e.g. 'new')
- AC3: date_publication=NULL in DB → null in JSON (no crash)
- AC4: All 14 pre-existing fields remain present (non-regression)
"""
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
