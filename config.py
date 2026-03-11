TOULOUSE_LAT = 43.6044622
TOULOUSE_LNG = 1.4442469

SEARCH_URL = (
    "https://www.leboncoin.fr/recherche"
    "?category=9"
    "&text=constructible%20-%22non%20constructible%22%20-%22pas%20constructible%22"
    "&lat=43.6404224&lng=1.4548992&radius=100000"
    "&price=1000-50000"
    "&real_estate_type=3"
    "&owner_type=all"
    "&sort=time&order=desc"
)

MAX_PAGES = 30  # ~35 annonces/page → 30 pages = 1050 annonces max

GPS_MATCH_THRESHOLD_M = 50         # metres — fuzzy GPS proximity threshold
AREA_MATCH_THRESHOLD_PCT = 0.10    # 10% — relative area difference threshold
