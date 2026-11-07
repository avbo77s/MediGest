
# Classes d'accès aux données (DAO) pour communiquer avec la base SQLite
import sqlite3

from security import hash_password, verifier_mot_de_passe



# 1. UTILISATEUR DAO /////////////////////


class UtilisateurDAO:

    def __init__(self, db):
        self.db = db

    # Chercher un utilisateur par login
    

    def chercher_par_login(self, login):

        curseur = self.db.execute(
            """
            SELECT * FROM Users
            WHERE login = ?
            """,
            (login,)
        )

        return curseur.fetchone()

  
    # Chercher un utilisateur par ID
   

    def chercher_par_id(self, id_user):

        curseur = self.db.execute(
            """
            SELECT * FROM Users
            WHERE id_user = ?
            """,
            (id_user,)
        )

        return curseur.fetchone()

   
    # Ajouter un patient
    

    def ajouter_patient(
        self, login, mot_de_passe, cin, nom, prenom,
        email, telephone, adresse, date_naissance,
        sexe=None, allergies=None
    ):

        mot_de_passe_hash = hash_password(mot_de_passe)

        try:
            curseur = self.db.execute(
                """
                INSERT INTO Users (
                    login, mot_de_passe_hash, role,
                    cin, nom, prenom, email, telephone,
                    adresse, date_naissance, sexe, allergies
                )
                VALUES (?, ?, 'patient', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    login, mot_de_passe_hash, cin, nom, prenom,
                    email, telephone, adresse, date_naissance,
                    sexe, allergies
                )
            )

            self.db.commit()
            return curseur.lastrowid

        except sqlite3.IntegrityError as erreur:
            self.db.rollback()
            raise ValueError(f"Erreur lors de l'inscription : {erreur}")

   
    # Ajouter un médecin
   

    def ajouter_medecin(
        self, login, mot_de_passe, cin, nom, prenom,
        email, telephone, adresse, specialite, tarif
    ):

        mot_de_passe_hash = hash_password(mot_de_passe)

        try:
            curseur = self.db.execute(
                """
                INSERT INTO Users (
                    login, mot_de_passe_hash, role,
                    cin, nom, prenom, email, telephone,
                    adresse, specialite, tarif
                )
                VALUES (?, ?, 'medecin', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    login, mot_de_passe_hash, cin, nom, prenom,
                    email, telephone, adresse, specialite, tarif
                )
            )

            self.db.commit()
            return curseur.lastrowid

        except sqlite3.IntegrityError as erreur:
            self.db.rollback()
            raise ValueError(f"Erreur lors de l'ajout du médecin : {erreur}")

   
    # Authentification
   

    def authentifier(self, login, mot_de_passe):

        utilisateur = self.chercher_par_login(login)

        if utilisateur is None:
            return None

        if utilisateur["actif"] == 0:
            return None

        if verifier_mot_de_passe(
            mot_de_passe,
            utilisateur["mot_de_passe_hash"]
        ):
            return utilisateur

        return None

   
    # Afficher tous les patients
   

    def afficher_patients(self):

        curseur = self.db.execute(
            """
            SELECT * FROM Users
            WHERE lower(role) = 'patient'
            ORDER BY nom
            """
        )

        return curseur.fetchall()

   
    # Afficher tous les médecins
   

    def afficher_medecins(self):

        curseur = self.db.execute(
            """
            SELECT * FROM Users
            WHERE lower(role) = 'medecin'
            ORDER BY nom
            """
        )

        return curseur.fetchall()

   
    # Modifier les informations utilisateur
   

    def modifier_utilisateur(self, id_user, **donnees):

        colonnes_autorisees = [
            "nom", "prenom", "telephone",
            "email", "adresse", "date_naissance",
            "sexe", "allergies", "specialite", "tarif"
        ]

        modifications = {
            cle: valeur
            for cle, valeur in donnees.items()
            if cle in colonnes_autorisees
        }

        if not modifications:
            return False

        champs = ", ".join(
            f"{cle} = ?" for cle in modifications
        )

        valeurs = list(modifications.values())
        valeurs.append(id_user)

        try:
            curseur = self.db.execute(
                f"""
                UPDATE Users
                SET {champs}
                WHERE id_user = ?
                """,
                valeurs
            )

            self.db.commit()
            return curseur.rowcount > 0

        except sqlite3.IntegrityError as erreur:
            self.db.rollback()
            raise ValueError(f"Modification impossible : {erreur}")

   
    # Désactiver un compte
   

    def desactiver_utilisateur(self, id_user):

        curseur = self.db.execute(
            """
            UPDATE Users
            SET actif = 0
            WHERE id_user = ?
            """,
            (id_user,)
        )

        self.db.commit()
        return curseur.rowcount > 0

   
    # Réactiver un compte
   

    def reactiver_utilisateur(self, id_user):

        curseur = self.db.execute(
            """
            UPDATE Users
            SET actif = 1
            WHERE id_user = ?
            """,
            (id_user,)
        )

        self.db.commit()
        return curseur.rowcount > 0

   
    # Supprimer un utilisateur
   

    def supprimer_utilisateur(self, id_user):

        try:
            curseur = self.db.execute(
                """
                DELETE FROM Users
                WHERE id_user = ?
                """,
                (id_user,)
            )

            self.db.commit()
            return curseur.rowcount > 0

        except sqlite3.IntegrityError:
            self.db.rollback()
            raise ValueError(
                "Impossible de supprimer cet utilisateur : "
                "il possède des rendez-vous associés."
            )

   
    # Changer le mot de passe
   

    def changer_mot_de_passe(
        self, id_user, ancien_mot_de_passe, nouveau_mot_de_passe
    ):

        utilisateur = self.chercher_par_id(id_user)

        if utilisateur is None:
            return False

        if not verifier_mot_de_passe(
            ancien_mot_de_passe,
            utilisateur["mot_de_passe_hash"]
        ):
            return False

        nouveau_hash = hash_password(nouveau_mot_de_passe)

        self.db.execute(
            """
            UPDATE Users
            SET mot_de_passe_hash = ?
            WHERE id_user = ?
            """,
            (nouveau_hash, id_user)
        )

        self.db.commit()
        return True


