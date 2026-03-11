"""Tests for matcher.py — Story 1.1: Fuzzy Matcher Module"""
import pytest
import config
import matcher


# ---------------------------------------------------------------------------
# Helper: two real GPS points ~30m apart (same building, different corners)
# Toulouse city hall area
# ---------------------------------------------------------------------------
LAT_A = 43.6044622
LNG_A = 1.4442469
# ~30m north
LAT_B = 43.6047322
LNG_B = 1.4442469
# ~200m north (far)
LAT_FAR = 43.6062622
LNG_FAR = 1.4442469


def _candidate(id, lat, lng, superficie):
    return {"id": id, "lat": lat, "lng": lng, "superficie": superficie}


# ---------------------------------------------------------------------------
# AC1: Positive match — GPS ≤ 50m AND area diff ≤ 10%
# ---------------------------------------------------------------------------
class TestPositiveMatch:
    def test_exact_same_position_same_area(self):
        candidates = [_candidate(42, LAT_A, LNG_A, 100.0)]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) == 42

    def test_nearby_position_area_within_threshold(self):
        # ~30m apart, area diff 5%
        candidates = [_candidate(7, LAT_B, LNG_B, 105.0)]
        result = matcher.find_match(LAT_A, LNG_A, 100.0, candidates)
        assert result == 7

    def test_returns_first_matching_candidate(self):
        candidates = [
            _candidate(1, LAT_FAR, LNG_FAR, 100.0),   # GPS too far
            _candidate(2, LAT_B, LNG_B, 100.0),        # matches
            _candidate(3, LAT_B, LNG_B, 100.0),        # also matches but second
        ]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) == 2

    def test_area_exactly_at_threshold(self):
        # 10% diff exactly → should match
        candidates = [_candidate(5, LAT_A, LNG_A, 110.0)]  # (110-100)/110 ≈ 0.0909 < 0.10
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) == 5

    def test_gps_near_threshold_should_match(self):
        # ~40m north (clearly within 50m threshold): Δlat ≈ 40/111320 ≈ 0.000359°
        lat_40m = LAT_A + 0.000359
        candidates = [_candidate(9, lat_40m, LNG_A, 100.0)]
        result = matcher.find_match(LAT_A, LNG_A, 100.0, candidates)
        assert result == 9


# ---------------------------------------------------------------------------
# AC2: NULL/malformed input — must return None without exception
# ---------------------------------------------------------------------------
class TestNullHandling:
    def test_lat_none(self):
        candidates = [_candidate(1, LAT_A, LNG_A, 100.0)]
        assert matcher.find_match(None, LNG_A, 100.0, candidates) is None

    def test_lng_none(self):
        candidates = [_candidate(1, LAT_A, LNG_A, 100.0)]
        assert matcher.find_match(LAT_A, None, 100.0, candidates) is None

    def test_area_none(self):
        candidates = [_candidate(1, LAT_A, LNG_A, 100.0)]
        assert matcher.find_match(LAT_A, LNG_A, None, candidates) is None

    def test_all_none(self):
        assert matcher.find_match(None, None, None, []) is None

    def test_lat_string_non_numeric(self):
        assert matcher.find_match("abc", LNG_A, 100.0, []) is None

    def test_area_string_non_numeric(self):
        assert matcher.find_match(LAT_A, LNG_A, "not_a_number", []) is None

    def test_lat_inf_returns_none(self):
        assert matcher.find_match(float("inf"), LNG_A, 100.0, []) is None

    def test_lng_nan_returns_none(self):
        assert matcher.find_match(LAT_A, float("nan"), 100.0, []) is None

    def test_candidate_inf_lat_skipped(self):
        candidates = [
            _candidate(1, float("inf"), LNG_A, 100.0),  # bad → skip
            _candidate(2, LAT_A, LNG_A, 100.0),         # good → match
        ]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) == 2

    def test_empty_candidates(self):
        assert matcher.find_match(LAT_A, LNG_A, 100.0, []) is None

    def test_candidate_missing_lat(self):
        candidates = [{"id": 1, "lng": LNG_A, "superficie": 100.0}]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) is None

    def test_candidate_missing_lng(self):
        candidates = [{"id": 1, "lat": LAT_A, "superficie": 100.0}]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) is None

    def test_candidate_missing_superficie(self):
        candidates = [{"id": 1, "lat": LAT_A, "lng": LNG_A}]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) is None

    def test_candidate_null_lat(self):
        candidates = [_candidate(1, None, LNG_A, 100.0)]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) is None

    def test_candidate_malformed_area(self):
        candidates = [_candidate(1, LAT_A, LNG_A, "bad")]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) is None

    def test_skip_bad_candidate_continue_to_good(self):
        candidates = [
            _candidate(1, None, LNG_A, 100.0),         # bad → skip
            _candidate(2, LAT_A, LNG_A, 100.0),        # good → match
        ]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) == 2

    def test_candidate_missing_id_skipped(self):
        candidates = [
            {"lat": LAT_A, "lng": LNG_A, "superficie": 100.0},  # no 'id' → skip
            _candidate(2, LAT_A, LNG_A, 100.0),                  # good → match
        ]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) == 2


# ---------------------------------------------------------------------------
# AC3: No match when thresholds exceeded
# ---------------------------------------------------------------------------
class TestNoMatch:
    def test_gps_too_far(self):
        # ~200m away
        candidates = [_candidate(1, LAT_FAR, LNG_FAR, 100.0)]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) is None

    def test_area_diff_too_large(self):
        # GPS close but area diff 20%
        candidates = [_candidate(1, LAT_A, LNG_A, 120.0)]  # (120-100)/120 ≈ 0.167 > 0.10
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) is None

    def test_gps_close_area_just_over_threshold(self):
        # area diff just over 10%: (111-100)/111 ≈ 0.099... wait let me calc properly
        # need (|a1-a2|)/max(a1,a2) > 0.10 → say area2=112: (112-100)/112 = 12/112 ≈ 0.107 > 0.10
        candidates = [_candidate(1, LAT_A, LNG_A, 112.0)]
        assert matcher.find_match(LAT_A, LNG_A, 100.0, candidates) is None


# ---------------------------------------------------------------------------
# AC4: Config constants present
# ---------------------------------------------------------------------------
class TestConfigConstants:
    def test_gps_threshold_present(self):
        assert hasattr(config, "GPS_MATCH_THRESHOLD_M")
        assert config.GPS_MATCH_THRESHOLD_M == 50

    def test_area_threshold_present(self):
        assert hasattr(config, "AREA_MATCH_THRESHOLD_PCT")
        assert config.AREA_MATCH_THRESHOLD_PCT == 0.10


# ---------------------------------------------------------------------------
# AC5: Import constraints (structural — validated via ast parse)
# ---------------------------------------------------------------------------
class TestImportConstraints:
    def test_matcher_importable_without_side_effects(self):
        import importlib
        mod = importlib.import_module("matcher")
        assert callable(mod.find_match)

    def test_haversine_private(self):
        assert callable(matcher._haversine)

    def test_no_forbidden_imports(self):
        import ast
        import pathlib
        src = (pathlib.Path(__file__).parent.parent / "matcher.py").read_text()
        tree = ast.parse(src)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module)
        for forbidden in ("sqlite3", "flask", "requests", "os", "sys"):
            assert forbidden not in imported, f"Forbidden import '{forbidden}' found in matcher.py"
        assert imported <= {"math", "config"}, f"Unexpected imports in matcher.py: {imported - {'math', 'config'}}"
