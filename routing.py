import requests

from config import TOULOUSE_LAT, TOULOUSE_LNG

_sess = requests.Session()
_sess.headers["User-Agent"] = "leboncoin-scraper/1.0"


def drive_time(lat: float, lng: float) -> str:
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{lng},{lat};{TOULOUSE_LNG},{TOULOUSE_LAT}?overview=false"
    )
    try:
        r = _sess.get(url, timeout=12)
        d = r.json()
        if d.get("code") == "Ok":
            secs = d["routes"][0]["duration"]
            h, m = divmod(int(secs // 60), 60)
            return f"{h}h {m:02d}min" if h else f"{m}min"
    except Exception as e:
        print(f"    OSRM: {e}")
    return "N/A"