# =====================================================
# 2. RENDEZ-VOUS DAO
# =====================================================

class RendezVousDAO:

    def __init__(self, db):
        self.db = db

   
    # Ajouter un rendez-vous
   

    def ajouter_rdv(
        self, id_patient, id_medecin,
        date_heure, motif
    ):

        try:
            curseur = self.db.execute(
                """
                INSERT INTO rendez_vous (
                    id_patient, id_medecin,
                    date_heure, motif
                )
                VALUES (?, ?, ?, ?)
                """,
                (id_patient, id_medecin, date_heure, motif)
            )

            self.db.commit()
            return curseur.lastrowid

        except sqlite3.IntegrityError as erreur:
            self.db.rollback()
            raise ValueError(f"Impossible de créer le rendez-vous : {erreur}")

   
    # Chercher un rendez-vous par ID
   

    def chercher_par_id(self, id_rendezvous):

        curseur = self.db.execute(
            """
            SELECT * FROM rendez_vous
            WHERE id_rendezvous = ?
            """,
            (id_rendezvous,)
        )

        return curseur.fetchone()

   
    # Afficher tous les rendez-vous
   

    def afficher_tous(self):

        curseur = self.db.execute(
            """
            SELECT
                r.*,
                p.nom AS nom_patient,
                p.prenom AS prenom_patient,
                m.nom AS nom_medecin,
                m.prenom AS prenom_medecin
            FROM rendez_vous r
            JOIN Users p ON r.id_patient = p.id_user
            JOIN Users m ON r.id_medecin = m.id_user
            ORDER BY r.date_heure
            """
        )

        return curseur.fetchall()

   
    # Rendez-vous d'un patient
   

    def afficher_par_patient(self, id_patient):

        curseur = self.db.execute(
            """
            SELECT
                r.*,
                m.nom AS nom_medecin,
                m.prenom AS prenom_medecin
            FROM rendez_vous r
            JOIN Users m ON r.id_medecin = m.id_user
            WHERE r.id_patient = ?
            ORDER BY r.date_heure DESC
            """,
            (id_patient,)
        )

        return curseur.fetchall()

   
    # Rendez-vous d'un médecin
   

    def afficher_par_medecin(self, id_medecin):

        curseur = self.db.execute(
            """
            SELECT
                r.*,
                p.nom AS nom_patient,
                p.prenom AS prenom_patient
            FROM rendez_vous r
            JOIN Users p ON r.id_patient = p.id_user
            WHERE r.id_medecin = ?
            ORDER BY r.date_heure
            """,
            (id_medecin,)
        )

        return curseur.fetchall()

   
    # Modifier le statut
   

    def modifier_statut(self, id_rendezvous, nouveau_statut):

        statuts = [
            "DEMANDE", "PLANIFIE", "HONORE", "ANNULE"
        ]

        if nouveau_statut not in statuts:
            raise ValueError("Statut invalide.")

        curseur = self.db.execute(
            """
            UPDATE rendez_vous
            SET statut = ?
            WHERE id_rendezvous = ?
            """,
            (nouveau_statut, id_rendezvous)
        )

        self.db.commit()
        return curseur.rowcount > 0

   
    # Annuler un rendez-vous
   

    def annuler_rdv(self, id_rendezvous):

        return self.modifier_statut(
            id_rendezvous, "ANNULE"
        )

   
    # Enregistrer une consultation
   

    def enregistrer_consultation(
        self, id_rendezvous, diagnostic,
        ordonnance=None, montant=None
    ):

        curseur = self.db.execute(
            """
            UPDATE rendez_vous
            SET diagnostic = ?,
                ordonnance = ?,
                montant = ?,
                statut = 'HONORE'
            WHERE id_rendezvous = ?
            """,
            (
                diagnostic,
                ordonnance,
                montant,
                id_rendezvous
            )
        )

        self.db.commit()
        return curseur.rowcount > 0

   
    # Enregistrer un paiement
   

    def enregistrer_paiement(
        self, id_rendezvous, mode_paiement, date_paiement
    ):

        curseur = self.db.execute(
            """
            UPDATE rendez_vous
            SET paiement = 'paye',
                mode_paiement = ?,
                date_paiement = ?
            WHERE id_rendezvous = ?
            """,
            (
                mode_paiement,
                date_paiement,
                id_rendezvous
            )
        )

        self.db.commit()
        return curseur.rowcount > 0


