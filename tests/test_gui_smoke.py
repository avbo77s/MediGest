# Tests simples pour verifier que la fenetre et les onglets s'ouvrent bien
import os
import sys
import unittest
from unittest import mock

# Pour pouvoir importer les fichiers du projet
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

from database import creer_base, get_connection, base_vide
from gui import Application
import data_test
import horloge


class TestInterface(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # On s'assure que la base contient les donnees de base avant les tests
        creer_base()
        db = get_connection()
        if base_vide(db):
            data_test.charger(db)
        db.close()

    def setUp(self):
        self.db = get_connection()
        self.app = Application(self.db)

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.db.close()

    @mock.patch("tkinter.messagebox.showinfo")
    @mock.patch("tkinter.messagebox.showwarning")
    def test_medecin_a_7_onglets(self, mock_warn, mock_info):
        # Verifie que le medecin se connecte bien avec ses 7 onglets
        self.app.login.set("dr.alaoui")
        self.app.mdp.set("medecin123")
        self.app.connecter()

        self.assertIsNotNone(self.app.user)
        self.assertEqual(self.app.user.role, "medecin")
        self.assertEqual(self.app.carnet.index("end"), 7)

        onglets = [self.app.carnet.tab(i, "text") for i in range(7)]
        self.assertEqual(
            onglets,
            ["Patients", "Rendez-vous", "Consultations", "Stock",
             "Facturation", "Tableau de bord", "Mon profil"]
        )

        # On teste que chaque onglet peut se rafraichir sans bug
        for i in range(7):
            self.app.carnet.select(i)
            self.app.rafraichir_courant()

    @mock.patch("tkinter.messagebox.showinfo")
    @mock.patch("tkinter.messagebox.showwarning")
    def test_patient_a_4_onglets(self, mock_warn, mock_info):
        # Verifie que le patient se connecte bien avec ses 4 onglets
        self.app.login.set("s.tazi")
        self.app.mdp.set("patient123")
        self.app.connecter()

        self.assertIsNotNone(self.app.user)
        self.assertEqual(self.app.user.role, "patient")
        self.assertEqual(self.app.carnet.index("end"), 4)

        onglets = [self.app.carnet.tab(i, "text") for i in range(4)]
        self.assertEqual(
            onglets,
            ["Mes rendez-vous", "Mes ordonnances", "Mes factures", "Mon profil"]
        )

        for i in range(4):
            self.app.carnet.select(i)
            self.app.rafraichir_courant()

    @mock.patch("tkinter.messagebox.showinfo")
    @mock.patch("tkinter.messagebox.showwarning")
    def test_mauvais_mot_de_passe(self, mock_warn, mock_info):
        # Verifie qu'un mauvais mot de passe refuse la connexion
        self.app.login.set("dr.alaoui")
        self.app.mdp.set("mauvais_mot_de_passe")
        self.app.connecter()

        self.assertIsNone(self.app.user)
        mock_warn.assert_called_once()


if __name__ == "__main__":
    unittest.main()

