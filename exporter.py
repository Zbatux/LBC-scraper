import csv
import sqlite3


def export_to_csv(db_name="lbc_data.db", csv_file="output.csv"):
    """Exporte les données de la base SQLite vers un fichier CSV."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT titre, prix, superficie, prix_m2, trajet, lien, "
        "viabilise, emprise_sol, partiellement_constructible, partiellement_agricole, "
        "nogo, note "
        "FROM annonces"
    )
    rows = cursor.fetchall()
    conn.close()

    def fmt(val):
        """Formate un nombre en remplaçant le point décimal par une virgule."""
        if val is None:
            return ""
        if isinstance(val, float):
            return str(val).replace(".", ",")
        return val

    def fmt_bool(val):
        """Formate un booléen SQLite (0/1/None) en texte lisible."""
        if val is None:
            return ""
        return "Oui" if val == 1 else "Non"

    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow([
            "Titre", "Prix (€)", "Superficie (m²)", "Prix au m² (€/m²)",
            "Temps trajet Toulouse", "Lien",
            "Viabilisé", "Emprise au sol (%)", "Partiellement constructible", "Partiellement agricole",
            "Nogo", "Note",
        ])
        for row in rows:
            titre, prix, superficie, prix_m2, trajet, lien, viab, emprise, constr, agri, nogo, note = row
            writer.writerow([
                fmt(titre), fmt(prix), fmt(superficie), fmt(prix_m2),
                fmt(trajet), fmt(lien),
                fmt_bool(viab), fmt(emprise), fmt_bool(constr), fmt_bool(agri),
                fmt_bool(nogo), fmt(note),
            ])

    print(f"Données exportées vers le fichier {csv_file}.")
