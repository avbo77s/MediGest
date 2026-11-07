# ============================================================
# Cette partie est faite par Abderrahmane (GUI)
# ============================================================

import html
import json
import os
import shutil
import sqlite3
import unicodedata
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk, messagebox, font

import exports
import horloge
from dao import UtilisateurDAO, MedicamentDAO, RendezVousDAO, StatistiquesDAO
from models import Patient, Medecin, Medicament, LigneOrdonnance, Ordonnance

#cette partie est fait sans ai
VERT = "#0f766e"        # Vert sarcelle médical
VERT_CLAIR = "#14b8a6"  # Vert clair pour hover et barres
ROUGE = "#b91c1c"       # Rouge d'alerte et boutons destructifs

COULEURS_STATUT = {
    "PLANIFIE": "#fef3c7",  # Jaune pâle
    "DEMANDE":  "#ffedd5",  # Orange pâle
    "HONORE":   "#dcfce7",  # Vert pâle
    "ANNULE":   "#e5e7eb",  # Gris clair
}

COULEURS_ANNEAU = {
    "PLANIFIE": "#eab308",
    "DEMANDE":  "#f97316",
    "HONORE":   "#16a34a",
    "ANNULE":   "#9ca3af",
}

# Créneaux horaires de 30 min entre 08:00 et 17:30
CRENEAUX_BASE = ["%02d:%02d" % (h, m) for h in range(8, 18) for m in (0, 30)]



#cette partie est fait sans ai
def appliquer_style(racine):
    # on configure le style clam pour avoir de belles couleurs sur les boutons et les tables
    style = ttk.Style(racine)
    style.theme_use("clam")

    # Calcul dynamique de la hauteur des lignes selon la police systeme pour eviter tout chevauchement
    f_defaut = font.nametofont("TkDefaultFont")
    hauteur_ligne = max(26, f_defaut.metrics("linespace") + 8)

    style.configure("TButton", padding=4)
    style.configure("Action.TButton", background=VERT, foreground="white")
    style.map("Action.TButton", background=[("active", VERT_CLAIR)])
    style.configure("Danger.TButton", background=ROUGE, foreground="white")
    style.configure("Titre.TLabel", foreground=VERT, font=("TkDefaultFont", 9, "bold"))
    style.configure("Alerte.TLabel", foreground=ROUGE, font=("TkDefaultFont", 9, "bold"))

    # Configuration du tableau pour que le texte soit parfaitement aere
    style.configure("Treeview", rowheight=hauteur_ligne)
    style.configure("Treeview.Heading", background=VERT, foreground="white", font=("TkDefaultFont", 9, "bold"))
    style.map("Treeview", background=[("selected", VERT_CLAIR)], foreground=[("selected", "white")])
    style.map("Treeview.Heading", background=[("active", VERT_CLAIR)])

    style.configure("Chiffre.TLabel", foreground=VERT, font=("TkDefaultFont", 13, "bold"))

    # Configuration des onglets pour un affichage net sans coupure de titre
    style.configure("TNotebook.Tab", padding=[8, 4], font=("TkDefaultFont", 9, "bold"))
    style.map("TNotebook.Tab", background=[("selected", "#ffffff"), ("active", "#e6f4f1")])


#cette partie est fait sans ai
def champ(parent, libelle, ligne, colonne=0, largeur=16, show=None):
    # fonction pratique pour creer un label et une zone de texte dans une grille
    variable = tk.StringVar()
    ttk.Label(parent, text=libelle).grid(row=ligne, column=colonne, sticky="e", padx=4, pady=2)
    ttk.Entry(parent, textvariable=variable, width=largeur, show=show or "").grid(
        row=ligne, column=colonne + 1, sticky="w", pady=2
    )
    return variable


def lire_col(ligne, cle, defaut=""):
    # pour lire une colonne sans faire planter le code si elle est vide
    try:
        val = ligne[cle]
        return defaut if val is None else val
    except Exception:
        return defaut


