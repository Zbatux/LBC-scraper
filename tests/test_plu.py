import pytest
import requests

import plu


pytestmark = pytest.mark.integration


def test_plu_by_commune_negrepelisse():
    result = plu.get_plu_info(commune="Negrepelisse")
    assert "error" not in result, f"Unexpected error: {result}"
    assert result["code_insee"] == "82134"
    assert result["commune"] == "NÈGREPELISSE"
    assert result["type"] in ["PLU", "PLUi", "POS", "CC"]
    assert result["archive_url"].startswith("https://")


def test_plu_by_coords_negrepelisse():
    result = plu.get_plu_info(lat=44.075, lon=1.522)
    assert "error" not in result, f"Unexpected error: {result}"
    assert result["code_insee"] == "82134"
    assert result["archive_url"].startswith("https://")


def test_plu_commune_and_coords_same_result():
    by_name = plu.get_plu_info(commune="Negrepelisse")
    by_coords = plu.get_plu_info(lat=44.075, lon=1.522)
    assert by_name["archive_url"] == by_coords["archive_url"]


def test_plu_nonexistent_commune():
    result = plu.get_plu_info(commune="Zzzznotacommune")
    assert "error" in result


def test_plu_ocean_coords():
    result = plu.get_plu_info(lat=0.0, lon=0.0)
    assert "error" in result


def test_archive_url_is_downloadable():
    result = plu.get_plu_info(commune="Negrepelisse")
    assert "archive_url" in result, f"No archive_url: {result}"
    resp = requests.head(result["archive_url"], timeout=15, allow_redirects=True)
    assert resp.status_code in (200, 302)
