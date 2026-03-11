"""
Serveur Flask — Interface web d'édition des annonces LBC.

Endpoints :
  GET  /                       → Sert l'UI (templates/index.html)
  GET  /api/annonces           → Retourne toutes les annonces en JSON
  DELETE /api/annonces         → Suppression bulk  { ids: [int, ...] }
  PATCH  /api/annonces/bulk    → Toggle bool bulk   { ids, field, value }
  PATCH  /api/annonces/<id>    → Mise à jour partielle d'une annonce

Seuls les champs de la EDITABLE_FIELDS whitelist sont modifiables
pour prévenir toute injection via nom de colonne.
"""

import os
import sqlite3

from flask import Flask, jsonify, render_template, request

DB_NAME = "lbc_data.db"

# Whitelist des colonnes éditables (protection contre l'injection de nom de colonne)
EDITABLE_FIELDS = {"note", "nogo", "viabilise", "partiellement_constructible", "partiellement_agricole"}

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Exécuté à l'import : garantit que les colonnes nogo/note existent

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_columns():
    """Garantit que les colonnes de migration existent (bases créées avant la migration)."""
    conn = get_db()
    for sql in [
        "ALTER TABLE annonces ADD COLUMN nogo INTEGER DEFAULT 0",
        "ALTER TABLE annonces ADD COLUMN note INTEGER",
        "ALTER TABLE annonces ADD COLUMN status TEXT",
        "ALTER TABLE annonces ADD COLUMN first_seen TEXT",
        "ALTER TABLE annonces ADD COLUMN date_publication TEXT",
    ]:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


# Appel immédiat à l'import pour migrer la base existante (ignoré si la base n'existe pas encore)
with app.app_context():
    if os.path.exists(DB_NAME):
        ensure_columns()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/annonces", methods=["GET"])
def get_annonces():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, titre, prix, superficie, prix_m2, trajet, lien, "
            "viabilise, emprise_sol, partiellement_constructible, partiellement_agricole, "
            "analyse_faite, nogo, note, "
            "status, first_seen, date_publication "
            "FROM annonces ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/annonces", methods=["DELETE"])
def delete_annonces():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids", [])
    if not ids or not all(isinstance(i, int) for i in ids):
        return jsonify({"error": "ids must be a non-empty list of integers"}), 400

    conn = get_db()
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM annonces WHERE id IN ({placeholders})", ids)
    conn.commit()
    deleted = conn.total_changes
    conn.close()
    return jsonify({"deleted": deleted})


@app.route("/api/annonces/bulk", methods=["PATCH"])
def bulk_update():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids", [])
    field = data.get("field")
    value = data.get("value")

    if not ids or not all(isinstance(i, int) for i in ids):
        return jsonify({"error": "ids must be a non-empty list of integers"}), 400
    if field not in EDITABLE_FIELDS:
        return jsonify({"error": f"field '{field}' is not editable"}), 400
    if value not in (0, 1):
        return jsonify({"error": "value must be 0 or 1"}), 400

    conn = get_db()
    placeholders = ",".join("?" * len(ids))
    # field is validated against whitelist — safe to interpolate
    conn.execute(
        f"UPDATE annonces SET {field} = ? WHERE id IN ({placeholders})",
        [value, *ids],
    )
    conn.commit()
    updated = conn.total_changes
    conn.close()
    return jsonify({"updated": updated})


@app.route("/api/annonces/<int:annonce_id>", methods=["PATCH"])
def update_annonce(annonce_id):
    data = request.get_json(silent=True) or {}
    updates = {k: v for k, v in data.items() if k in EDITABLE_FIELDS}
    if not updates:
        return jsonify({"error": "no editable fields provided"}), 400

    # Validate note range
    if "note" in updates:
        note = updates["note"]
        if note is not None and not (isinstance(note, int) and 1 <= note <= 10):
            return jsonify({"error": "note must be an integer between 1 and 10, or null"}), 400

    # Validate boolean fields
    for bool_field in EDITABLE_FIELDS - {"note"}:
        if bool_field in updates and updates[bool_field] not in (0, 1, None):
            return jsonify({"error": f"{bool_field} must be 0, 1, or null"}), 400

    conn = get_db()
    # fields are validated against whitelist — safe to interpolate
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE annonces SET {set_clause} WHERE id = ?",
        [*updates.values(), annonce_id],
    )
    conn.commit()
    conn.close()
    return jsonify({"updated": 1})


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