def normaliser(texte):
    # enleve les accents pour que la recherche trouve facilement le nom ou prenom
    t = unicodedata.normalize("NFD", str(texte or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def objet_vers_user(ligne):
    # transforme la ligne sql en objet pour manipuler facilement les donnees
    if ligne is None:
        return None
    role = str(lire_col(ligne, "role", "")).lower()
    attrs = {
        "id": lire_col(ligne, "id_user") or lire_col(ligne, "id"),
        "login": lire_col(ligne, "login"),
        "nom": lire_col(ligne, "nom"),
        "prenom": lire_col(ligne, "prenom"),
        "cin": lire_col(ligne, "cin"),
        "telephone": lire_col(ligne, "telephone"),
        "email": lire_col(ligne, "email"),
        "adresse": lire_col(ligne, "adresse"),
        "role": "medecin" if role == "medecin" else "patient",
        "tarif": lire_col(ligne, "tarif", 200.0),
        "specialite": lire_col(ligne, "specialite", "Médecine générale"),
        "allergies": lire_col(ligne, "allergies", ""),
    }

    class UtilisateurConnecte:
        def __init__(self, data):
            for k, v in data.items():
                setattr(self, k, v)

        def nom_complet(self):
            p, n = self.prenom or "", (self.nom or "").upper()
            return f"Dr {p} {n}" if self.role == "medecin" else f"{p} {n}"

        def ecrans(self):
            if self.role == "medecin":
                return ["Patients", "Rendez-vous", "Consultations", "Stock",
                        "Facturation", "Tableau de bord", "Mon profil"]
            return ["Mes rendez-vous", "Mes ordonnances", "Mes factures", "Mon profil"]

    return UtilisateurConnecte(attrs)


 
# 3. COMPOSANTS RÉUTILISABLES
 

#cette partie est fait sans ai
class Table(ttk.Frame):
    # notre composant tableau avec le treeview et la barre de defilement

    def __init__(self, parent, colonnes, hauteur=10):
        super().__init__(parent)
        self.colonnes = colonnes
        self.arbre = ttk.Treeview(
            self,
            columns=[c[0] for c in colonnes],
            show="headings",
            height=hauteur,
            selectmode="browse"
        )
        for cle, titre, largeur in colonnes:
            self.arbre.heading(cle, text=titre)
            self.arbre.column(cle, width=largeur, minwidth=max(40, largeur // 2), stretch=True, anchor="w")

        defil = ttk.Scrollbar(self, orient="vertical", command=self.arbre.yview)
        self.arbre.configure(yscrollcommand=defil.set)
        self.arbre.pack(side="left", fill="both", expand=True)
        defil.pack(side="right", fill="y")

        for statut, couleur in COULEURS_STATUT.items():
            self.arbre.tag_configure(statut, background=couleur)
        self.arbre.tag_configure("alerte", background="#fee2e2", foreground=ROUGE)

    def charger(self, lignes, etiquette=None):
        # vide et recharge le tableau avec les nouvelles donnees
        self.arbre.delete(*self.arbre.get_children())
        for ligne in lignes:
            valeurs = [lire_col(ligne, c[0]) for c in self.colonnes]
            tags = (etiquette(ligne),) if etiquette else ()
            ident = str(lire_col(ligne, "id") or lire_col(ligne, "id_user") or
                        lire_col(ligne, "id_rendezvous") or lire_col(ligne, "id_med"))
            self.arbre.insert("", "end", iid=ident, values=valeurs, tags=tags)

    def selection(self):
        # renvoie l'id de la ligne selectionnee par l'utilisateur
        choix = self.arbre.selection()
        if not choix:
            return None
        try:
            return int(choix[0])
        except ValueError:
            return choix[0]

    def surselection(self, fonction):
        # declenche l'action quand on clique sur une ligne
        self.arbre.bind("<<TreeviewSelect>>", lambda _evt: fonction())


#cette partie est fait sans ai
class Onglet(ttk.Frame):
    # classe de base commune a tous les onglets du projet

    def __init__(self, carnet, app):
        super().__init__(carnet, padding=8)
        self.app = app
        self.construire()
        self.rafraichir()

    def construire(self):
        pass

    def rafraichir(self):
        pass

    def agir(self, action):
        # execute l'action et affiche un message clair si une regle est violee au lieu de crasher
        try:
            action()
        except Exception as e:
            messagebox.showwarning("MediGest", str(e))
        else:
            self.app.rafraichir_tout()

    def selection_ou_message(self, table, message="Sélectionnez d'abord une ligne."):
        identifiant = table.selection()
        if identifiant is None:
            messagebox.showinfo("MediGest", message)
        return identifiant


 
# 4. GRAPHIQUES CANVAS DU TABLEAU DE BORD
 

#cette partie est fait sans ai
class Histogramme(tk.Canvas):
    def __init__(self, parent, **options):
        super().__init__(parent, bg="white", highlightthickness=1,
                         highlightbackground="#d1d5db", **options)
        self.donnees = []
        self.bind("<Configure>", lambda _evt: self.dessiner(self.donnees))

    def dessiner(self, donnees):
        self.donnees = donnees or []
        self.delete("all")
        if not self.donnees:
            return
        f_petit = font.nametofont("TkSmallCaptionFont")
        f_gras = font.Font(font=f_petit)
        f_gras.configure(weight="bold")

        w, h = max(self.winfo_width(), 100), max(self.winfo_height(), 100)
        maxi = max((v for _, v in self.donnees), default=1) or 1
        pas = (w - 30) / max(len(self.donnees), 1)

        lh = f_petit.metrics("linespace")
        bas_y = h - lh - 6

        for i, (libelle, val) in enumerate(self.donnees):
            x0 = 15 + i * pas + pas * 0.15
            x1 = 15 + (i + 1) * pas - pas * 0.15
            y1 = bas_y
            hauteur_barre = (bas_y - 45) * (val / maxi)
            y0 = max(24, y1 - hauteur_barre)
            self.create_rectangle(x0, y0, x1, y1, fill=VERT, outline="")
            self.create_text((x0 + x1) / 2, y0 - lh // 2, text=str(int(val)), font=f_gras)
            self.create_text((x0 + x1) / 2, h - lh // 2 - 2, text=libelle, font=f_petit)


#cette partie est fait sans ai
class Anneau(tk.Canvas):
    def __init__(self, parent, **options):
        super().__init__(parent, bg="white", highlightthickness=1,
                         highlightbackground="#d1d5db", **options)
        self.donnees = {}
        self.bind("<Configure>", lambda _evt: self.dessiner(self.donnees))

    def dessiner(self, donnees):
        self.donnees = donnees or {}
        self.delete("all")
        total = sum(self.donnees.values())
        f_petit = font.nametofont("TkSmallCaptionFont")
        f_titre = font.nametofont("TkHeadingFont")

        w, h = max(self.winfo_width(), 100), max(self.winfo_height(), 100)
        if total == 0:
            self.create_text(w // 2, h // 2, text="Aucune visite", fill="#9ca3af", font=f_petit)
            return
        # on plafonne le rayon à 160px pour éviter un anneau trop grand sur grands écrans
        rayon = max(30, min(160, min(w // 3, h // 2) - 15))
        cx, cy = w // 3, h // 2
        boite = (cx - rayon, cy - rayon, cx + rayon, cy + rayon)

        debut = 90
        for statut, nombre in self.donnees.items():
            if nombre <= 0:
                continue
            angle = min(360 * nombre / total, 359.99)
            c = COULEURS_ANNEAU.get(statut, "#9ca3af")
            self.create_arc(boite, start=debut, extent=-angle, style="arc", width=20, outline=c)
            debut -= angle

        self.create_text(cx, cy, text=f"{total}\nvisites", font=f_titre, justify="center")

        # légende à droite de l'anneau, jamais trop près du bord
        leg_x = min(w - 150, cx + rayon + 40)
        lh = max(16, f_petit.metrics("linespace") + 2)
        debut_y = max(10, cy - (len(self.donnees) * lh) // 2)
        for i, (statut, nombre) in enumerate(self.donnees.items()):
            y = debut_y + i * lh
            c = COULEURS_ANNEAU.get(statut, "#9ca3af")
            self.create_rectangle(leg_x, y, leg_x + 12, y + 10, fill=c, outline="")
            self.create_text(leg_x + 16, y + 5, anchor="w",
                             text=f"{statut.capitalize()} : {nombre}", font=f_petit)


#cette partie est fait sans ai
class BarresHorizontales(tk.Canvas):
    def __init__(self, parent, **options):
        super().__init__(parent, bg="white", highlightthickness=1,
                         highlightbackground="#d1d5db", **options)
        self.donnees = []
        self.bind("<Configure>", lambda _evt: self.dessiner(self.donnees))

    def dessiner(self, donnees):
        self.donnees = donnees or []
        self.delete("all")
        if not self.donnees:
            return
        f_petit = font.nametofont("TkSmallCaptionFont")
        f_gras = font.Font(font=f_petit)
        f_gras.configure(weight="bold")

        w, h = max(self.winfo_width(), 200), max(self.winfo_height(), 50)
        maxi = max((v for _, v in self.donnees), default=1) or 1

        n = max(len(self.donnees), 1)
        lh = max(20, min(28, (h - 12) // n))
        label_w = max((f_petit.measure(nom) for nom, _ in self.donnees), default=120) + 20

        for i, (nom, val) in enumerate(self.donnees):
            y = 6 + i * lh
            longueur = max(10, (w - label_w - 60) * (val / maxi))
            self.create_text(8, y + lh // 2, anchor="w", text=nom, font=f_petit)
            self.create_rectangle(label_w, y + 2, label_w + longueur, y + lh - 2, fill=VERT_CLAIR, outline="")
            self.create_text(label_w + longueur + 8, y + lh // 2, anchor="w", text=str(val), font=f_gras)


 
# 5. ONGLETS DU MÉDECIN
 

#cette partie est fait sans ai
class OngletPatients(Onglet):
    # onglet pour chercher, voir la fiche et creer des patients

    def construire(self):
        haut = ttk.Frame(self)
        haut.pack(fill="x", pady=(0, 4))
        self.recherche = tk.StringVar()
        self.archives = tk.BooleanVar(value=False)

        ttk.Label(haut, text="Rechercher (nom, CIN) :").pack(side="left")
        entree_rech = ttk.Entry(haut, textvariable=self.recherche, width=18)
        entree_rech.pack(side="left", padx=6)
        ttk.Checkbutton(haut, text="Afficher les comptes archivés",
                        variable=self.archives, command=self.rafraichir).pack(side="left", padx=8)
        self.recherche.trace_add("write", lambda *_: self.rafraichir())

        cols = [
            ("cin", "CIN", 85), ("nom", "Nom", 120), ("prenom", "Prénom", 120),
            ("date_naissance", "Naissance", 95), ("sexe", "Sexe", 45),
            ("telephone", "Téléphone", 115), ("allergies", "Allergies", 160)
        ]
        self.table = Table(self, cols, hauteur=5)
        self.table.pack(fill="both", expand=True, pady=2)
        self.table.surselection(self.afficher_fiche)

        info_frame = ttk.Frame(self)
        info_frame.pack(fill="x", pady=2)
        self.fiche = ttk.Label(info_frame, style="Titre.TLabel")
        self.fiche.pack(side="left", padx=4)
        ttk.Button(info_frame, text="Archiver / réactiver",
                   style="Danger.TButton", command=self.archiver).pack(side="right")

        cadre = ttk.LabelFrame(self, text="Nouveau compte patient", padding=4)
        cadre.pack(fill="x", pady=(2, 4))
        self.v = {
            "login": champ(cadre, "Login", 0, 0, largeur=12),
            "mdp": champ(cadre, "Mot de passe", 0, 2, largeur=12, show="*"),
            "nom": champ(cadre, "Nom", 0, 4, largeur=12),
            "prenom": champ(cadre, "Prénom", 1, 0, largeur=12),
            "cin": champ(cadre, "CIN", 1, 2, largeur=12),
            "naissance": champ(cadre, "Naissance", 2, 0, largeur=12),
            "telephone": champ(cadre, "Téléphone", 2, 2, largeur=12),
            "email": champ(cadre, "E-mail", 2, 4, largeur=12),
            "adresse": champ(cadre, "Adresse", 3, 0, largeur=12),
            "allergies": champ(cadre, "Allergies", 3, 2, largeur=12),
        }
        self.sexe = tk.StringVar(value="F")
        ttk.Label(cadre, text="Sexe").grid(row=1, column=4, sticky="e", padx=4, pady=2)
        ttk.Combobox(cadre, textvariable=self.sexe, values=["M", "F"],
                     width=6, state="readonly").grid(row=1, column=5, sticky="w", pady=2)
        ttk.Button(cadre, text="Créer le compte", style="Action.TButton",
                   command=self.creer).grid(row=3, column=4, columnspan=2, sticky="ew", padx=4, pady=2)

    def rafraichir(self):
        pat = self.app.utilisateurs.afficher_patients() or []
        motif = normaliser(self.recherche.get().strip())
        filtres = []
        for p in pat:
            est_actif = bool(lire_col(p, "actif", 1))
            if not self.archives.get() and not est_actif:
                continue
            if motif:
                texte_ligne = normaliser(f"{lire_col(p, 'nom')} {lire_col(p, 'prenom')} {lire_col(p, 'cin')}")
                if motif not in texte_ligne:
                    continue
            d = dict(p)
            d["id"] = d.get("id_user")
            filtres.append(d)

        self.table.charger(filtres, lambda p: "ANNULE" if not lire_col(p, "actif", 1) else None)

    def afficher_fiche(self):
        ident = self.table.selection()
        if not ident:
            return
        p = self.app.utilisateurs.chercher_par_id(ident)
        if not p:
            return
        rdvs = self.app.rdv.afficher_par_patient(ident) or []
        honorés = [r for r in rdvs if lire_col(r, "statut") == "HONORE"]
        allergies = lire_col(p, 'allergies') or 'Aucune'
        self.fiche.config(
            text=f"Fiche : {lire_col(p, 'prenom')} {str(lire_col(p, 'nom')).upper()} (CIN : {lire_col(p, 'cin')})  ·  Allergies : {allergies}  ·  {len(honorés)} consultation(s)"
        )

    def archiver(self):
        ident = self.selection_ou_message(self.table)
        if not ident:
            return
        p = self.app.utilisateurs.chercher_par_id(ident)
        if not p:
            return
        actif = bool(lire_col(p, "actif", 1))
        def op():
            if actif:
                futurs = [r for r in (self.app.rdv.afficher_par_patient(ident) or [])
                          if lire_col(r, "statut") in ("PLANIFIE", "DEMANDE")]
                if futurs:
                    raise ValueError("Impossible d'archiver un patient avec des rendez-vous à venir.")
                self.app.utilisateurs.desactiver_utilisateur(ident)
            else:
                self.app.utilisateurs.reactiver_utilisateur(ident)
        self.agir(op)

    def creer(self):
        d = {k: v.get().strip() for k, v in self.v.items()}
        def op():
            for k in ("login", "mdp", "nom", "prenom", "cin", "email"):
                if not d.get(k):
                    raise ValueError(f"Le champ '{k}' est obligatoire.")
            self.app.utilisateurs.ajouter_patient(
                d["login"], d["mdp"], d["cin"], d["nom"], d["prenom"],
                d["email"], d["telephone"] or None, d["adresse"] or None,
                d["naissance"] or "1990-01-01", self.sexe.get(), d["allergies"] or None
            )
            for v in self.v.values():
                v.set("")
        self.agir(op)


#cette partie est fait sans ai
class OngletRendezVous(Onglet):
    # onglet pour l'agenda des rendez-vous avec filtres par date

    def construire(self):
        barre = ttk.Frame(self)
        barre.pack(fill="x", pady=(0, 4))
        self.filtre = tk.StringVar(value="semaine")
        self.nom = tk.StringVar()

        ttk.Label(barre, text="Afficher :", style="Titre.TLabel").pack(side="left")
        for val, txt in (("jour", "Aujourd'hui"), ("semaine", "Cette semaine"), ("tous", "Tous")):
            ttk.Radiobutton(barre, text=txt, value=val, variable=self.filtre,
                            command=self.rafraichir).pack(side="left", padx=4)
        ttk.Label(barre, text="Recherche :").pack(side="left", padx=(10, 4))
        ttk.Entry(barre, textvariable=self.nom, width=12).pack(side="left")
        ttk.Button(barre, text="Filtrer", style="Action.TButton",
                   command=self.rafraichir).pack(side="left", padx=6)

        plan = ttk.LabelFrame(self, text="Planifier un rendez-vous", padding=4)
        plan.pack(fill="x", pady=3)
        self.patient, self.jour = tk.StringVar(), tk.StringVar(value=horloge.aujourdhui())
        self.heure, self.motif = tk.StringVar(), tk.StringVar()

        ttk.Label(plan, text="Patient").pack(side="left", padx=4)
        self.liste_patients = ttk.Combobox(plan, textvariable=self.patient, state="readonly", width=18)
        self.liste_patients.pack(side="left")

        ttk.Label(plan, text="Date").pack(side="left", padx=4)
        entree_date = ttk.Entry(plan, textvariable=self.jour, width=10)
        entree_date.pack(side="left")
        entree_date.bind("<FocusOut>", lambda _: self.maj_creneaux())

        self.liste_heures = ttk.Combobox(plan, textvariable=self.heure, state="readonly", width=6)
        self.liste_heures.pack(side="left", padx=4)

        ttk.Label(plan, text="Motif").pack(side="left", padx=4)
        ttk.Entry(plan, textvariable=self.motif, width=14).pack(side="left")
        ttk.Button(plan, text="Planifier", style="Action.TButton",
                   command=self.planifier).pack(side="left", padx=6)

        pied = ttk.Frame(self)
        pied.pack(side="bottom", fill="x", pady=4)
        ttk.Button(pied, text="Annuler le rendez-vous", style="Danger.TButton",
                   command=self.annuler).pack(side="right", padx=(6, 0))
        ttk.Button(pied, text="Confirmer la demande", style="Action.TButton",
                   command=self.confirmer).pack(side="right", padx=6)
        self.attente = ttk.Label(pied, style="Titre.TLabel")
        self.attente.pack(side="left", fill="x", expand=True)

        cols = [
            ("date_heure", "Date et heure", 140), ("patient", "Patient", 180),
            ("motif", "Motif", 220), ("statut", "Statut", 100)
        ]
        self.table = Table(self, cols, hauteur=6)
        self.table.pack(fill="both", expand=True, pady=4)

    def rafraichir(self):
        patients = self.app.utilisateurs.afficher_patients() or []
        self.d_patients = {
            f"{lire_col(p, 'nom')} {lire_col(p, 'prenom')}": lire_col(p, "id_user")
            for p in patients if lire_col(p, "actif", 1)
        }
        self.liste_patients["values"] = list(self.d_patients.keys())
        self.maj_creneaux()

        tous_rdv = self.app.rdv.afficher_par_medecin(self.app.user.id) or []
        aujourdhui = horloge.aujourdhui()
        f = self.filtre.get()
        mot = normaliser(self.nom.get().strip())

        filtres = []
        n_demandes = 0
        for r in tous_rdv:
            stat = lire_col(r, "statut")
            if stat == "DEMANDE":
                n_demandes += 1
            dh = str(lire_col(r, "date_heure"))
            jour_rdv = dh[:10]
            if f == "jour" and jour_rdv != aujourdhui:
                continue
            if f == "semaine":
                try:
                    d_obj = datetime.strptime(jour_rdv, "%Y-%m-%d").date()
                    ref = datetime.strptime(aujourdhui, "%Y-%m-%d").date()
                    if abs((d_obj - ref).days) > 7:
                        continue
                except Exception:
                    pass
            p_nom = f"{lire_col(r, 'nom_patient', '')} {lire_col(r, 'prenom_patient', '')}".strip()
            if not p_nom:
                p_obj = self.app.utilisateurs.chercher_par_id(lire_col(r, "id_patient"))
                p_nom = f"{lire_col(p_obj, 'nom')} {lire_col(p_obj, 'prenom')}" if p_obj else ""
            if mot and mot not in normaliser(p_nom):
                continue
            filtres.append({
                "id": lire_col(r, "id_rendezvous"),
                "date_heure": dh,
                "patient": p_nom,
                "motif": lire_col(r, "motif"),
                "statut": stat
            })

        self.table.charger(filtres, lambda row: row["statut"])
        self.attente.config(text=f"{n_demandes} demande(s) en attente")

    def maj_creneaux(self):
        j = self.jour.get().strip()
        try:
            d = datetime.strptime(j, "%Y-%m-%d").date()
            if d.weekday() == 6:  # Dimanche
                self.liste_heures["values"] = []
                return
        except Exception:
            self.liste_heures["values"] = []
            return

        occupes = set()
        for r in (self.app.rdv.afficher_par_medecin(self.app.user.id) or []):
            if lire_col(r, "statut") != "ANNULE" and str(lire_col(r, "date_heure")).startswith(j):
                occupes.add(str(lire_col(r, "date_heure"))[11:16])
        libres = [c for c in CRENEAUX_BASE if c not in occupes]
        self.liste_heures["values"] = libres
        if libres and not self.heure.get():
            self.heure.set(libres[0])

    def planifier(self):
        id_p = self.d_patients.get(self.patient.get())
        if not id_p:
            messagebox.showinfo("MediGest", "Veuillez choisir un patient.")
            return
        dh = f"{self.jour.get().strip()} {self.heure.get().strip()}"
        def op():
            id_rdv = self.app.rdv.ajouter_rdv(id_p, self.app.user.id, dh, self.motif.get().strip())
            self.app.rdv.modifier_statut(id_rdv, "PLANIFIE")
        self.agir(op)

    def confirmer(self):
        ident = self.selection_ou_message(self.table)
        if ident:
            self.agir(lambda: self.app.rdv.modifier_statut(ident, "PLANIFIE"))

    def annuler(self):
        ident = self.selection_ou_message(self.table)
        if ident and messagebox.askyesno("MediGest", "Annuler ce rendez-vous ?"):
            self.agir(lambda: self.app.rdv.annuler_rdv(ident))


#cette partie est fait sans ai
class OngletConsultations(Onglet):
    # onglet pour honorer le rdv, ecrire le diagnostic et donner des medicaments

    def construire(self):
        ttk.Label(self, text="1. Rendez-vous à honorer", style="Titre.TLabel").pack(anchor="w")
        cols = [("date_heure", "Date et heure", 140), ("patient", "Patient", 200), ("motif", "Motif", 220)]
        self.table = Table(self, cols, hauteur=3)
        self.table.pack(fill="x", pady=2)
        self.table.surselection(self.changer_rdv)

        self.allergie = ttk.Label(self, style="Alerte.TLabel")
        self.allergie.pack(anchor="w", pady=2)

        bas = ttk.Frame(self)
        bas.pack(side="bottom", fill="x", pady=4)
        ttk.Button(bas, text="Retirer la ligne", command=self.retirer_ligne).pack(side="left")
        ttk.Button(bas, text="Valider la consultation", style="Action.TButton",
                   command=self.valider).pack(side="right")

        corps = ttk.Frame(self)
        corps.pack(fill="both", expand=True, pady=2)

        gauche = ttk.Frame(corps)
        gauche.pack(side="left", fill="both", expand=True)
        ttk.Label(gauche, text="2. Diagnostic", style="Titre.TLabel").pack(anchor="w")
        self.diagnostic = tk.Text(gauche, height=5, width=28, wrap="word")
        self.diagnostic.pack(fill="both", expand=True, pady=2)

        droite = ttk.Frame(corps)
        droite.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ttk.Label(droite, text="3. Ordonnance (stock diminué à la validation)",
                  style="Titre.TLabel").pack(anchor="w")

        cadre_ajout = ttk.Frame(droite)
        cadre_ajout.pack(fill="x", pady=2)
        self.med_choisi, self.qte = tk.StringVar(), tk.IntVar(value=1)
        self.posologie = tk.StringVar(value="1 prise, 3 fois par jour")

        l1 = ttk.Frame(cadre_ajout)
        l1.pack(fill="x", pady=1)
        ttk.Label(l1, text="Médicament :").pack(side="left")
        self.liste_med = ttk.Combobox(l1, textvariable=self.med_choisi, state="readonly")
        self.liste_med.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Label(l1, text="Qté :").pack(side="left")
        ttk.Spinbox(l1, from_=1, to=20, textvariable=self.qte, width=3).pack(side="left", padx=2)

        l2 = ttk.Frame(cadre_ajout)
        l2.pack(fill="x", pady=1)
        ttk.Label(l2, text="Posologie :").pack(side="left")
        ttk.Entry(l2, textvariable=self.posologie).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(l2, text="Ajouter", command=self.ajouter_ligne).pack(side="left")

        self.lignes_ord = []
        self.table_lignes = Table(droite, [("id", "N°", 30), ("nom", "Médicament", 140),
                                           ("qte", "Qté", 40), ("posologie", "Posologie", 160)], hauteur=3)
        self.table_lignes.pack(fill="both", expand=True, pady=2)

    def rafraichir(self):
        tous = self.app.rdv.afficher_par_medecin(self.app.user.id) or []
        a_faire = []
        for r in tous:
            if lire_col(r, "statut") == "PLANIFIE":
                p_nom = f"{lire_col(r, 'nom_patient', '')} {lire_col(r, 'prenom_patient', '')}".strip()
                if not p_nom:
                    p = self.app.utilisateurs.chercher_par_id(lire_col(r, "id_patient"))
                    p_nom = f"{lire_col(p, 'nom')} {lire_col(p, 'prenom')}" if p else ""
                a_faire.append({
                    "id": lire_col(r, "id_rendezvous"),
                    "date_heure": lire_col(r, "date_heure"),
                    "patient": p_nom,
                    "motif": lire_col(r, "motif")
                })
        self.table.charger(a_faire)

        meds = self.app.medicaments.afficher_medicaments() or []
        self.d_meds = {f"{lire_col(m, 'designation')} (stock {lire_col(m, 'stock')})": m for m in meds}
        self.liste_med["values"] = list(self.d_meds.keys())
        self.lignes_ord = []
        self.maj_lignes()
        self.diagnostic.delete("1.0", "end")
        self.allergie.config(text="")

    def changer_rdv(self):
        ident = self.table.selection()
        if not ident:
            return
        r = self.app.rdv.chercher_par_id(ident)
        if not r:
            return
        p = self.app.utilisateurs.chercher_par_id(lire_col(r, "id_patient"))
        al = lire_col(p, "allergies")
        self.allergie.config(text=f"Allergies connues du patient : {al}" if al else "")

    def ajouter_ligne(self):
        m = self.d_meds.get(self.med_choisi.get())
        if not m:
            messagebox.showinfo("MediGest", "Choisissez d'abord un médicament.")
            return
        if self.qte.get() > lire_col(m, "stock", 0):
            messagebox.showwarning("MediGest", f"Stock insuffisant ({lire_col(m, 'stock')} restant).")
            return
        self.lignes_ord.append({
            "id": len(self.lignes_ord) + 1,
            "id_med": lire_col(m, "id_med"),
            "nom": lire_col(m, "designation"),
            "qte": self.qte.get(),
            "posologie": self.posologie.get().strip(),
            "prix": lire_col(m, "prix", 0.0)
        })
        self.maj_lignes()

    def retirer_ligne(self):
        choix = self.table_lignes.selection()
        if choix is not None:
            idx = int(choix) - 1
            if 0 <= idx < len(self.lignes_ord):
                del self.lignes_ord[idx]
                for i, l in enumerate(self.lignes_ord):
                    l["id"] = i + 1
                self.maj_lignes()

    def maj_lignes(self):
        self.table_lignes.charger(self.lignes_ord)

    def valider(self):
        ident = self.selection_ou_message(self.table)
        if not ident:
            return
        diag = self.diagnostic.get("1.0", "end").strip()
        if not diag:
            messagebox.showwarning("MediGest", "Veuillez saisir un diagnostic.")
            return
        def op():
            tarif_base = float(self.app.user.tarif or 200.0)
            total_meds = sum(l["prix"] * l["qte"] for l in self.lignes_ord)
            montant = tarif_base + total_meds
            json_ord = json.dumps(self.lignes_ord, ensure_ascii=False) if self.lignes_ord else None

            # Diminuer le stock
            for l in self.lignes_ord:
                med = self.app.medicaments.chercher_par_id(l["id_med"])
                nouveau = max(0, lire_col(med, "stock", 0) - l["qte"])
                self.app.medicaments.modifier_stock(l["id_med"], nouveau)

            self.app.rdv.enregistrer_consultation(ident, diag, json_ord, montant)
        self.agir(op)


#cette partie est fait sans ai
class OngletStock(Onglet):
    # onglet pour surveiller le stock des medicaments et en rajouter

    def construire(self):
        cols = [
            ("designation", "Désignation", 170), ("famille", "Famille", 130),
            ("forme", "Forme", 90), ("prix", "Prix (MAD)", 80),
            ("stock", "Stock", 60), ("seuil", "Seuil d'alerte", 90)
        ]

        cadre = ttk.LabelFrame(self, text="Nouveau médicament", padding=4)
        cadre.pack(side="bottom", fill="x", pady=(2, 4))
        self.v = {
            "designation": champ(cadre, "Désignation", 0, 0, largeur=11),
            "famille": champ(cadre, "Famille", 0, 2, largeur=9),
            "forme": champ(cadre, "Forme", 0, 4, largeur=7),
            "prix": champ(cadre, "Prix (MAD)", 1, 0, largeur=7),
            "stock": champ(cadre, "Stock initial", 1, 2, largeur=7),
            "seuil": champ(cadre, "Seuil d'alerte", 1, 4, largeur=7),
        }
        ttk.Button(cadre, text="Ajouter", style="Action.TButton",
                   command=self.ajouter).grid(row=1, column=6, padx=6, pady=2, sticky="ew")

        ligne = ttk.Frame(self)
        ligne.pack(side="bottom", fill="x", pady=2)
        self.quantite = tk.IntVar(value=20)
        ttk.Label(ligne, text="Quantité reçue :").pack(side="left")
        ttk.Spinbox(ligne, from_=1, to=500, textvariable=self.quantite, width=6).pack(side="left", padx=4)
        ttk.Button(ligne, text="Réapprovisionner le médicament sélectionné",
                   style="Action.TButton", command=self.reapprovisionner).pack(side="left", padx=6)

        self.bilan = ttk.Label(self, style="Alerte.TLabel")
        self.bilan.pack(side="bottom", anchor="w", pady=2)

        self.table = Table(self, cols, hauteur=6)
        self.table.pack(fill="both", expand=True, pady=4)

    def rafraichir(self):
        meds = self.app.medicaments.afficher_medicaments() or []
        lignes = []
        alertes = 0
        for m in meds:
            d = dict(m)
            d["id"] = d.get("id_med")
            stk, seuil = lire_col(d, "stock", 0), lire_col(d, "seuil", 0)
            if stk <= seuil:
                alertes += 1
            lignes.append(d)

        self.table.charger(lignes, lambda m: "alerte" if lire_col(m, "stock", 0) <= lire_col(m, "seuil", 0) else None)
        self.bilan.config(text=f"⚠ {alertes} médicament(s) sous le seuil d'alerte" if alertes else "")

    def reapprovisionner(self):
        ident = self.selection_ou_message(self.table)
        if not ident:
            return
        m = self.app.medicaments.chercher_par_id(ident)
        nouveau = lire_col(m, "stock", 0) + self.quantite.get()
        self.agir(lambda: self.app.medicaments.modifier_stock(ident, nouveau))

    def ajouter(self):
        d = {k: v.get().strip() for k, v in self.v.items()}
        def op():
            for k in ("designation", "famille", "forme", "prix", "stock", "seuil"):
                if not d.get(k):
                    raise ValueError(f"Champ '{k}' manquant.")
            self.app.medicaments.ajouter_medicament(
                d["designation"], d["famille"], d["forme"],
                float(d["prix"]), int(d["stock"]), int(d["seuil"])
            )
            for v in self.v.values():
                v.set("")
        self.agir(op)


#cette partie est fait sans ai
class OngletFacturation(Onglet):
    # onglet pour generer les factures et enregistrer les paiements

    def construire(self):
        haut = ttk.Frame(self)
        haut.pack(fill="x", pady=(0, 4))
        self.tarif = tk.StringVar(value=str(self.app.user.tarif or 200))
        ttk.Label(haut, text="Mon tarif de consultation (MAD) :").pack(side="left")
        ttk.Entry(haut, textvariable=self.tarif, width=8).pack(side="left", padx=4)
        ttk.Button(haut, text="Modifier", command=self.changer_tarif).pack(side="left")
        ttk.Button(haut, text="Exporter en CSV", command=self.exporter).pack(side="right")

        bas = ttk.Frame(self)
        bas.pack(side="bottom", fill="x", pady=4)
        self.mode = tk.StringVar(value="Espèces")
        ttk.Combobox(bas, textvariable=self.mode, values=["Espèces", "Carte", "Chèque"],
                     state="readonly", width=9).pack(side="left", padx=4)
        ttk.Button(bas, text="Encaisser", style="Action.TButton",
                   command=self.encaisser).pack(side="left")
        ttk.Button(bas, text="Imprimer la facture", command=lambda: self.imprimer("facture")).pack(side="right")
        ttk.Button(bas, text="Imprimer l'ordonnance", command=lambda: self.imprimer("ordonnance")).pack(side="right", padx=6)

        self.total = ttk.Label(self, style="Alerte.TLabel")
        self.total.pack(side="bottom", anchor="w", pady=2)

        cols = [
            ("date", "Date", 95), ("patient", "Patient", 140),
            ("diagnostic", "Diagnostic", 200), ("montant", "Montant (MAD)", 125),
            ("facture", "Facture", 85), ("paiement", "Paiement", 95)
        ]
        self.table = Table(self, cols, hauteur=8)
        self.table.pack(fill="both", expand=True, pady=4)

    def rafraichir(self):
        rdvs = self.app.rdv.afficher_par_medecin(self.app.user.id) or []
        lignes = []
        impayes = 0.0
        for r in rdvs:
            if lire_col(r, "statut") == "HONORE":
                p_nom = f"{lire_col(r, 'nom_patient', '')} {lire_col(r, 'prenom_patient', '')}".strip()
                if not p_nom:
                    p = self.app.utilisateurs.chercher_par_id(lire_col(r, "id_patient"))
                    p_nom = f"{lire_col(p, 'nom')} {lire_col(p, 'prenom')}" if p else ""
                paye = str(lire_col(r, "paiement", "impaye")).lower() == "paye"
                mont = float(lire_col(r, "montant", 0.0) or 0.0)
                if not paye:
                    impayes += mont
                lignes.append({
                    "id": lire_col(r, "id_rendezvous"),
                    "date": str(lire_col(r, "date_heure"))[:10],
                    "patient": p_nom,
                    "diagnostic": lire_col(r, "diagnostic"),
                    "montant": "%.2f" % mont,
                    "facture": "PAYE" if paye else "IMPAYE",
                    "paiement": lire_col(r, "mode_paiement") or "-"
                })
        self.table.charger(lignes, lambda l: "HONORE" if l["facture"] == "PAYE" else "DEMANDE")
        self.total.config(text="Total des factures impayées : %.2f MAD" % impayes)

    def changer_tarif(self):
        try:
            nouveau = float(self.tarif.get())
        except ValueError:
            messagebox.showwarning("MediGest", "Tarif invalide.")
            return
        def op():
            self.app.utilisateurs.modifier_utilisateur(self.app.user.id, tarif=nouveau)
            self.app.user.tarif = nouveau
        self.agir(op)

    def encaisser(self):
        ident = self.selection_ou_message(self.table)
        if ident:
            d = horloge.aujourdhui()
            self.agir(lambda: self.app.rdv.enregistrer_paiement(ident, self.mode.get(), d))

    def imprimer(self, quoi):
        ident = self.selection_ou_message(self.table)
        if ident:
            html_txt = self.app.generer_html(ident, quoi)
            exports.ouvrir_dans_navigateur(html_txt)

    def exporter(self):
        lignes = []
        for c in self.table.arbre.get_children():
            v = self.table.arbre.item(c)["values"]
            lignes.append({
                "Date": v[0], "Patient": v[1], "Diagnostic": v[2],
                "Montant (MAD)": v[3], "Facture": v[4], "Paiement": v[5]
            })
        if lignes:
            f = exports.exporter_csv(lignes)
            messagebox.showinfo("MediGest", f"Fichier exporté avec succès :\n{f}")


#cette partie est fait sans ai
class OngletTableauDeBord(Onglet):
    # onglet du tableau de bord avec les graphiques et stats

    def construire(self):
        cartes = ttk.Frame(self)
        cartes.pack(fill="x", pady=(0, 4))
        for col in range(6):
            cartes.columnconfigure(col, weight=1, uniform="kpi")

        self.chiffres = {}
        for col, (cle, lib) in enumerate((("patients", "Patients"), ("consultations", "Consultations"),
                                         ("ca", "CA encaissé"), ("impayes", "Impayés"),
                                         ("alertes", "Alerte stock"), ("demandes", "En attente"))):
            carte = ttk.LabelFrame(cartes, text=lib, padding=3)
            carte.grid(row=0, column=col, sticky="nsew", padx=2)
            self.chiffres[cle] = ttk.Label(carte, style="Chiffre.TLabel")
            self.chiffres[cle].pack(pady=2)

        # le pied de page (bouton sauvegarder) doit être ancré en bas avant les autres frames
        pied = ttk.Frame(self)
        pied.pack(side="bottom", fill="x", pady=4)
        ttk.Button(pied, text="Sauvegarder la base de données", command=self.sauvegarder).pack(side="right")

        # la section "médicaments les plus prescrits" prend une hauteur fixe en bas
        ttk.Label(self, text="Médicaments les plus prescrits", style="Titre.TLabel").pack(anchor="w", pady=(2, 0))
        self.barres = BarresHorizontales(self, height=220)
        self.barres.pack(side="bottom", fill="x", pady=(2, 4))

        # le milieu (histogramme + anneau) prend tout l'espace vertical restant
        milieu = ttk.Frame(self)
        milieu.pack(fill="both", expand=True, pady=2)
        milieu.columnconfigure(0, weight=3)
        milieu.columnconfigure(1, weight=2)
        # la ligne 1 (les canvas) doit s'étirer verticalement
        milieu.rowconfigure(1, weight=1)

        ttk.Label(milieu, text="Chiffre d'affaires encaissé par mois (MAD)",
                  style="Titre.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(milieu, text="Répartition de mes visites",
                  style="Titre.TLabel").grid(row=0, column=1, sticky="w")

        # hauteur initiale plus grande, les canvas s'adaptent ensuite avec <Configure>
        self.histogramme = Histogramme(milieu, height=260)
        self.histogramme.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        self.anneau = Anneau(milieu, height=260)
        self.anneau.grid(row=1, column=1, sticky="nsew")

    def rafraichir(self):
        rdvs = self.app.rdv.afficher_par_medecin(self.app.user.id) or []
        pat = self.app.utilisateurs.afficher_patients() or []
        actifs = sum(1 for p in pat if lire_col(p, "actif", 1))

        honores = [r for r in rdvs if lire_col(r, "statut") == "HONORE"]
        ca = sum(float(lire_col(r, "montant", 0) or 0) for r in honores
                 if str(lire_col(r, "paiement")).lower() == "paye")
        impayes = sum(float(lire_col(r, "montant", 0) or 0) for r in honores
                      if str(lire_col(r, "paiement")).lower() != "paye")
        alertes = self.app.stats.stock_en_alerte()
        demandes = sum(1 for r in rdvs if lire_col(r, "statut") == "DEMANDE")

        self.chiffres["patients"].config(text=str(actifs))
        self.chiffres["consultations"].config(text=str(len(honores)))
        self.chiffres["ca"].config(text=f"{int(ca)} MAD")
        self.chiffres["impayes"].config(text=f"{int(impayes)} MAD")
        self.chiffres["alertes"].config(text=str(alertes))
        self.chiffres["demandes"].config(text=str(demandes))

        # 1. Chiffre d'affaires par mois
        mois_ca = {}
        for r in honores:
            if str(lire_col(r, "paiement")).lower() == "paye":
                d_str = str(lire_col(r, "date_heure"))[:7]
                mois_ca[d_str] = mois_ca.get(d_str, 0.0) + float(lire_col(r, "montant", 0) or 0)
        donnees_hist = [(k[5:], v) for k, v in sorted(mois_ca.items())]
        self.histogramme.dessiner(donnees_hist or [("Total", ca)])

        # 2. Répartition par statut
        stats_rep = {"PLANIFIE": 0, "DEMANDE": 0, "HONORE": 0, "ANNULE": 0}
        for r in rdvs:
            s = lire_col(r, "statut")
            if s in stats_rep:
                stats_rep[s] += 1
        self.anneau.dessiner(stats_rep)

        # 3. Médicaments prescrits
        comptes = {}
        for r in honores:
            txt = lire_col(r, "ordonnance")
            if txt:
                try:
                    for l in json.loads(txt):
                        comptes[l["nom"]] = comptes.get(l["nom"], 0) + int(l.get("qte", 1))
                except Exception:
                    pass
        top = sorted(comptes.items(), key=lambda x: x[1], reverse=True)[:5]
        self.barres.dessiner(top)

    def sauvegarder(self):
        try:
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = f"MediGest_backup_{now_str}.db"
            shutil.copy2("MediGest.db", dest)
            messagebox.showinfo("MediGest", f"Sauvegarde créée avec succès :\n{dest}")
        except Exception as e:
            messagebox.showwarning("MediGest", f"Échec de la sauvegarde : {e}")


 
# 6. ONGLETS DU PATIENT
 

#cette partie est fait sans ai
class OngletMesRendezVous(Onglet):
    # onglet pour que le patient demande un rendez-vous

    def construire(self):
        cadre = ttk.LabelFrame(self, text="Demander un rendez-vous (le médecin devra le confirmer)", padding=6)
        cadre.pack(fill="x", pady=4)
        self.medecin, self.jour = tk.StringVar(), tk.StringVar(value=horloge.aujourdhui())
        self.heure, self.motif = tk.StringVar(), tk.StringVar()

        self.liste_med = ttk.Combobox(cadre, textvariable=self.medecin, state="readonly", width=22)
        self.liste_med.pack(side="left", padx=4)

        entree_date = ttk.Entry(cadre, textvariable=self.jour, width=10)
        entree_date.pack(side="left", padx=4)
        entree_date.bind("<FocusOut>", lambda _: self.maj_creneaux())

        self.liste_heures = ttk.Combobox(cadre, textvariable=self.heure, state="readonly", width=6)
        self.liste_heures.pack(side="left", padx=4)

        ttk.Entry(cadre, textvariable=self.motif, width=14).pack(side="left", padx=4)
        ttk.Button(cadre, text="Demander", style="Action.TButton",
                   command=self.demander).pack(side="left", padx=6)

        ttk.Button(self, text="Annuler le rendez-vous sélectionné",
                   style="Danger.TButton", command=self.annuler).pack(side="bottom", anchor="e", pady=4)

        cols = [
            ("date_heure", "Date et heure", 130), ("medecin", "Médecin", 150),
            ("specialite", "Spécialité", 140), ("motif", "Motif", 150),
            ("statut", "Statut", 90)
        ]
        self.table = Table(self, cols, hauteur=6)
        self.table.pack(fill="both", expand=True, pady=4)

    def rafraichir(self):
        meds = self.app.utilisateurs.afficher_medecins() or []
        self.d_meds = {
            f"Dr {lire_col(m, 'prenom')} {str(lire_col(m, 'nom')).upper()} — {lire_col(m, 'specialite')}": lire_col(m, "id_user")
            for m in meds
        }
        self.liste_med["values"] = list(self.d_meds.keys())
        if self.d_meds and not self.medecin.get():
            self.medecin.set(list(self.d_meds.keys())[0])
        self.maj_creneaux()

        rdvs = self.app.rdv.afficher_par_patient(self.app.user.id) or []
        lignes = []
        for r in rdvs:
            m_obj = self.app.utilisateurs.chercher_par_id(lire_col(r, "id_medecin"))
            m_nom = f"Dr {lire_col(m_obj, 'prenom')} {str(lire_col(m_obj, 'nom')).upper()}" if m_obj else ""
            lignes.append({
                "id": lire_col(r, "id_rendezvous"),
                "date_heure": lire_col(r, "date_heure"),
                "medecin": m_nom,
                "specialite": lire_col(m_obj, "specialite") if m_obj else "",
                "motif": lire_col(r, "motif"),
                "statut": lire_col(r, "statut")
            })
        self.table.charger(lignes, lambda r: r["statut"])

    def maj_creneaux(self):
        id_m = self.d_meds.get(self.medecin.get())
        j = self.jour.get().strip()
        if not id_m or not j:
            self.liste_heures["values"] = []
            return
        occupes = set()
        for r in (self.app.rdv.afficher_par_medecin(id_m) or []):
            if lire_col(r, "statut") != "ANNULE" and str(lire_col(r, "date_heure")).startswith(j):
                occupes.add(str(lire_col(r, "date_heure"))[11:16])
        libres = [c for c in CRENEAUX_BASE if c not in occupes]
        self.liste_heures["values"] = libres
        if libres and not self.heure.get():
            self.heure.set(libres[0])

    def demander(self):
        id_m = self.d_meds.get(self.medecin.get())
        if not id_m or not self.heure.get():
            messagebox.showinfo("MediGest", "Choisissez un médecin, une date et un créneau valide.")
            return
        def op():
            # Limite de 2 demandes en attente
            mes = self.app.rdv.afficher_par_patient(self.app.user.id) or []
            if sum(1 for r in mes if lire_col(r, "statut") == "DEMANDE") >= 2:
                raise ValueError("Vous avez déjà 2 demandes de rendez-vous en attente.")
            dh = f"{self.jour.get().strip()} {self.heure.get().strip()}"
            self.app.rdv.ajouter_rdv(self.app.user.id, id_m, dh, self.motif.get().strip() or "Consultation")
        self.agir(op)

    def annuler(self):
        ident = self.selection_ou_message(self.table)
        if not ident:
            return
        r = self.app.rdv.chercher_par_id(ident)
        def op():
            try:
                date_rdv = datetime.strptime(str(lire_col(r, "date_heure")), "%Y-%m-%d %H:%M")
                if date_rdv - datetime.now() < timedelta(hours=24):
                    raise ValueError("Annulation impossible à moins de 24 heures du rendez-vous.")
            except ValueError as ve:
                raise ve
            except Exception:
                pass
            self.app.rdv.annuler_rdv(ident)
        self.agir(op)


#cette partie est fait sans ai
class OngletMesOrdonnances(Onglet):
    # onglet pour voir ses ordonnances et les imprimer

    def construire(self):
        cols = [("date_heure", "Date", 140), ("medecin", "Médecin", 140), ("diagnostic", "Diagnostic", 260)]
        self.table = Table(self, cols, hauteur=5)
        self.table.pack(fill="x", pady=2)
        self.table.surselection(self.afficher)

        ttk.Label(self, text="Ordonnance", style="Titre.TLabel").pack(anchor="w", pady=(4, 0))
        self.texte = tk.Text(self, height=8, state="disabled", bg="#f9fafb")
        self.texte.pack(fill="both", expand=True, pady=2)

        ttk.Button(self, text="Imprimer l'ordonnance", command=self.imprimer).pack(anchor="e", pady=2)

    def rafraichir(self):
        rdvs = self.app.rdv.afficher_par_patient(self.app.user.id) or []
        lignes = []
        for r in rdvs:
            if lire_col(r, "statut") == "HONORE" and lire_col(r, "ordonnance"):
                m_obj = self.app.utilisateurs.chercher_par_id(lire_col(r, "id_medecin"))
                lignes.append({
                    "id": lire_col(r, "id_rendezvous"),
                    "date_heure": str(lire_col(r, "date_heure"))[:10],
                    "medecin": f"Dr {lire_col(m_obj, 'prenom')} {str(lire_col(m_obj, 'nom')).upper()}" if m_obj else "",
                    "diagnostic": lire_col(r, "diagnostic")
                })
        self.table.charger(lignes)

    def afficher(self):
        ident = self.table.selection()
        if not ident:
            return
        r = self.app.rdv.chercher_par_id(ident)
        txt = lire_col(r, "ordonnance")
        corps = "Aucun médicament prescrit."
        if txt:
            try:
                lignes = json.loads(txt)
                corps = "\n".join(f"• {l['nom']} — {l['qte']} boîte(s) — {l['posologie']}" for l in lignes)
            except Exception:
                pass
        self.texte.config(state="normal")
        self.texte.delete("1.0", "end")
        self.texte.insert("1.0", corps)
        self.texte.config(state="disabled")

    def imprimer(self):
        ident = self.selection_ou_message(self.table)
        if ident:
            html_txt = self.app.generer_html(ident, "ordonnance")
            exports.ouvrir_dans_navigateur(html_txt)


#cette partie est fait sans ai
class OngletMesFactures(Onglet):
    # onglet pour voir les factures et ce qu'il reste a payer

    def construire(self):
        cols = [
            ("date", "Date", 100), ("medecin", "Médecin", 150),
            ("montant", "Montant (MAD)", 110), ("statut", "Statut", 90),
            ("mode", "Paiement", 100)
        ]
        self.table = Table(self, cols, hauteur=10)
        self.table.pack(fill="both", expand=True, pady=4)

        pied = ttk.Frame(self)
        pied.pack(fill="x", pady=4)
        self.reste = ttk.Label(pied, style="Alerte.TLabel")
        self.reste.pack(side="left")
        ttk.Button(pied, text="Imprimer la facture sélectionnée",
                   command=self.imprimer).pack(side="right")

    def rafraichir(self):
        rdvs = self.app.rdv.afficher_par_patient(self.app.user.id) or []
        lignes = []
        reste = 0.0
        for r in rdvs:
            if lire_col(r, "statut") == "HONORE":
                m_obj = self.app.utilisateurs.chercher_par_id(lire_col(r, "id_medecin"))
                paye = str(lire_col(r, "paiement", "impaye")).lower() == "paye"
                mont = float(lire_col(r, "montant", 0) or 0)
                if not paye:
                    reste += mont
                lignes.append({
                    "id": lire_col(r, "id_rendezvous"),
                    "date": str(lire_col(r, "date_heure"))[:10],
                    "medecin": f"Dr {lire_col(m_obj, 'prenom')} {str(lire_col(m_obj, 'nom')).upper()}" if m_obj else "",
                    "montant": "%.2f" % mont,
                    "statut": "PAYE" if paye else "IMPAYE",
                    "mode": lire_col(r, "mode_paiement") or "-"
                })
        self.table.charger(lignes, lambda l: "HONORE" if l["statut"] == "PAYE" else "DEMANDE")
        self.reste.config(text="Reste à payer : %.2f MAD" % reste)

    def imprimer(self):
        ident = self.selection_ou_message(self.table)
        if ident:
            html_txt = self.app.generer_html(ident, "facture")
            exports.ouvrir_dans_navigateur(html_txt)


 
#   ONGLET COMMUN : PROFIL
 

#cette partie est fait sans ai
class OngletProfil(Onglet):
    # onglet pour modifier ses coordonnees et son mot de passe

    def construire(self):
        u = self.app.user
        identite = ttk.LabelFrame(self, text="Mon identité (non modifiable)", padding=4)
        identite.pack(fill="x", pady=2)
        for lib, val in (("Nom", u.nom_complet()), ("CIN", u.cin), ("Login", u.login)):
            ttk.Label(identite, text=f"{lib} : {val}",
                      font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=8, pady=1)

        coords = ttk.LabelFrame(self, text="Mes coordonnées", padding=4)
        coords.pack(fill="x", pady=3)
        self.tel = champ(coords, "Téléphone", 0, largeur=24)
        self.mail = champ(coords, "E-mail", 1, largeur=24)
        self.adresse = champ(coords, "Adresse", 2, largeur=24)
        self.tel.set(u.telephone or "")
        self.mail.set(u.email or "")
        self.adresse.set(u.adresse or "")
        ttk.Button(coords, text="Enregistrer les coordonnées", style="Action.TButton",
                   command=self.enregistrer).grid(row=3, column=1, pady=3)

        secret = ttk.LabelFrame(self, text="Changer mon mot de passe", padding=4)
        secret.pack(fill="x", pady=3)
        self.ancien = champ(secret, "Ancien mot de passe", 0, 0, largeur=14, show="*")
        self.nouveau = champ(secret, "Nouveau mot de passe", 0, 2, largeur=14, show="*")
        self.confirme = champ(secret, "Confirmer le mot de passe", 1, 0, largeur=14, show="*")
        ttk.Button(secret, text="Changer le mot de passe", style="Action.TButton",
                   command=self.changer_mdp).grid(row=1, column=2, columnspan=2, sticky="w", padx=6, pady=2)

    def enregistrer(self):
        def op():
            self.app.utilisateurs.modifier_utilisateur(
                self.app.user.id, telephone=self.tel.get().strip() or None,
                email=self.mail.get().strip(), adresse=self.adresse.get().strip() or None
            )
            self.app.user.telephone = self.tel.get().strip()
            self.app.user.email = self.mail.get().strip()
            self.app.user.adresse = self.adresse.get().strip()
            messagebox.showinfo("MediGest", "Coordonnées mises à jour avec succès.")
        self.agir(op)

    def changer_mdp(self):
        if self.nouveau.get() != self.confirme.get():
            messagebox.showwarning("MediGest", "La confirmation ne correspond pas au nouveau mot de passe.")
            return
        def op():
            self.app.utilisateurs.changer_mot_de_passe(
                self.app.user.id, self.ancien.get(), self.nouveau.get()
            )
            self.ancien.set("")
            self.nouveau.set("")
            self.confirme.set("")
            messagebox.showinfo("MediGest", "Mot de passe modifié avec succès.")
        self.agir(op)


 
#   DICTIONNAIRE DE DISPATCH DES ONGLETS
 

ONGLETS = {
    "Patients": OngletPatients,
    "Rendez-vous": OngletRendezVous,
    "Consultations": OngletConsultations,
    "Stock": OngletStock,
    "Facturation": OngletFacturation,
    "Tableau de bord": OngletTableauDeBord,
    "Mes rendez-vous": OngletMesRendezVous,
    "Mes ordonnances": OngletMesOrdonnances,
    "Mes factures": OngletMesFactures,
    "Mon profil": OngletProfil,
}


 
#   FENÊTRE PRINCIPALE (APPLICATION)
 

#cette partie est fait sans ai
class Application(tk.Tk):
    # fenetre principale qui ouvre le login puis les onglets

    def __init__(self, db):
        super().__init__()
        self.title("MediGest — Clinique Al Amal")
        ecran_l = self.winfo_screenwidth()
        ecran_h = self.winfo_screenheight()
        base_l = min(1200, max(1080, int(ecran_l * 0.75)))
        base_h = min(780, max(680, int(ecran_h * 0.75)))
        self.geometry(f"{base_l}x{base_h}")
        self.minsize(1020, 660)
        appliquer_style(self)

        self.db = db
        self.utilisateurs = UtilisateurDAO(db)
        self.medicaments = MedicamentDAO(db)
        self.rdv = RendezVousDAO(db)
        self.stats = StatistiquesDAO(db)

        self.user = None
        self.page = None
        self.carnet = None

        self.afficher_connexion()

    def afficher_connexion(self):
        # formulaire de connexion identifiant et mot de passe
        if self.page:
            self.page.destroy()
        self.user = None

        self.page = ttk.Frame(self, padding=40)
        self.page.pack(expand=True)

        ttk.Label(self.page, text="+ MediGest", font=("TkDefaultFont", 26, "bold"),
                  foreground=VERT).pack()
        ttk.Label(self.page, text="Clinique Al Amal — gestion des rendez-vous et des dossiers").pack(pady=(0, 20))

        self.login, self.mdp = tk.StringVar(), tk.StringVar()
        ttk.Label(self.page, text="Identifiant").pack(anchor="w")
        entree = ttk.Entry(self.page, textvariable=self.login, width=36)
        entree.pack()

        ttk.Label(self.page, text="Mot de passe").pack(anchor="w", pady=(10, 0))
        ttk.Entry(self.page, textvariable=self.mdp, show="*", width=36).pack()

        ttk.Button(self.page, text="Se connecter", style="Action.TButton",
                   command=self.connecter).pack(fill="x", pady=16)

        ttk.Label(self.page, text="Comptes d'essai : dr.alaoui / medecin123  ·  s.tazi / patient123",
                  foreground="#6b7280").pack()

        self.bind("<Return>", lambda _evt: self.connecter() if self.user is None else None)
        entree.focus_set()

    def connecter(self):
        # verifie le compte dans la base et ouvre la session
        l = self.login.get().strip()
        m = self.mdp.get()
        row = self.utilisateurs.authentifier(l, m)
        if not row:
            messagebox.showwarning("MediGest", "Identifiant ou mot de passe incorrect.")
            return
        user_obj = objet_vers_user(row)
        self.ouvrir_session(user_obj)

    def ouvrir_session(self, user):
        # ouvre la session et charge les onglets selon le role
        self.user = user
        self.page.destroy()

        if self.winfo_width() < 1050 or self.winfo_height() < 660:
            ecran_l = self.winfo_screenwidth()
            ecran_h = self.winfo_screenheight()
            base_l = min(1200, max(1080, int(ecran_l * 0.75)))
            base_h = min(780, max(680, int(ecran_h * 0.75)))
            self.geometry(f"{base_l}x{base_h}")

        self.page = ttk.Frame(self)
        self.page.pack(fill="both", expand=True)

        # Barre verte en haut
        barre = tk.Frame(self.page, bg=VERT)
        barre.pack(fill="x")
        tk.Label(barre, text="+ MediGest", bg=VERT, fg="white",
                 font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=10, pady=4)
        ttk.Button(barre, text="Déconnexion",
                   command=self.afficher_connexion).pack(side="right", padx=6, pady=2)
        tk.Label(barre, text=f"{user.nom_complet()} [{user.role.upper()}]",
                 bg=VERT, fg="white").pack(side="right", padx=10)

        # Carnet d'onglets polymorphique
        self.carnet = ttk.Notebook(self.page)
        self.carnet.pack(fill="both", expand=True, padx=6, pady=6)

        for nom in user.ecrans():
            if nom in ONGLETS:
                self.carnet.add(ONGLETS[nom](self.carnet, self), text=nom)

        self.carnet.bind("<<NotebookTabChanged>>", lambda _: self.rafraichir_courant())
        self.message_accueil()

    def rafraichir_courant(self):
        courant = self.carnet.nametowidget(self.carnet.select())
        if hasattr(courant, "rafraichir"):
            courant.rafraichir()

    def rafraichir_tout(self):
        for o in self.carnet.winfo_children():
            if hasattr(o, "rafraichir"):
                o.rafraichir()

    def message_accueil(self):
        # message de bienvenue qui resume les rendez-vous du jour
        aujourdhui = horloge.aujourdhui()
        if self.user.role == "medecin":
            rdvs = self.rdv.afficher_par_medecin(self.user.id) or []
            n_jour = sum(1 for r in rdvs if str(lire_col(r, "date_heure")).startswith(aujourdhui))
            n_dem = sum(1 for r in rdvs if lire_col(r, "statut") == "DEMANDE")
            n_stk = self.stats.stock_en_alerte()
            lignes = [
                f"{n_jour} rendez-vous prévu(s) aujourd'hui",
                f"{n_dem} demande(s) de rendez-vous à confirmer",
                f"{n_stk} médicament(s) sous le seuil d'alerte"
            ]
        else:
            rdvs = self.rdv.afficher_par_patient(self.user.id) or []
            futurs = [r for r in rdvs if str(lire_col(r, "date_heure")) >= aujourdhui
                      and lire_col(r, "statut") in ("PLANIFIE", "DEMANDE")]
            if futurs:
                lignes = [f"Prochain rendez-vous : {lire_col(futurs[0], 'date_heure')}"]
            else:
                lignes = ["Aucun rendez-vous prévu prochainement."]
        messagebox.showinfo(f"Bonjour {self.user.nom_complet()}",
                            "Résumé de votre journée :\n\n• " + "\n• ".join(lignes))

    def generer_html(self, id_rdv, quoi):
        # cree la page html prete a imprimer dans le navigateur
        r = self.rdv.chercher_par_id(id_rdv)
        p = self.utilisateurs.chercher_par_id(lire_col(r, "id_patient"))
        m = self.utilisateurs.chercher_par_id(lire_col(r, "id_medecin"))
        e = html.escape
        titre = "Ordonnance Médicale" if quoi == "ordonnance" else "Facture de Consultation"

        corps = f"<h3>Clinique Al Amal</h3><p><b>Médecin :</b> Dr {e(lire_col(m, 'prenom'))} {e(str(lire_col(m, 'nom')).upper())}<br>"
        corps += f"<b>Patient :</b> {e(lire_col(p, 'prenom'))} {e(str(lire_col(p, 'nom')).upper())} (CIN : {e(lire_col(p, 'cin'))})<br>"
        corps += f"<b>Date :</b> {e(lire_col(r, 'date_heure'))}</p>"

        if quoi == "ordonnance":
            corps += f"<p><b>Diagnostic :</b> {e(lire_col(r, 'diagnostic') or 'Non spécifié')}</p>"
            txt = lire_col(r, "ordonnance")
            corps += "<table border='1' cellpadding='6' cellspacing='0'><tr><th>Médicament</th><th>Quantité</th><th>Posologie</th></tr>"
            if txt:
                try:
                    for l in json.loads(txt):
                        corps += f"<tr><td>{e(l['nom'])}</td><td>{l['qte']}</td><td>{e(l['posologie'])}</td></tr>"
                except Exception:
                    pass
            corps += "</table>"
        else:
            mont = float(lire_col(r, "montant", 0.0) or 0.0)
            paye = str(lire_col(r, "paiement", "impaye")).lower() == "paye"
            corps += f"<p><b>Montant total :</b> {mont:.2f} MAD<br>"
            corps += f"<b>Statut :</b> {'Payé' if paye else 'En attente de paiement'}<br>"
            if paye:
                corps += f"<b>Mode de règlement :</b> {e(lire_col(r, 'mode_paiement'))} (le {lire_col(r, 'date_paiement')})</p>"

        return f"<!doctype html><html><head><meta charset='utf-8'><title>{titre}</title></head><body><h1>{titre}</h1>{corps}</body></html>"
