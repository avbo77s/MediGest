
import csv
import tempfile
import webbrowser
from pathlib import Path
from datetime import datetime


def exporter_csv(lignes):
    """Exporte une liste de lignes dans un fichier CSV."""

    if not lignes:
        raise ValueError("Aucune donnée à exporter.")

    # Récupérer les noms des colonnes
    colonnes = lignes[0].keys()

    # Créer un nom de fichier avec la date et l'heure
    nom_fichier = "export_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"

    chemin = Path.cwd() / nom_fichier

    # Écrire les données dans le fichier CSV
    with open(chemin, "w", newline="", encoding="utf-8-sig") as fichier:
        writer = csv.writer(fichier, delimiter=";")

        writer.writerow(colonnes)

        for ligne in lignes:
            writer.writerow([ligne[colonne] for colonne in colonnes])

    return str(chemin)


def ouvrir_dans_navigateur(contenu_html):
    """Crée un fichier HTML temporaire et l'ouvre dans le navigateur."""

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
