"""
Script de capture d'écran pour le user journey MediGest.
Prend des screenshots de chaque étape du parcours médecin et patient.
"""
import os, sys, time
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(__file__))
os.makedirs("captures", exist_ok=True)

from database import creer_base, get_connection, base_vide
import data_test
from main import creer_medecins_test
from gui import Application

def capture(app, nom):
    """Fait une capture de la fenêtre tkinter."""
    app.update_idletasks()
    app.update()
    time.sleep(0.3)
    app.update_idletasks()
    x = app.winfo_rootx()
    y = app.winfo_rooty()
    w = app.winfo_width()
    h = app.winfo_height()
    sortie = f"captures/{nom}.png"
    ret = os.system(f"import -window root -crop {w}x{h}+{x}+{y} +repage {sortie} 2>/dev/null")
    if ret != 0:
        os.system(f"scrot -a {x},{y},{w},{h} {sortie} 2>/dev/null")
    print(f"  → {sortie} ({w}x{h})")

creer_base()
db = get_connection()
if base_vide(db):
    data_test.charger(db)
else:
    creer_medecins_test(db)

app = Application(db)
app.geometry("1180x740")
app.update_idletasks()
app.update()

# ── Étape 1 : Écran de connexion ──────────────────────────────────────────────
print("1. Écran de connexion")
capture(app, "01_connexion")

# ── Étape 2 : Connexion médecin ───────────────────────────────────────────────
print("2. Connexion médecin dr.alaoui")
app.login.set("dr.alaoui")
app.mdp.set("medecin123")
app.update()
capture(app, "02_connexion_remplie")
app.connecter()
app.update_idletasks(); app.update(); time.sleep(0.4)

# ── Étape 3 : Dashboard médecin ───────────────────────────────────────────────
print("3. Dashboard médecin")
app.carnet.select(0)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "03_dashboard_medecin")

# ── Étape 4 : Onglet Patients ─────────────────────────────────────────────────
print("4. Onglet Patients")
app.carnet.select(1)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "04_patients")

# ── Étape 5 : Onglet Consultations ────────────────────────────────────────────
print("5. Onglet Consultations")
app.carnet.select(2)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "05_consultations")

# ── Étape 6 : Onglet Agenda (Rendez-vous) ────────────────────────────────────
print("6. Onglet Agenda")
app.carnet.select(3)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "06_agenda")

# ── Étape 7 : Onglet Stock ────────────────────────────────────────────────────
print("7. Onglet Stock")
app.carnet.select(4)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "07_stock")

# ── Étape 8 : Onglet Facturation ─────────────────────────────────────────────
print("8. Onglet Facturation")
app.carnet.select(5)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "08_facturation")

# ── Étape 9 : Onglet Profil médecin ──────────────────────────────────────────
print("9. Onglet Profil médecin")
app.carnet.select(6)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "09_profil_medecin")

# ── Déconnexion et connexion patient ─────────────────────────────────────────
print("10. Déconnexion")
app.afficher_connexion()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "10_deconnexion")

print("11. Connexion patient s.tazi")
app.login.set("s.tazi")
app.mdp.set("patient123")
app.update()
app.connecter()
app.update_idletasks(); app.update(); time.sleep(0.4)

# ── Étape 12 : Dashboard patient ─────────────────────────────────────────────
print("12. Dashboard patient - Mes rendez-vous")
app.carnet.select(0)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "11_patient_rdv")

# ── Étape 13 : Onglet Prendre RDV ────────────────────────────────────────────
print("13. Prendre un RDV")
app.carnet.select(1)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "12_patient_prendre_rdv")

# ── Étape 14 : Onglet Ordonnances patient ─────────────────────────────────────
print("14. Ordonnances patient")
app.carnet.select(2)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "13_patient_ordonnances")

# ── Étape 15 : Profil patient ─────────────────────────────────────────────────
print("15. Profil patient")
app.carnet.select(3)
app.rafraichir_courant()
app.update_idletasks(); app.update(); time.sleep(0.3)
capture(app, "14_patient_profil")

app.destroy()
db.close()
print("\nToutes les captures sont dans ./captures/")

