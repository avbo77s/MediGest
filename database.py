
import sqlite3


def creer_base():

    db = sqlite3.connect("MediGest.db")
    db.execute("PRAGMA foreign_keys = ON")

    cursor = db.cursor()

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS Users (
            id_user INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            mot_de_passe_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (lower(role) IN ('medecin','patient')),
            cin TEXT NOT NULL UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            telephone TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            adresse TEXT,
            actif INTEGER NOT NULL DEFAULT 1 CHECK (actif IN (0, 1)),
            date_naissance TEXT,
            sexe TEXT CHECK (sexe IS NULL OR lower(sexe) IN ('m','f')),
            allergies TEXT,
            specialite TEXT,
            tarif REAL CHECK (tarif IS NULL OR tarif >= 0),

            CHECK (
                (lower(role) = 'medecin'
                 AND specialite IS NOT NULL
                 AND tarif IS NOT NULL)
                OR
                (lower(role) = 'patient'
                 AND date_naissance IS NOT NULL
                 AND tarif IS NULL)
            )
        );

        CREATE TABLE IF NOT EXISTS rendez_vous (
            id_rendezvous INTEGER PRIMARY KEY AUTOINCREMENT,
            id_patient INTEGER NOT NULL,
            id_medecin INTEGER NOT NULL,
            date_heure TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'DEMANDE'
                CHECK (statut IN ('DEMANDE', 'PLANIFIE', 'HONORE', 'ANNULE')),
            motif TEXT NOT NULL,
            ordonnance TEXT,
            diagnostic TEXT,
            montant REAL CHECK (montant IS NULL OR montant >= 0),
            paiement TEXT NOT NULL DEFAULT 'impaye'
                CHECK (lower(paiement) IN ('impaye','paye')),
            mode_paiement TEXT,
            date_paiement TEXT,

            FOREIGN KEY (id_patient)
                REFERENCES Users(id_user) ON DELETE RESTRICT,

            FOREIGN KEY (id_medecin)
                REFERENCES Users(id_user) ON DELETE RESTRICT,

            CHECK (id_patient <> id_medecin)
        );

        CREATE TABLE IF NOT EXISTS medicament (
            id_med INTEGER PRIMARY KEY AUTOINCREMENT,
            designation TEXT NOT NULL UNIQUE,
            famille_med TEXT NOT NULL,
            forme TEXT NOT NULL,
            prix REAL NOT NULL CHECK (prix >= 0),
            stock INTEGER NOT NULL DEFAULT 1 CHECK (stock >= 0),
            seuil INTEGER NOT NULL DEFAULT 0 CHECK (seuil >= 0)
        );
        """
    )

    db.commit()
    db.close()

    print("Base de données créée avec succès.")


def get_connection():

    db = sqlite3.connect("MediGest.db")

    db.row_factory = sqlite3.Row

    db.execute("PRAGMA foreign_keys = ON")

    return db
def base_vide(db):
    resultat = db.execute(
        "SELECT COUNT(*) FROM Users"
    ).fetchone()

    return resultat[0] == 0

if __name__ == "__main__":
    # creation de base de donnne
    creer_base()
