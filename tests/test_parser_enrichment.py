"""Tests for Story 1.3: Parser Enrichment — parse_date_publication, get_coords, process() output"""
from unittest.mock import patch
import parsers
import database


# ---------------------------------------------------------------------------
# AC3 & AC4: parse_date_publication
# ---------------------------------------------------------------------------

class TestParseDatePublication:
    def test_returns_string_when_present(self):
        ad = {"first_publication_date": "2024-06-15T10:00:00+02:00"}
        assert parsers.parse_date_publication(ad) == "2024-06-15T10:00:00+02:00"

    def test_returns_none_when_key_absent(self):
        assert parsers.parse_date_publication({}) is None

    def test_returns_none_when_value_is_none(self):
        assert parsers.parse_date_publication({"first_publication_date": None}) is None

    def test_returns_none_when_value_is_empty_string(self):
        assert parsers.parse_date_publication({"first_publication_date": ""}) is None

    def test_coerces_non_string_to_string(self):
        ad = {"first_publication_date": 20240615}
        result = parsers.parse_date_publication(ad)
        assert result == "20240615"

    def test_unrelated_keys_ignored(self):
        ad = {"subject": "Terrain", "price": [50000]}
        assert parsers.parse_date_publication(ad) is None


# ---------------------------------------------------------------------------
# AC1 & AC2: get_coords
# ---------------------------------------------------------------------------

class TestGetCoords:
    def test_returns_floats_when_present(self):
        ad = {"location": {"lat": 43.6044622, "lng": 1.4442469}}
        lat, lng = parsers.get_coords(ad)
        assert lat == 43.6044622
        assert lng == 1.4442469
        assert isinstance(lat, float)
        assert isinstance(lng, float)

    def test_returns_floats_when_int_coords(self):
        """AC1: integer coordinates from JSON must be cast to float."""
        ad = {"location": {"lat": 43, "lng": 1}}
        lat, lng = parsers.get_coords(ad)
        assert isinstance(lat, float)
        assert isinstance(lng, float)
        assert lat == 43.0
        assert lng == 1.0

    def test_returns_none_none_when_no_location_key(self):
        lat, lng = parsers.get_coords({})
        assert lat is None
        assert lng is None

    def test_returns_none_none_when_location_empty(self):
        lat, lng = parsers.get_coords({"location": {}})
        assert lat is None
        assert lng is None

    def test_returns_none_for_lat_when_lat_missing(self):
        lat, lng = parsers.get_coords({"location": {"lng": 1.44}})
        assert lat is None
        assert lng == 1.44

    def test_returns_none_for_lng_when_lng_missing(self):
        lat, lng = parsers.get_coords({"location": {"lat": 43.6}})
        assert lat == 43.6
        assert lng is None

    def test_returns_none_none_when_coords_malformed(self):
        """AC2: malformed (non-numeric) coordinates must return None, not raise."""
        lat, lng = parsers.get_coords({"location": {"lat": "invalid", "lng": "not_a_number"}})
        assert lat is None
        assert lng is None


# ---------------------------------------------------------------------------
# AC1, AC2, AC3, AC4, AC5: process() output dict
# ---------------------------------------------------------------------------

def _make_ad(lat=43.6044622, lng=1.4442469, date_pub="2024-06-15T10:00:00+02:00"):
    ad = {
        "subject": "Terrain test",
        "price": [50000],
        "attributes": [{"key": "land_surface", "value_label": "500"}],
        "link": "https://www.leboncoin.fr/ad/ventes_immobilieres/123",
    }
    if lat is not None or lng is not None:
        ad["location"] = {}
        if lat is not None:
            ad["location"]["lat"] = lat
        if lng is not None:
            ad["location"]["lng"] = lng
    if date_pub is not None:
        ad["first_publication_date"] = date_pub
    return ad


class TestProcessOutputDict:
    def test_output_includes_lat_lng_date_publication(self):
        raw = [_make_ad()]
        with patch("database.drive_time", return_value="15 min"), \
             patch("database.get_existing_trajets", return_value={}):
            result = database.process(raw)
        assert len(result) == 1
        row = result[0]
        assert row["lat"] == 43.6044622
        assert row["lng"] == 1.4442469
        assert row["date_publication"] == "2024-06-15T10:00:00+02:00"

    def test_output_preserves_all_existing_fields(self):
        raw = [_make_ad()]
        with patch("database.drive_time", return_value="15 min"), \
             patch("database.get_existing_trajets", return_value={}):
            result = database.process(raw)
        row = result[0]
        for key in ("titre", "prix", "superficie", "prix_m2", "trajet", "lien"):
            assert key in row, f"Missing existing field: {key}"

    def test_lat_lng_none_when_no_gps(self):
        ad = {
            "subject": "Terrain sans GPS",
            "price": [30000],
            "attributes": [{"key": "land_surface", "value_label": "200"}],
            "link": "https://www.leboncoin.fr/ad/ventes_immobilieres/456",
        }
        with patch("database.drive_time", return_value="N/A"), \
             patch("database.get_existing_trajets", return_value={}):
            result = database.process([ad])
        row = result[0]
        assert row["lat"] is None
        assert row["lng"] is None

    def test_date_publication_none_when_absent(self):
        ad = {
            "subject": "Terrain sans date",
            "price": [40000],
            "location": {"lat": 43.6, "lng": 1.44},
            "attributes": [{"key": "land_surface", "value_label": "300"}],
            "link": "https://www.leboncoin.fr/ad/ventes_immobilieres/789",
        }
        with patch("database.drive_time", return_value="10 min"), \
             patch("database.get_existing_trajets", return_value={}):
            result = database.process([ad])
        assert result[0]["date_publication"] is None

    def test_lat_lng_extracted_even_when_trajet_cached(self):
        """Ensures get_coords() is called unconditionally, not just in the routing branch."""
        ad = _make_ad()
        titre = ad["subject"].strip()
        import hashlib
        superficie = 500.0
        key = hashlib.md5(f"{titre}|{superficie}".encode("utf-8")).hexdigest()
        with patch("database.get_existing_trajets", return_value={key: "20 min"}):
            result = database.process([ad])
        row = result[0]
        assert row["lat"] == 43.6044622
        assert row["lng"] == 1.4442469
        assert row["trajet"] == "20 min"
