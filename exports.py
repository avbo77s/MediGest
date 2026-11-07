
# Fonctions pour exporter les factures en CSV et ouvrir les documents HTML
import csv
import tempfile
import webbrowser
from pathlib import Path
from datetime import datetime


def exporter_csv(lignes):
    # Exporte la liste des lignes dans un fichier CSV avec séparateur point-virgule pour Excel
    if not lignes:
        raise ValueError("Aucune donnée à exporter.")

    colonnes = lignes[0].keys()
    nom_fichier = "export_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
    chemin = Path.cwd() / nom_fichier

    with open(chemin, "w", newline="", encoding="utf-8-sig") as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(colonnes)
        for ligne in lignes:
            writer.writerow([ligne[colonne] for colonne in colonnes])

    return str(chemin)


def ouvrir_dans_navigateur(contenu_html):
    # Crée un fichier temporaire HTML et l'ouvre directement dans le navigateur pour impression
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".html",
        encoding="utf-8",
        delete=False
    ) as fichier:
        fichier.write(contenu_html)
        chemin = fichier.name

    webbrowser.open(Path(chemin).as_uri())
    return chemin
