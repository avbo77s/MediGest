from database import creer_base, get_connection
from dao import UtilisateurDAO
from gui import Application


def creer_medecins_test(db):

    utilisateurs = UtilisateurDAO(db)

    # Médecin 1 : Dr Alaoui
    if utilisateurs.chercher_par_login("dr.alaoui") is None:

        utilisateurs.ajouter_medecin(
            "dr.alaoui",
            "medecin123",
            "A100200",
            "Alaoui",
            "Karim",
            "k.alaoui@alamal.ma",
            "0522000001",
            "Clinique Al Amal, Casablanca",
            "Médecine générale",
            200
        )

        print("Dr Alaoui ajouté !")

    # Médecin 2 : Dr Bennani
    if utilisateurs.chercher_par_login("dr.bennani") is None:

        utilisateurs.ajouter_medecin(
            "dr.bennani",
            "medecin123",
            "B300400",
            "Bennani",
            "Salma",
            "s.bennani@alamal.ma",
            "0522000002",
            "Clinique Al Amal, Casablanca",
            "Cardiologie",
            300
        )

        print("Dr Bennani ajouté !")


def main():

    creer_base()

    db = get_connection()

    try:
        # Ajouter les médecins sans toucher aux autres données
        creer_medecins_test(db)

        # Lancer l'application
        app = Application(db)
        app.mainloop()

    finally:
        db.close()


if __name__ == "__main__":
    main()
