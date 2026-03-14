import requests

from config import GEO_API_COMMUNES_URL, GPU_DOCUMENT_URL

_sess = requests.Session()
_sess.headers["User-Agent"] = "leboncoin-scraper/1.0"

_DOC_PRIORITY = ["PLUi", "PLU", "POS", "CC"]


def resolve_commune(lat=None, lon=None, commune=None):
    """Resolve commune INSEE code and name from GPS coords or commune name."""
    if lat is not None and lon is not None:
        params = {"lat": lat, "lon": lon, "fields": "nom,code", "limit": 1}
    elif commune:
        params = {"nom": commune, "fields": "nom,code", "limit": 1}
    else:
        raise ValueError("lat+lon or commune required")

    r = _sess.get(GEO_API_COMMUNES_URL, params=params, timeout=12)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError("Commune introuvable")
    return data[0]["code"], data[0]["nom"]


def find_active_plu(code_insee):
    """Find active PLU document for a commune, prioritising PLUi > PLU > POS > CC."""
    r = _sess.get(GPU_DOCUMENT_URL, params={"grid": code_insee}, timeout=12)
    r.raise_for_status()
    docs = r.json()

    active = [d for d in docs if d.get("status") == "document.production"]
    if not active:
        return None

    for doc_type in _DOC_PRIORITY:
        for doc in active:
            if doc.get("type") == doc_type:
                return doc
    return active[0]


def get_archive_url(document_id):
    """Fetch archive download URL for a PLU document."""
    r = _sess.get(f"{GPU_DOCUMENT_URL}/{document_id}/details", timeout=12)
    r.raise_for_status()
    return r.json().get("archiveUrl")


def get_plu_info(lat=None, lon=None, commune=None):
    """Orchestrate commune resolution → PLU lookup → archive URL."""
    try:
        code_insee, nom = resolve_commune(lat=lat, lon=lon, commune=commune)
    except ValueError:
        return {"error": "Commune introuvable"}
    except requests.RequestException as e:
        print(f"    PLU resolve_commune: {e}")
        return {"error": "Erreur lors de la communication avec les APIs d'urbanisme"}

    try:
        document = find_active_plu(code_insee)
    except requests.RequestException as e:
        print(f"    PLU find_active_plu: {e}")
        return {"error": "Erreur lors de la communication avec les APIs d'urbanisme"}

    if document is None:
        return {"error": "Aucun PLU trouvé pour cette commune (commune au RNU)"}

    try:
        archive_url = get_archive_url(document["id"])
    except requests.RequestException as e:
        print(f"    PLU get_archive_url: {e}")
        return {"error": "Erreur lors de la communication avec les APIs d'urbanisme"}

    if not archive_url or not archive_url.startswith("https://"):
        return {"error": "Archive PLU non disponible pour ce document"}

    return {
        "commune": nom.upper(),
        "code_insee": code_insee,
        "type": document["type"],
        "date_approbation": document.get("datApprobation"),
        "date_publication": document.get("datPublication"),
        "archive_url": archive_url,
    }
