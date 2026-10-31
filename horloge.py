
from datetime import date, datetime

def aujourdhui():
    """Retourne la date actuelle au format AAAA-MM-JJ."""
    return date.today().strftime("%Y-%m-%d")


def maintenant():
    """Retourne la date et l'heure actuelles."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def convertir_date(texte):
    """Convertit une date AAAA-MM-JJ en objet date."""
    return datetime.strptime(texte, "%Y-%m-%d").date()
