# Fonctions pour manipuler les dates du jour et heures
from datetime import date, datetime


def aujourdhui():
    # Donne la date d'aujourd'hui au format texte AAAA-MM-JJ
    return date.today().strftime("%Y-%m-%d")


def maintenant():
    # Donne la date et l'heure actuelles (ex: 2026-11-02 14:30)
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def convertir_date(texte):
    # Transforme une date texte en objet date Python
    return datetime.strptime(texte, "%Y-%m-%d").date()
