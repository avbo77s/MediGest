# Classes modèles pour représenter les objets du domaine médical
import datetime as dt

# Classe de base pour représenter une personne
class Personne:
    def __init__(self, id, login, nom, prenom, cin, telephone, email, adresse):
        self.id = id
        self.login = login
        self.nom = nom
        self.prenom = prenom
        self.cin = cin
        self.telephone = telephone
        self.email = email
        self.adresse = adresse

    def nom_complet(self, nom=None, prenom=None):
        n = nom if nom is not None else self.nom
        p = prenom if prenom is not None else self.prenom
        return f"{p} {str(n).upper()}"

    def peut_ecrire(self):
        # Par défaut, pas de droit d'écriture médicale
        return False


# Classe Patient qui hérite de Personne
class Patient(Personne):
    def __init__(self, id, login, nom, prenom, cin, telephone, email, adresse, date_naissance, sexe, allergies, role="Patient"):
        super().__init__(id, login, nom, prenom, cin, telephone, email, adresse)
        self.date_naissance = date_naissance
        self.sexe = sexe
        self.allergies = allergies
        self.role = "patient"

    def age(self):
        # Calcule l'âge à partir de la date de naissance
        if not self.date_naissance:
            return 0
        aujourd_hui = dt.date.today()
        d = self.date_naissance if isinstance(self.date_naissance, dt.date) else dt.datetime.strptime(str(self.date_naissance)[:10], "%Y-%m-%d").date()
        age = aujourd_hui.year - d.year
        if (aujourd_hui.month, aujourd_hui.day) < (d.month, d.day):
            age -= 1
        return age

    def ecrans(self):
        # Liste des 4 écrans autorisés pour un patient
        return ["Mes rendez-vous", "Mes ordonnances", "Mes factures", "Mon profil"]


# Classe Médecin qui hérite de Personne
class Medecin(Personne):
    def __init__(self, id, login, nom, prenom, cin, telephone, email, adresse, role="Medecin", specialite="Médecine générale", Tarif=200):
        super().__init__(id, login, nom, prenom, cin, telephone, email, adresse)
        self.role = "medecin"
        self.specialite = specialite
        self.Tarif = Tarif
        self.tarif = Tarif

    def nom_complet(self, nom=None, prenom=None):
        n = nom if nom is not None else self.nom
        p = prenom if prenom is not None else self.prenom
        return f"Dr {p} {str(n).upper()}"

    def peut_ecrire(self):
        # Le médecin a le droit de prescrire et créer des consultations
        return True

    def ecrans(self):
        # Liste des 7 écrans autorisés pour un médecin
        return ["Patients", "Rendez-vous", "Consultations", "Stock", "Facturation", "Tableau de bord", "Mon profil"]


# Classe représentant un rendez-vous
class RendezVous:
    def __init__(self, id, id_patient, id_medecin, date_heure, motif, statut="DEMANDE", actif=1):
        self.id = id
        self.id_patient = id_patient
        self.id_medecin = id_medecin
        self.date_heure = date_heure
        self.motif = motif
        self.statut = statut
        self.diagnostic = None
        self.ordonnance = None
        self.montant = None
        self.actif = actif

    def est_actif(self):
        if not self.actif:
            self.statut = "ANNULE"

    def est_a_venir(self):
        return self.date_heure > dt.datetime.now()


# Classe représentant un médicament en stock
class Medicament:
    def __init__(self, id, designation, famille, prix, stock, seuil):
        self.id = id
        self.designation = designation
        self.famille = famille
        self.prix = prix
        self.stock = stock
        self.seuil = seuil

    def en_alerte(self):
        # Vérifie si le stock est inférieur ou égal au seuil de sécurité
        return self.stock <= self.seuil

    def diponible(self, qte):
        return self.stock >= qte


# Exception personnalisée pour les erreurs de règles métier (rendez-vous en doublon, stock insuffisant, etc.)
class RegleMetier(Exception):
    pass


# Ligne dans une ordonnance associant un médicament et sa posologie
class LigneOrdonnance:
    def __init__(self, medicament, qte, prix, posologie=""):
        self.medicament = medicament
        self.id_med = getattr(medicament, "id", None)
        self.nom = getattr(medicament, "designation", str(medicament))
        self.qte = qte
        self.prix = prix
        self.posologie = posologie

    def verifier_stock(self):
        if hasattr(self.medicament, "diponible"):
            return self.medicament.diponible(self.qte)
        return True

    def total(self):
        return self.qte * self.prix


# Ordonnance regroupant plusieurs lignes de médicaments
class Ordonnance:
    def __init__(self):
        self.lignes = []

    def ajouter_ligne(self, ligne):
        if ligne.verifier_stock():
            self.lignes.append(ligne)
        else:
            raise RegleMetier("Stock insuffisant pour ce médicament.")

    def total(self):
        return sum(ligne.total() for ligne in self.lignes)


if __name__ == "__main__":
    # Test simple du modèle
    med = Medicament(1, "Paracetamol", "Antalgique", 20, 10, 2)
    ligne = LigneOrdonnance(med, 2, med.prix, "1 prise matin et soir")
    ord = Ordonnance()
    ord.ajouter_ligne(ligne)
    print("Test models.py OK - Total ordonnance :", ord.total())
