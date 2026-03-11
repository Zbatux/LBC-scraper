import math
import config

EARTH_RADIUS_M = 6_371_000  # metres


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in metres between two GPS points."""
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def find_match(lat: float, lng: float, area: float, candidates: list[dict]) -> int | None:
    """Returns annonce_id of matched candidate, or None if no match / missing data."""
    if lat is None or lng is None or area is None:
        return None
    try:
        lat = float(lat)
        lng = float(lng)
        area = float(area)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lng) and math.isfinite(area)):
        return None

    for candidate in candidates:
        c_id = candidate.get("id")
        c_lat = candidate.get("lat")
        c_lng = candidate.get("lng")
        c_area = candidate.get("superficie")
        if c_id is None or c_lat is None or c_lng is None or c_area is None:
            continue
        try:
            c_lat = float(c_lat)
            c_lng = float(c_lng)
            c_area = float(c_area)
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(c_lat) and math.isfinite(c_lng) and math.isfinite(c_area)):
            continue

        if _haversine(lat, lng, c_lat, c_lng) <= config.GPS_MATCH_THRESHOLD_M:
            max_area = max(area, c_area)
            if max_area > 0 and abs(area - c_area) / max_area <= config.AREA_MATCH_THRESHOLD_PCT:
                return c_id

    return None
