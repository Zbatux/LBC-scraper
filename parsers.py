import re


def get_attr(ad: dict, key: str) -> str | None:
    for a in ad.get("attributes", []):
        if a.get("key") == key:
            return a.get("value_label") or str(a.get("value", ""))
    return None


def parse_price(ad: dict) -> float | None:
    p = ad.get("price")
    if isinstance(p, list) and p:
        return float(p[0])
    if isinstance(p, (int, float)):
        return float(p)
    return None


def parse_area(ad: dict) -> float | None:
    for key in ("square", "land_surface", "surface"):
        val = get_attr(ad, key)
        if val:
            n = re.sub(r"[^\d.,]", "", val).replace(",", ".")
            try:
                return float(n)
            except ValueError:
                pass
    for text in (ad.get("subject", ""), ad.get("body", "")):
        m = re.search(r"(\d[\d\s]*)\s*m[²2]", text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(" ", ""))
            except ValueError:
                pass
    return None


def get_coords(ad: dict) -> tuple:
    loc = ad.get("location", {})
    return loc.get("lat"), loc.get("lng")


def build_url(ad: dict) -> str:
    return f"https://www.leboncoin.fr/ad/ventes_immobilieres/{ad.get('list_id', '')}"