# =====================================================
# 3. MEDICAMENT DAO
# =====================================================

class MedicamentDAO:

    def __init__(self, db):
        self.db = db

   
    # Ajouter un médicament
   

    def ajouter_medicament(
        self, designation, famille_med,
        forme, prix, stock, seuil
    ):

        try:
            curseur = self.db.execute(
                """
                INSERT INTO medicament (
                    designation, famille_med,
                    forme, prix, stock, seuil
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    designation, famille_med,
                    forme, prix, stock, seuil
                )
            )

            self.db.commit()
            return curseur.lastrowid

        except sqlite3.IntegrityError as erreur:
            self.db.rollback()
            raise ValueError(f"Erreur médicament : {erreur}")

   
    # Afficher tous les médicaments
   

    def afficher_medicaments(self):

        curseur = self.db.execute(
            """
            SELECT * FROM medicament
            ORDER BY designation
            """
        )

        return curseur.fetchall()

   
    # Chercher un médicament par ID
   

    def chercher_par_id(self, id_med):

        curseur = self.db.execute(
            """
            SELECT * FROM medicament
            WHERE id_med = ?
            """,
            (id_med,)
        )

        return curseur.fetchone()

   
    # Modifier un médicament
   

    def modifier_medicament(
        self, id_med, designation, famille_med,
        forme, prix, seuil
    ):

        try:
            curseur = self.db.execute(
                """
                UPDATE medicament
                SET designation = ?,
                    famille_med = ?,
                    forme = ?,
                    prix = ?,
                    seuil = ?
                WHERE id_med = ?
                """,
                (
                    designation, famille_med,
                    forme, prix, seuil, id_med
                )
            )

            self.db.commit()
            return curseur.rowcount > 0

        except sqlite3.IntegrityError as erreur:
            self.db.rollback()
            raise ValueError(f"Modification impossible : {erreur}")

   
    # Supprimer un médicament
   

    def supprimer_medicament(self, id_med):

        curseur = self.db.execute(
            """
            DELETE FROM medicament
            WHERE id_med = ?
            """,
            (id_med,)
        )

        self.db.commit()
        return curseur.rowcount > 0

   
    # Modifier la quantité en stock
   

    def modifier_stock(self, id_med, nouvelle_quantite):

        if nouvelle_quantite < 0:
            raise ValueError("Le stock ne peut pas être négatif.")

        curseur = self.db.execute(
            """
            UPDATE medicament
            SET stock = ?
            WHERE id_med = ?
            """,
            (nouvelle_quantite, id_med)
        )

        self.db.commit()
        return curseur.rowcount > 0

   
    # Vérifier la disponibilité
   

    def verifier_stock(self, id_med, quantite):

        medicament = self.chercher_par_id(id_med)

        if medicament is None:
            return False

        return medicament["stock"] >= quantite

   
    # Médicaments en alerte
   

    def medicaments_en_alerte(self):

        curseur = self.db.execute(
            """
            SELECT * FROM medicament
            WHERE stock <= seuil
            ORDER BY stock
            """
        )

        return curseur.fetchall()


# =====================================================
# 4. STATISTIQUES DAO
# =====================================================

class StatistiquesDAO:

    def __init__(self, db):
        self.db = db

   
    # Nombre de patients
   

    def nombre_patients(self):

        curseur = self.db.execute(
            """
            SELECT COUNT(*) FROM Users
            WHERE lower(role) = 'patient'
            AND actif = 1
            """
        )

        return curseur.fetchone()[0]

   
    # Nombre de médecins
   

    def nombre_medecins(self):

        curseur = self.db.execute(
            """
            SELECT COUNT(*) FROM Users
            WHERE lower(role) = 'medecin'
            AND actif = 1
            """
        )

        return curseur.fetchone()[0]

   
    # Nombre de rendez-vous
   

    def nombre_rdv(self):

        curseur = self.db.execute(
            """
            SELECT COUNT(*) FROM rendez_vous
            """
        )

        return curseur.fetchone()[0]

   
    # Rendez-vous aujourd'hui
   

    def rdv_aujourdhui(self):

        curseur = self.db.execute(
            """
            SELECT COUNT(*) FROM rendez_vous
            WHERE date(date_heure) = date('now', 'localtime')
            """
        )

        return curseur.fetchone()[0]

   
    # Chiffre d'affaires
   

    def chiffre_affaires(self):

        curseur = self.db.execute(
            """
            SELECT COALESCE(SUM(montant), 0)
            FROM rendez_vous
            WHERE lower(paiement) = 'paye'
            """
        )

        return curseur.fetchone()[0]

   
    # Nombre de médicaments en alerte
   

    def stock_en_alerte(self):

        curseur = self.db.execute(
            """
            SELECT COUNT(*) FROM medicament
            WHERE stock <= seuil
            """
        )

        return curseur.fetchone()[0]

   
    # Résumé du tableau de bord
   

    def resume_accueil(self, utilisateur=None):

        return {
            "nombre_patients": self.nombre_patients(),
            "nombre_medecins": self.nombre_medecins(),
            "nombre_rdv": self.nombre_rdv(),
            "rdv_aujourdhui": self.rdv_aujourdhui(),
            "chiffre_affaires": self.chiffre_affaires(),
            "stock_en_alerte": self.stock_en_alerte()
        }
