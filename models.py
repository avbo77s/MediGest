import datetime as dt #librarie de date car dans une tache jai besoin de la date d aujourhui  
class Personne :
    def __init__(self,id,login,nom,prenom,cin,telephone,email,adresse):
        self.id=id
        self.login=login
        self.nom=nom
        self.prenom=prenom
        self.cin=cin
        self.telephone=telephone
        self.email=email
        self.adresse=adresse
    def nom_complet(self,nom,prenom):
        return f"le nom complet est:{nom} {prenom}"
    def peut_ecrire(self):
        return False
#heritage
class Patient(Personne):
    def __init__(self,id,login,nom,prenom,cin,telephone,email,adresse,date_naissance,sexe,allergies,role):
        Personne.__init__(self,id,login,nom,prenom,cin,telephone,email,adresse)
        self.date_naissance=date_naissance
        self.sexe=sexe
        self.allergies=allergies
        self.role=role
        self.role="Patient"
    def age(self):
        aujourd_hui = dt.date.today()
        age = aujourd_hui.year - self.date_naissance.year
        if (aujourd_hui.month, aujourd_hui.day) < (
        self.date_naissance.month, self.date_naissance.day
        ):
            age -= 1

        return age
    def ecrans(self):
        return [
            f"""Mon Profil: 
            CIN:{self.cin}
            Nom: {self.nom}
            Prenom: {self.prenom}
            Sexe: {self.sexe}
            Role: {self.role}
            Telephone: {self.telephone}
            Email:{self.email}
            Adresse:{self.adresse}""",
            f"Mes rendez_vous:",
            f"Mes factures:",
            f"Mes ordonnaces:"
            ]
#heritage
class Medecin(Personne):
    def __init__(self,id,login,nom,prenom,cin,telephone,email,adresse,role,specialite,Tarif):
        Personne.__init__(self,id,login,nom,prenom,cin,telephone,email,adresse)
        self.role=role
        self.role="Medecin"
        self.specialite=specialite
        self.Tarif=Tarif
    def nom_complet(self, nom, prenom):
        return f"Dr.{prenom} {nom} "
    def peut_ecrire(self):
        return True
    def ecrans(self):
        return [f"""Mon Profil:
                CIN:{self.cin}
                Nom: {self.nom}
                Prenom: {self.prenom}
                Role: {self.role}
                Telephone: {self.telephone}
                Email:{self.email}
                Adresse:{self.adresse}""",
                "Mes clients:",
                "Rendez-vous",
                "Consultations",
                "Stock",
                "Facturation",
                "Tableau de bord",       
                ]

class RendezVous:
    def __init__(self,id,id_patient,id_medecin,date_heure,motif,statut="DEMANDE",actif=1):
        self.id=id
        self.id_patient=id_patient
        self.id_medecin=id_medecin
        self.date_heure=date_heure
        self.motif=motif
        self.statut=statut
        self.diagnostic = None
        self.ordonnance = None
        self.montant = None
        self.actif=actif

    def est_actif(self):
        if not self.actif:
            self.statut="ANNULE"
    def est_a_venir(self):
        return self.date_heure > dt.datetime.now()
    



            
class Medicament:
    def __init__(self,id,designation,famille,prix,stock,seuil):
        self.id=id
        self.designation=designation
        self.famille=famille
        self.prix=prix
        self.stock=stock
        self.seuil=seuil
    def en_alerte(self):
        return self.stock<=self.seuil
    def diponible(self,qte):
        return self.stock>=qte
class RegleMetier:
    pass


class LigneOrdonnance:
    def __init__(self, medicament, qte, prix):
        self.medicament = medicament
        self.id_med = medicament.id
        self.nom = medicament.designation
        self.qte = qte
        self.prix = prix
    def verifier_stock(self):
        return self.medicament.diponible(self.qte)

    def total(self):
        return self.qte * self.prix
class Ordonnance:
    def __init__(self):
        self.lignes = []
    def ajouter_ligne(self, ligne):
        if ligne.verifier_stock():
            self.lignes.append(ligne)
        else:
            raise ValueError("Stock insuffisant pour ce médicament.")
    def total(self):
        return sum(ligne.total() for ligne in self.lignes)    
med = Medicament(1, "Paracetamol", "Antalgique", 20, 10, 2)

ligne = LigneOrdonnance(med, 2, med.prix)

ordonnance = Ordonnance()
ordonnance.ajouter_ligne(ligne)

print("Total :", ordonnance.total())
print("Stock suffisant :", ligne.verifier_stock())
print("Alerte stock :", med.en_alerte())