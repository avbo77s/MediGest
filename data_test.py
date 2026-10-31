import json

from database import get_connection, creer_base, base_vide
from dao import UtilisateurDAO

MEDICAMENTS = [
    # désignation, famille, forme, prix, stock, seuil
    ("Amlodipine 5 mg",      "Antihypertenseurs",   "Comprimé", 48, 50, 15),
    ("Amoxicilline 1 g",     "Pénicillines",        "Comprimé", 38, 60, 20),
    ("Aspirine 100 mg",      "Antiagrégants",       "Comprimé", 15, 70, 20),
    ("Atorvastatine 20 mg",  "Statines",            "Comprimé", 70,  8, 15),   # sous le seuil
    ("Ibuprofène 400 mg",    "Anti-inflammatoires", "Comprimé", 22,  6, 15),   # sous le seuil
    ("Metformine 850 mg",    "Antidiabétiques",     "Comprimé", 28, 90, 25),
    ("Oméprazole 20 mg",     "Antiacides",          "Gélule",   45, 40, 15),
    ("Paracétamol 500 mg",   "Antalgiques",         "Comprimé", 12, 150, 40),
    ("Sirop antitussif",     "Antitussifs",         "Flacon",   30, 12, 10),
    ("Vitamine D3",          "Vitamines",           "Ampoule",  55, 25, 10),
]

PATIENTS = [
    # login, cin, nom, prénom, naissance, sexe, téléphone, allergies
    ("s.tazi",     "AB123456", "Tazi",     "Sara",   "1992-03-14", "F", "0612345678", None),
    ("n.fassi",    "EF345678", "Fassi",    "Nadia",  "2001-11-21", "F", "0670123456", None),
    ("o.berrada",  "GH901234", "Berrada",  "Omar",   "1978-01-09", "M", "0655987654", "Aspirine"),
    ("y.idrissi",  "CD789012", "Idrissi",  "Youssef", "1985-07-02", "M", "0661234567", "Pénicillines"),
    ("m.kabbaj",   "JK567890", "Kabbaj",   "Mehdi",  "1996-05-30", "M", "0662345678", None),
    ("h.chraibi",  "IJ567890", "Chraibi",  "Hajar",  "1969-05-30", "F", "0666543210", None),
]

POSO_PARACETAMOL = "1 prise, 3 fois par jour"

# Consultations honorées du Dr Alaoui :
# (date_heure, patient, motif, diagnostic, [(médicament, qté, posologie)], montant, mode, date de paiement)
HONORES_ALAOUI = [
    ("2026-05-27 09:00", "s.tazi",    "Fièvre", "Syndrome grippal",
     [("Paracétamol 500 mg", 2, POSO_PARACETAMOL)], 224, "Espèces", "2026-05-27"),
    ("2026-06-04 14:30", "n.fassi",   "Toux", "Bronchite",
     [("Sirop antitussif", 1, "2 cuillères, 3 fois par jour")], 230, "Carte", "2026-06-04"),
    ("2026-06-18 10:00", "y.idrissi", "Fatigue", "Carence en vitamine D",
     [("Vitamine D3", 1, "1 ampoule par semaine")], 255, "Espèces", "2026-06-18"),
    ("2026-07-06 14:00", "o.berrada", "Douleurs lombaires", "Lombalgie commune",
     [("Ibuprofène 400 mg", 2, "1 comprimé, 2 fois par jour")], 244, "Chèque", "2026-07-06"),
    ("2026-07-21 11:00", "m.kabbaj",  "Maux de tête", "Céphalée de tension",
     [("Paracétamol 500 mg", 1, POSO_PARACETAMOL)], 212, "Carte", "2026-07-21"),
    ("2026-08-13 09:00", "s.tazi",    "Contrôle", "RAS", [], 200, "Espèces", "2026-08-13"),
    ("2026-08-30 16:00", "n.fassi",   "Douleurs abdominales", "Gastrite",
     [("Oméprazole 20 mg", 1, "1 gélule le matin à jeun")], 245, "Carte", "2026-08-30"),
    ("2026-09-13 09:00", "y.idrissi", "Toux", "Bronchite",
     [("Sirop antitussif", 1, "2 cuillères, 3 fois par jour")], 230, "Espèces", "2026-09-13"),
    ("2026-10-04 14:30", "m.kabbaj",  "Fièvre", "Syndrome grippal",
     [("Paracétamol 500 mg", 2, POSO_PARACETAMOL)], 224, "Espèces", "2026-10-04"),
    ("2026-10-09 10:00", "s.tazi",    "Fatigue", "Anémie légère",
     [("Vitamine D3", 1, "1 ampoule par semaine")], 255, "Carte", "2026-10-09"),
    # facturée mais pas encore payée : 212 MAD d'impayés
    ("2026-10-15 09:00", "o.berrada", "Céphalée", "Céphalée de tension",
     [("Paracétamol 500 mg", 1, POSO_PARACETAMOL)], 212, None, None),
    # honorée mais pas encore facturée (« à facturer »)
    ("2026-10-20 11:00", "n.fassi",   "Rhinopharyngite", "Rhinopharyngite virale",
     [("Paracétamol 500 mg", 2, POSO_PARACETAMOL)], None, None, None),
]

