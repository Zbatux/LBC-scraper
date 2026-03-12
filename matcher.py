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


def find_similar(target: dict, candidates: list[dict]) -> list[dict]:
    """Return candidates within GPS radius and area tolerance of target, sorted by distance."""
    t_lat = target.get("lat")
    t_lng = target.get("lng")
    t_area = target.get("superficie")
    if t_lat is None or t_lng is None or t_area is None:
        return []
    try:
        t_lat = float(t_lat)
        t_lng = float(t_lng)
        t_area = float(t_area)
    except (TypeError, ValueError):
        return []
    if not (math.isfinite(t_lat) and math.isfinite(t_lng) and math.isfinite(t_area)):
        return []
    if t_area <= 0:
        return []

    t_id = target.get("id")
    results = []

    for cand in candidates:
        if cand.get("id") == t_id:
            continue
        c_lat = cand.get("lat")
        c_lng = cand.get("lng")
        c_area = cand.get("superficie")
        if c_lat is None or c_lng is None or c_area is None:
            continue
        try:
            c_lat = float(c_lat)
            c_lng = float(c_lng)
            c_area = float(c_area)
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(c_lat) and math.isfinite(c_lng) and math.isfinite(c_area)):
            continue
        if c_area <= 0:
            continue

        dist = _haversine(t_lat, t_lng, c_lat, c_lng)
        if dist > config.SIMILAR_GPS_RADIUS_M:
            continue

        max_area = max(t_area, c_area)
        if max_area > 0 and abs(t_area - c_area) / max_area <= config.SIMILAR_AREA_TOLERANCE_PCT:
            result = dict(cand)
            result["distance_m"] = round(dist)
            results.append(result)

    results.sort(key=lambda r: r["distance_m"])
    return results
