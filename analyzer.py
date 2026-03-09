import json
import re
import sqlite3

import ollama

OLLAMA_MODEL = "gemma3:12b"

ANALYZE_PROMPT = """
Tu es un assistant spécialisé dans l'analyse d'annonces immobilières françaises.
Analyse la description suivante d'un terrain et réponds UNIQUEMENT avec un objet JSON valide,
sans texte avant ou après, avec exactement ces 4 clés :

- "viabilise": détecte uniquement les terrains NON viabilisés pour éviter les faux positifs.
  Retourne 0 (non viabilisé) si la description contient l'un de ces indices négatifs :
  "non viabilisé", "sans viabilisation", "à viabiliser", "viabilisation à prévoir",
  "viabilisation non faite", "viabilisation en cours", "pas raccordé", "non raccordé",
  "assainissement individuel à créer", "assainissement à prévoir", "fosse septique à prévoir",
  "réseau non disponible", "pas de réseau", "aucun réseau", "travaux de viabilisation",
  "viabilisation à la charge", "à équiper", "sans raccordement".
  Retourne 1 (viabilisé) UNIQUEMENT si la description affirme EXPLICITEMENT et sans ambiguïté
  que le terrain EST déjà viabilisé, par exemple : "terrain viabilisé", "déjà viabilisé",
  "viabilisation faite", "entièrement viabilisé", "raccordé eau et électricité",
  "branchements effectués", "réseaux présents sur la parcelle", "borné et viabilisé".
  En cas de doute ou si rien n'est mentionné : retourne null.
  IMPORTANT : "constructible", "prêt à construire", "zone constructible" seuls ne suffisent PAS
  à conclure que le terrain est viabilisé — retourner null dans ce cas.
- "emprise_sol": le pourcentage d'emprise au sol mentionné dans l'annonce (ex: 20 pour 20%).
  Indices : "emprise au sol", "CES", "coefficient d'emprise", "emprise autorisée".
  Retourne 100.0 si aucune emprise au sol n'est mentionnée.
- "partiellement_constructible": 1 si une partie seulement du terrain est constructible.
  Indices : "partie constructible", "partiellement constructible", "zone mixte",
  "dont X m² constructibles", "constructible en partie", "constructibilité partielle".
  0 si entièrement constructible ou entièrement non constructible. null si inconnu.
- "partiellement_agricole": 1 si une partie du terrain est classée agricole ou zone A.
  Indices : "zone A", "partie agricole", "partiellement agricole", "section agricole",
  "zonage A", "zone naturelle", "zone N", "partie en zone A".
  0 sinon. null si inconnu.

Réponds UNIQUEMENT avec le JSON, sans explication, sans commentaire, sans balise markdown.
Exemple de réponse attendue : {"viabilise": 1, "emprise_sol": 20.0, "partiellement_constructible": 0, "partiellement_agricole": null}

Description :
"""


def analyze_description(description: str) -> dict | None:
    """Envoie la description au LLM local et retourne les champs structurés."""
    for attempt in range(2):
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": ANALYZE_PROMPT + description}],
                options={"temperature": 0},
            )
            content = response["message"]["content"].strip()
            # Extraction robuste du JSON même si le LLM ajoute du texte autour
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            continue
        except Exception as e:
            print(f"    ⚠ Ollama erreur (tentative {attempt+1}): {e}")
            if "Connection refused" in str(e) or "ConnectError" in str(e):
                print("    → Ollama n'est pas démarré. Lancez : ollama serve")
                return None
    return None


def analyze_all(db_name: str = "lbc_data.db"):
    """Analyse les descriptions non encore traitées via Ollama."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Migration : s'assurer que les colonnes IA existent
    for sql in [
        "ALTER TABLE annonces ADD COLUMN viabilise INTEGER",
        "ALTER TABLE annonces ADD COLUMN emprise_sol REAL",
        "ALTER TABLE annonces ADD COLUMN partiellement_constructible INTEGER",
        "ALTER TABLE annonces ADD COLUMN partiellement_agricole INTEGER",
        "ALTER TABLE annonces ADD COLUMN analyse_faite INTEGER DEFAULT 0",
    ]:
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.commit()

    cursor.execute(
        "SELECT id, titre, description FROM annonces "
        "WHERE description IS NOT NULL AND description != '' "
        "AND (analyse_faite IS NULL OR analyse_faite = 0 OR analyse_faite = '')"
    )
    todo = cursor.fetchall()
    conn.close()

    if not todo:
        print("  Aucune description à analyser (toutes déjà traitées ou manquantes).")
        return

    print(f"  {len(todo)} annonce(s) à analyser avec {OLLAMA_MODEL}...")
    updated = 0
    for i, (ad_id, titre, description) in enumerate(todo, 1):
        print(f"  [{i}/{len(todo)}] {titre[:55]}")
        result = analyze_description(description)
        if result is None:
            # Ollama indisponible → arrêt immédiat
            break

        conn = sqlite3.connect(db_name)
        conn.execute(
            """
            UPDATE annonces
            SET viabilise = ?,
                emprise_sol = ?,
                partiellement_constructible = ?,
                partiellement_agricole = ?,
                analyse_faite = 1
            WHERE id = ?
            """,
            (
                result.get("viabilise"),
                result.get("emprise_sol"),
                result.get("partiellement_constructible"),
                result.get("partiellement_agricole"),
                ad_id,
            ),
        )
        conn.commit()
        conn.close()
        updated += 1

    print(f"  ✓ {updated}/{len(todo)} annonces analysées.")