# Autres rendez-vous du Dr Alaoui : (date_heure, patient, motif, statut)
AUTRES_ALAOUI = [
    ("2026-10-22 15:00", "m.kabbaj",  "Maux de tête",           "ANNULE"),
    ("2026-10-27 09:00", "s.tazi",    "Fièvre",                 "PLANIFIE"),
    ("2026-10-27 10:30", "y.idrissi", "Renouvellement ordonnance", "PLANIFIE"),
    ("2026-10-28 11:00", "n.fassi",   "Douleurs articulaires",  "PLANIFIE"),
    ("2026-10-30 14:30", "o.berrada", "Bilan annuel",           "DEMANDE"),
]

# Rendez-vous de la Dr Bennani (cardiologie)
HONORES_BENNANI = [
    ("2026-09-02 10:00", "h.chraibi", "Palpitations", "Extrasystoles bénignes",
     [], 300, "Carte", "2026-09-02"),
    ("2026-10-01 11:30", "h.chraibi", "Contrôle tension", "Hypertension équilibrée",
     [("Amlodipine 5 mg", 1, "1 comprimé le matin")], 348, "Carte", "2026-10-01"),
    ("2026-10-12 15:00", "o.berrada", "Bilan cardiaque", "RAS", [], 300, None, None),
]
AUTRES_BENNANI = [
    ("2026-10-29 10:00", "h.chraibi", "Suivi tension",          "PLANIFIE"),
    ("2026-11-03 09:30", "y.idrissi", "Douleurs thoraciques",   "DEMANDE"),
]


def charger(db):
    """Remplit une base vide avec le jeu d'essai. Retourne (comptes, médicaments, rendez-vous)."""
    utilisateurs = UtilisateurDAO(db)

    id_alaoui = utilisateurs.ajouter_medecin(
        "dr.alaoui", "medecin123", "A100200", "Alaoui", "Karim", "k.alaoui@alamal.ma",
        "0522000001", "Clinique Al Amal, Casablanca", "Médecine générale", 200)
    id_bennani = utilisateurs.ajouter_medecin(
        "dr.bennani", "medecin123", "B300400", "Bennani", "Salma", "s.bennani@alamal.ma",
        "0522000002", "Clinique Al Amal, Casablanca", "Cardiologie", 300)

    ids = {}
    for login, cin, nom, prenom, naissance, sexe, tel, allergies in PATIENTS:
        ids[login] = utilisateurs._creer_patient(
            login, "patient123", cin, nom, prenom, login.replace(".", "") + "@example.ma",
            tel, "Casablanca", naissance, sexe, allergies)

    with db:
        for designation, famille, forme, prix, stock, seuil in MEDICAMENTS:
            db.execute("""INSERT INTO medicament (designation, famille_med, forme, prix, stock, seuil)
                          VALUES (?, ?, ?, ?, ?, ?)""",
                       (designation, famille, forme, prix, stock, seuil))
    catalogue = {l["designation"]: l for l in
                 db.execute("SELECT * FROM medicament").fetchall()}

    def ordonnance_json(lignes):
        if not lignes:
            return None
        return json.dumps([{"id_med": catalogue[nom]["id_med"], "nom": nom, "qte": qte,
                            "posologie": poso, "prix": catalogue[nom]["prix"]}
                           for nom, qte, poso in lignes], ensure_ascii=False)

    def inserer_honores(id_medecin, liste):
        for date_heure, login, motif, diagnostic, lignes, montant, mode, date_pay in liste:
            paiement = "PAYE" if mode else "IMPAYE"
            db.execute("""INSERT INTO rendez_vous
                          (id_patient, id_medecin, date_heure, statut, motif, diagnostic,
                           ordonnance, montant, paiement, mode_paiement, date_paiement)
                          VALUES (?, ?, ?, 'HONORE', ?, ?, ?, ?, ?, ?, ?)""",
                       (ids[login], id_medecin, date_heure, motif, diagnostic,
                        ordonnance_json(lignes), montant, paiement, mode, date_pay))

    def inserer_autres(id_medecin, liste):
        for date_heure, login, motif, statut in liste:
            db.execute("""INSERT INTO rendez_vous (id_patient, id_medecin, date_heure, statut, motif)
                          VALUES (?, ?, ?, ?, ?)""",
                       (ids[login], id_medecin, date_heure, statut, motif))

    with db:
        inserer_honores(id_alaoui, HONORES_ALAOUI)
        inserer_autres(id_alaoui, AUTRES_ALAOUI)
        inserer_honores(id_bennani, HONORES_BENNANI)
        inserer_autres(id_bennani, AUTRES_BENNANI)

    return (2 + len(PATIENTS), len(MEDICAMENTS),
            len(HONORES_ALAOUI) + len(AUTRES_ALAOUI) + len(HONORES_BENNANI) + len(AUTRES_BENNANI))


if __name__ == "__main__":
    creer_base()
    connexion = get_connection()
    if base_vide(connexion):
        comptes, medicaments, rdv = charger(connexion)
        print("Jeu d'essai chargé : %d comptes, %d médicaments, %d rendez-vous."
              % (comptes, medicaments, rdv))
    else:
        print("La base contient déjà des données : rien n'a été chargé.")
    connexion.close()
