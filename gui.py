"""gui.py : interface Tkinter de MediGest.

Nouveau design : menu latéral, cartes blanches, tableau de bord avec graphiques Canvas.
Ce fichier utilise les classes EXISTANTES du projet, sans les modifier :
    dao.py     -> UtilisateurDAO, RendezVousDAO, MedicamentDAO, StatistiquesDAO
    models.py  -> Patient, Medecin, Medicament, LigneOrdonnance, Ordonnance
"""
import html
import json
import sqlite3
import unicodedata
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk, messagebox
from tkinter import font as tkfont

import exports
import horloge
from dao import UtilisateurDAO, MedicamentDAO, RendezVousDAO, StatistiquesDAO
from models import Patient, Medecin, Medicament, LigneOrdonnance, Ordonnance

# ====================================================================== palette
VERT, VERT_FONCE, VERT_CLAIR = "#0f766e", "#115e59", "#14b8a6"
MENTHE = "#99d5cd"
LATERAL, LATERAL_SURVOL = "#0c3b38", "#14504b"          # menu de gauche
ROUGE, ROUGE_FONCE = "#dc2626", "#b91c1c"
ORANGE, JAUNE = "#f97316", "#eab308"
FOND, CARTE = "#f1f5f4", "#ffffff"
TEXTE, TEXTE_DOUX, BORDURE = "#1f2937", "#6b7280", "#dbe4e2"
BOUTON, BOUTON_SURVOL, BOUTON_APPUI = "#e7eeed", "#d6e3e0", "#c9d8d5"

COULEURS_STATUT = {"PLANIFIE": "#fef9c3", "DEMANDE": "#ffedd5", "HONORE": "#dcfce7", "ANNULE": "#eceff1"}
COULEURS_ANNEAU = {"PLANIFIE": JAUNE, "DEMANDE": ORANGE, "HONORE": "#16a34a", "ANNULE": "#9ca3af"}
LIBELLE_STATUT = {"PLANIFIE": "Planifié", "DEMANDE": "Demande", "HONORE": "Honoré", "ANNULE": "Annulé"}

MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS_LONGS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
              "octobre", "novembre", "décembre"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

# Créneaux de 30 min entre 08:00 et 17:30 (RG4)
CRENEAUX = ["%02d:%02d" % (h, m) for h in range(8, 18) for m in (0, 30)]

ECRANS_MEDECIN = ["Patients", "Rendez-vous", "Consultations", "Stock", "Facturation",
                  "Tableau de bord", "Mon profil"]
ECRANS_PATIENT = ["Mes rendez-vous", "Mes ordonnances", "Mes factures", "Mon profil"]

POLICE = "TkDefaultFont"       # remplacée par la meilleure police disponible dans appliquer_style()


def police(taille=10, gras=False):
    return (POLICE, taille, "bold") if gras else (POLICE, taille)


# ====================================================================== petites fonctions utiles
def lire(ligne, cle, defaut=""):
    """Lit une colonne d'une ligne sqlite3.Row (ou d'un dict) sans planter si elle est vide."""
    try:
        valeur = ligne[cle]
    except (KeyError, IndexError):
        return defaut
    return defaut if valeur is None else valeur


def sans_accents(texte):
    texte = unicodedata.normalize("NFD", str(texte).lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def date_longue(d):
    return "%s %d %s %d" % (JOURS[d.weekday()].capitalize(), d.day, MOIS_LONGS[d.month - 1], d.year)


def message_erreur(erreur):
    """Transforme une erreur technique en message clair pour l'utilisateur."""
    texte = str(erreur)
    for motif, message in (("Users.cin", "Ce CIN est déjà enregistré."),
                           ("Users.login", "Cet identifiant existe déjà."),
                           ("Users.email", "Cette adresse e-mail est déjà utilisée."),
                           ("Users.telephone", "Ce numéro de téléphone est déjà utilisé."),
                           ("medicament.designation", "Ce médicament existe déjà.")):
        if motif in texte:
            return message
    return texte


def verifier_date(texte):
    try:
        return horloge.convertir_date(texte)
    except ValueError:
        raise ValueError("Date invalide : utilisez le format AAAA-MM-JJ (ex. 2026-11-05).")


def en_nombre(texte, nom, entier=False):
    try:
        valeur = int(texte) if entier else float(str(texte).replace(",", "."))
    except ValueError:
        raise ValueError(nom + " doit être un nombre" + (" entier." if entier else "."))
    if valeur < 0:
        raise ValueError(nom + " ne peut pas être négatif.")
    return valeur


def exiger(donnees, champs):
    for cle, nom in champs:
        if not donnees.get(cle):
            raise ValueError(nom + " est obligatoire.")


def construire_utilisateur(ligne):
    """Transforme la ligne SQL renvoyée par authentifier() en objet Medecin ou Patient."""
    commun = (ligne["id_user"], ligne["login"], ligne["nom"], ligne["prenom"], ligne["cin"],
              ligne["telephone"], ligne["email"], ligne["adresse"])
    if str(ligne["role"]).lower() == "medecin":
        return Medecin(*commun, "Medecin", ligne["specialite"], ligne["tarif"])
    try:
        naissance = horloge.convertir_date(ligne["date_naissance"])
    except (ValueError, TypeError):
        naissance = date.today()
    return Patient(*commun, naissance, ligne["sexe"], ligne["allergies"], "Patient")


def est_medecin(user):
    return isinstance(user, Medecin)


def nom_affiche(user):
    base = "%s %s" % (user.prenom, str(user.nom).upper())
    return "Dr " + base if est_medecin(user) else base


def tarif_de(user):
    valeur = getattr(user, "Tarif", None)
    if valeur is None:
        valeur = getattr(user, "tarif", 0)
    return float(valeur or 0)


def role_de(user):
    return "MÉDECIN" if est_medecin(user) else "PATIENT"


def initiales(user):
    return (str(user.prenom)[:1] + str(user.nom)[:1]).upper()


def lire_ordonnance(texte):
    """Ordonnance stockée en JSON dans rendez_vous.ordonnance -> liste de dictionnaires."""
    if not texte:
        return []
    try:
        contenu = json.loads(texte)
    except (ValueError, TypeError):
        return [{"nom": str(texte), "qte": "", "posologie": ""}]
    if isinstance(contenu, dict):
        contenu = contenu.get("lignes", [])
    return [l for l in contenu if isinstance(l, dict)]


def statut_paiement(ligne):
    return "PAYE" if str(lire(ligne, "paiement", "impaye")).lower() == "paye" else "IMPAYE"


# ---------------------------------------------------------------- règles de gestion côté interface
def creneaux_libres(app, id_medecin, jour):
    """Horaires encore libres pour ce médecin ce jour-là (liste vide si dimanche ou jour passé)."""
    jour_date = verifier_date(jour)
    if jour_date < date.today() or jour_date.weekday() == 6:
        return []
    pris = {r["date_heure"][11:16] for r in app.rdv.afficher_par_medecin(id_medecin)
            if r["statut"] != "ANNULE" and r["date_heure"][:10] == jour}
    maintenant = horloge.maintenant()
    libres = []
    for heure in CRENEAUX:
        if heure in pris:
            continue
        if jour_date == date.today() and jour + " " + heure <= maintenant:
            continue
        libres.append(heure)
    return libres


def verifier_creneau(app, id_medecin, id_patient, jour, heure, motif):
    """RG3/RG4 : créneau valide, libre pour le médecin ET pour le patient. Renvoie 'AAAA-MM-JJ HH:MM'."""
    if not motif.strip():
        raise ValueError("Le motif est obligatoire.")
    if not heure:
        raise ValueError("Choisissez un horaire libre.")
    if heure not in creneaux_libres(app, id_medecin, jour):
        raise ValueError("Ce créneau n'est pas disponible (passé, dimanche ou déjà pris).")
    date_heure = jour + " " + heure
    for r in app.rdv.afficher_par_patient(id_patient):
        if r["statut"] != "ANNULE" and r["date_heure"] == date_heure:
            raise ValueError("Le patient a déjà un rendez-vous à cette heure.")
    return date_heure


def alerte_allergie(patient, medicament):
    """RG13 : message si le médicament appartient à une famille à laquelle le patient est allergique."""
    allergies = sans_accents(lire(patient, "allergies"))
    if not allergies:
        return None
    cible = sans_accents(medicament["famille_med"] + " " + medicament["designation"])
    for mot in allergies.replace(";", ",").replace("/", ",").split(","):
        mot = mot.strip()
        if len(mot) >= 4 and (mot in cible or mot.rstrip("s") in cible):
            return "Le patient est allergique à : %s.\n(%s — famille %s)" % (
                lire(patient, "allergies"), medicament["designation"], medicament["famille_med"])
    return None


# ====================================================================== style ttk
def appliquer_style(racine):
    global POLICE
    disponibles = set(tkfont.families(racine))
    POLICE = next((p for p in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "Noto Sans", "DejaVu Sans")
                   if p in disponibles), tkfont.nametofont("TkDefaultFont").actual("family"))
    for nom in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nom).configure(family=POLICE, size=10)

    racine.configure(bg=FOND)
    racine.option_add("*TCombobox*Listbox.background", CARTE)
    racine.option_add("*TCombobox*Listbox.foreground", TEXTE)
    racine.option_add("*TCombobox*Listbox.selectBackground", VERT)
    racine.option_add("*TCombobox*Listbox.selectForeground", "white")
    racine.option_add("*TCombobox*Listbox.font", police(10))

    st = ttk.Style(racine)
    st.theme_use("clam")
    st.configure(".", background=FOND, foreground=TEXTE, font=police(10), bordercolor=BORDURE,
                 troughcolor=FOND, focuscolor=FOND)

    # --- cadres et étiquettes
    st.configure("TFrame", background=FOND)
    st.configure("Carte.TFrame", background=CARTE, relief="solid", borderwidth=1, bordercolor=BORDURE,
                 lightcolor=BORDURE, darkcolor=BORDURE)
    st.configure("Interne.TFrame", background=CARTE)
    st.configure("TLabel", background=FOND, foreground=TEXTE)
    st.configure("Doux.TLabel", foreground=TEXTE_DOUX)
    st.configure("Alerte.TLabel", foreground=ROUGE, font=police(10, True))
    st.configure("Titre.TLabel", foreground=VERT, font=police(10, True))
    st.configure("Carte.TLabel", background=CARTE)
    st.configure("CarteDoux.TLabel", background=CARTE, foreground=TEXTE_DOUX, font=police(9))
    st.configure("CarteGras.TLabel", background=CARTE, font=police(10, True))
    st.configure("CarteTitre.TLabel", background=CARTE, foreground=TEXTE, font=police(20, True))
    st.configure("Section.TLabel", background=CARTE, foreground=VERT, font=police(11, True))
    st.configure("Erreur.TLabel", background=CARTE, foreground=ROUGE, font=police(9))
    st.configure("Chiffre.TLabel", background=CARTE, foreground=TEXTE, font=police(20, True))
    for nom, fond in (("TCheckbutton", FOND), ("TRadiobutton", FOND),
                      ("Carte.TCheckbutton", CARTE), ("Carte.TRadiobutton", CARTE)):
        st.configure(nom, background=fond, foreground=TEXTE)
        st.map(nom, background=[("active", fond)], indicatorcolor=[("selected", VERT), ("!selected", CARTE)])

    # --- boutons : gris par défaut, vert pour l'action, rouge pour le danger
    def bouton(nom, fond, survol, appui, texte, bord):
        st.configure(nom, padding=(14, 7), background=fond, foreground=texte, bordercolor=bord,
                     lightcolor=fond, darkcolor=fond, focuscolor=fond, relief="flat", font=police(10))
        st.map(nom,
               background=[("disabled", "#eef2f1"), ("pressed", appui), ("active", survol)],
               lightcolor=[("pressed", appui), ("active", survol)],
               darkcolor=[("pressed", appui), ("active", survol)],
               foreground=[("disabled", "#9ca3af")])
    bouton("TButton", BOUTON, BOUTON_SURVOL, BOUTON_APPUI, TEXTE, BORDURE)
    bouton("Action.TButton", VERT, VERT_FONCE, "#134e4a", "white", VERT)
    bouton("Danger.TButton", ROUGE, ROUGE_FONCE, "#7f1d1d", "white", ROUGE)
    bouton("Lateral.TButton", LATERAL_SURVOL, "#1b6660", "#0f4f49", "white", LATERAL_SURVOL)

    # --- champs de saisie
    champ_st = dict(padding=5, fieldbackground=CARTE, bordercolor=BORDURE, lightcolor=CARTE, darkcolor=CARTE)
    st.configure("TEntry", **champ_st)
    st.map("TEntry", bordercolor=[("focus", VERT)], lightcolor=[("focus", VERT)])
    st.configure("TCombobox", arrowcolor=TEXTE_DOUX, background=BOUTON, arrowsize=16, **champ_st)
    st.map("TCombobox", bordercolor=[("focus", VERT)], lightcolor=[("focus", VERT)],
           fieldbackground=[("readonly", CARTE)], selectbackground=[("readonly", CARTE)],
           selectforeground=[("readonly", TEXTE)], background=[("active", BOUTON_SURVOL)])
    st.configure("TSpinbox", arrowcolor=TEXTE_DOUX, background=BOUTON, arrowsize=14, **champ_st)
    st.map("TSpinbox", bordercolor=[("focus", VERT)], lightcolor=[("focus", VERT)])

    # --- tableaux
    st.configure("Treeview", background=CARTE, fieldbackground=CARTE, foreground=TEXTE, rowheight=28,
                 bordercolor=BORDURE, lightcolor=BORDURE, darkcolor=BORDURE, borderwidth=1, font=police(10))
    st.map("Treeview", background=[("selected", VERT)], foreground=[("selected", "white")])
    st.configure("Treeview.Heading", background="#e6efed", foreground=VERT_FONCE, relief="flat",
                 padding=(8, 8), font=police(10, True), bordercolor=BORDURE, lightcolor="#e6efed",
                 darkcolor="#e6efed")
    st.map("Treeview.Heading", background=[("active", "#d6e5e2")])

    # --- ascenseurs
    st.configure("Vertical.TScrollbar", background="#c3d1ce", troughcolor=FOND, bordercolor=FOND,
                 lightcolor="#c3d1ce", darkcolor="#c3d1ce", arrowcolor=TEXTE_DOUX, relief="flat", arrowsize=14)
    st.map("Vertical.TScrollbar", background=[("active", "#9fb5b1")])


# ====================================================================== composants réutilisables
def carte(parent, **options):
    """Carte blanche à bordure fine."""
    options.setdefault("padding", 16)
    return ttk.Frame(parent, style="Carte.TFrame", **options)


class Table(ttk.Frame):
    """Tableau (Treeview + ascenseur). colonnes = [(cle, titre, largeur), ...]. Chaque ligne est un dict avec 'id'."""

    def __init__(self, parent, colonnes, hauteur=8):
        super().__init__(parent)
        self.colonnes = colonnes
        self.arbre = ttk.Treeview(self, columns=[c[0] for c in colonnes], show="headings",
                                  height=hauteur, selectmode="browse")
        for cle, titre, largeur in colonnes:
            self.arbre.heading(cle, text=titre, anchor="w")
            self.arbre.column(cle, width=largeur, minwidth=40, anchor="w")
        defil = ttk.Scrollbar(self, orient="vertical", command=self.arbre.yview)
        self.arbre.configure(yscrollcommand=defil.set)
        self.arbre.pack(side="left", fill="both", expand=True)
        defil.pack(side="right", fill="y")
        for statut, couleur in COULEURS_STATUT.items():
            self.arbre.tag_configure(statut, background=couleur)
        self.arbre.tag_configure("ANNULE", background=COULEURS_STATUT["ANNULE"], foreground=TEXTE_DOUX)
        self.arbre.tag_configure("alerte", background="#fee2e2", foreground=ROUGE_FONCE)
        self.arbre.tag_configure("pair", background=CARTE)
        self.arbre.tag_configure("impair", background="#f6f9f8")

    def charger(self, lignes, etiquette=None):
        """Remplace le contenu. etiquette(ligne) -> nom de tag (couleur de la ligne)."""
        ancienne = self.selection()
        self.arbre.delete(*self.arbre.get_children())
        for rang, ligne in enumerate(lignes):
            valeurs = [ligne.get(c[0], "") for c in self.colonnes]
            tag = etiquette(ligne) if etiquette else None
            self.arbre.insert("", "end", iid=str(ligne["id"]), values=valeurs,
                              tags=(tag or ("impair" if rang % 2 else "pair"),))
        if ancienne is not None and self.arbre.exists(str(ancienne)):
            self.arbre.selection_set(str(ancienne))

    def selection(self):
        choix = self.arbre.selection()
        return int(choix[0]) if choix else None

    def surselection(self, fonction):
        self.arbre.bind("<<TreeviewSelect>>", lambda _evt: fonction())


def champ(parent, libelle, ligne, colonne=0, largeur=18, show=None, espace=0):
    """Étiquette + zone de saisie dans une grille; renvoie la variable liée."""
    variable = tk.StringVar()
    ttk.Label(parent, text=libelle, style="Carte.TLabel").grid(row=ligne, column=colonne, sticky="w", padx=(0, 10), pady=4)
    ttk.Entry(parent, textvariable=variable, width=largeur, show=show or "").grid(
        row=ligne, column=colonne + 1, sticky="ew", pady=4, padx=(0, espace))
    return variable


def zone_texte(parent, **options):
    return tk.Text(parent, font=police(10), bg=CARTE, fg=TEXTE, relief="flat", padx=10, pady=8,
                   highlightthickness=1, highlightbackground=BORDURE, highlightcolor=VERT,
                   insertbackground=TEXTE, **options)


def ecrire_texte(zone, texte):
    zone.config(state="normal")
    zone.delete("1.0", "end")
    zone.insert("1.0", texte)
    zone.config(state="disabled")


# ---------------------------------------------------------------- graphiques dessinés sur Canvas
class Graphique(tk.Canvas):
    def __init__(self, parent, vide, **options):
        super().__init__(parent, bg=CARTE, highlightthickness=1, highlightbackground=BORDURE, **options)
        self.donnees = vide
        self.bind("<Configure>", lambda _evt: self.dessiner(self.donnees))

    def message_vide(self):
        self.create_text(self.winfo_width() / 2, self.winfo_height() / 2, text="Pas encore de données",
                         fill=TEXTE_DOUX, font=police(10))


class Histogramme(Graphique):
    def __init__(self, parent, **options):
        super().__init__(parent, [], **options)

    def dessiner(self, donnees):
        self.donnees = donnees
        self.delete("all")
        if not donnees or not any(v for _, v in donnees):
            self.message_vide()
            return
        largeur, hauteur = self.winfo_width(), self.winfo_height()
        marge, haut, bas = 18, 30, 26
        zone = max(hauteur - haut - bas, 1)
        maxi = max(v for _, v in donnees) or 1
        for k in range(4):
            y = haut + zone * k / 3
            self.create_line(marge, y, largeur - marge, y, fill="#e8eeed")
        pas = (largeur - 2 * marge) / len(donnees)
        for i, (libelle, valeur) in enumerate(donnees):
            x0, x1 = marge + i * pas + pas * 0.22, marge + (i + 1) * pas - pas * 0.22
            y1 = hauteur - bas
            y0 = y1 - zone * valeur / maxi
            couleur = VERT if i == len(donnees) - 1 else MENTHE
            self.create_rectangle(x0, y0, x1, y1, fill=couleur, outline="")
            self.create_text((x0 + x1) / 2, y0 - 10, text=str(round(valeur)), fill=TEXTE, font=police(9, True))
            self.create_text((x0 + x1) / 2, hauteur - 12, text=libelle, fill=TEXTE_DOUX, font=police(9))


class Anneau(Graphique):
    def __init__(self, parent, **options):
        super().__init__(parent, {}, **options)

    def dessiner(self, donnees):
        self.donnees = donnees
        self.delete("all")
        total = sum(donnees.values())
        if total == 0:
            self.message_vide()
            return
        largeur, hauteur = self.winfo_width(), self.winfo_height()
        rayon = max(min(largeur // 3, hauteur // 2) - 24, 10)
        cx, cy = largeur // 3, hauteur // 2
        boite = (cx - rayon, cy - rayon, cx + rayon, cy + rayon)
        debut = 90
        for statut, nombre in donnees.items():
            if nombre == 0:
                continue
            angle = min(360 * nombre / total, 359.99)
            self.create_arc(boite, start=debut, extent=-angle, style="arc", width=24,
                            outline=COULEURS_ANNEAU[statut])
            debut -= angle
        self.create_text(cx, cy - 8, text=str(total), fill=TEXTE, font=police(20, True))
        self.create_text(cx, cy + 14, text="visites", fill=TEXTE_DOUX, font=police(9))
        depart = cy - len(donnees) * 11 + 3
        for i, (statut, nombre) in enumerate(donnees.items()):
            y, x = depart + i * 22, 2 * largeur // 3
            self.create_rectangle(x, y, x + 12, y + 12, fill=COULEURS_ANNEAU[statut], outline="")
            self.create_text(x + 20, y + 6, anchor="w", fill=TEXTE, font=police(10),
                             text="%s : %d" % (LIBELLE_STATUT[statut], nombre))


class BarresHorizontales(Graphique):
    def __init__(self, parent, **options):
        super().__init__(parent, [], **options)

    def dessiner(self, donnees):
        self.donnees = donnees
        self.delete("all")
        if not donnees:
            self.message_vide()
            return
        maxi = max(v for _, v in donnees) or 1
        x0 = 180
        zone = max(self.winfo_width() - x0 - 50, 10)
        for i, (nom, valeur) in enumerate(donnees):
            y = 10 + i * 24
            longueur = zone * valeur / maxi
            self.create_text(14, y + 7, anchor="w", text=nom, fill=TEXTE, font=police(9))
            self.create_rectangle(x0, y, x0 + zone, y + 14, fill="#eef3f2", outline="")
            self.create_rectangle(x0, y, x0 + longueur, y + 14, fill=VERT_CLAIR, outline="")
            self.create_text(x0 + longueur + 8, y + 7, anchor="w", text=str(valeur), fill=TEXTE, font=police(9, True))


# ====================================================================== pages (écrans)
class Page(ttk.Frame):
    """Classe mère des écrans : construire() crée les widgets, rafraichir() relit la base."""
    titre, sous_titre = "", ""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.construire()
        self.rafraichir()

    def construire(self):
        pass

    def rafraichir(self):
        pass

    def agir(self, action, succes=None):
        """Exécute une action ; une erreur devient un message clair. Renvoie True si tout s'est bien passé."""
        try:
            action()
        except (ValueError, sqlite3.Error) as erreur:
            messagebox.showwarning("MediGest", message_erreur(erreur))
            return False
        if succes:
            self.app.notifier(succes)
        self.app.rafraichir_tout()
        return True

    def choisir(self, table, message="Sélectionnez d'abord une ligne dans le tableau."):
        identifiant = table.selection()
        if identifiant is None:
            messagebox.showinfo("MediGest", message)
        return identifiant


# ---------------------------------------------------------------- MÉDECIN : patients
class PagePatients(Page):
    titre, sous_titre = "Patients", "Dossiers, comptes et allergies"

    def construire(self):
        self.columnconfigure(0, weight=5)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(0, weight=1)
        gauche = ttk.Frame(self)
        gauche.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        droite = carte(self)
        droite.grid(row=0, column=1, sticky="nsew")

        barre = ttk.Frame(gauche)
        barre.pack(fill="x", pady=(0, 10))
        self.recherche, self.archives = tk.StringVar(), tk.BooleanVar()
        ttk.Label(barre, text="Rechercher").pack(side="left")
        ttk.Entry(barre, textvariable=self.recherche, width=26).pack(side="left", padx=8)
        ttk.Checkbutton(barre, text="Afficher les comptes archivés", variable=self.archives,
                        command=self.rafraichir).pack(side="left", padx=6)
        self.recherche.trace_add("write", lambda *_: self.rafraichir())

        self.table = Table(gauche, [("cin", "CIN", 80), ("nom", "Nom", 85), ("prenom", "Prénom", 85),
                                    ("naissance", "Naissance", 95), ("sexe", "Sexe", 55),
                                    ("telephone", "Téléphone", 100), ("allergies", "Allergies", 100)], 9)
        self.table.pack(fill="both", expand=True)
        self.table.surselection(self.afficher_fiche)
        ttk.Label(gauche, text="Fiche du patient", style="Titre.TLabel").pack(anchor="w", pady=(12, 4))
        self.fiche = zone_texte(gauche, height=6, state="disabled", wrap="word")
        self.fiche.pack(fill="x")
        ttk.Button(gauche, text="Archiver / réactiver le patient sélectionné", style="Danger.TButton",
                   command=self.archiver).pack(anchor="e", pady=(8, 0))

        ttk.Label(droite, text="Nouveau compte patient", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(droite, text="Date de naissance au format AAAA-MM-JJ", style="CarteDoux.TLabel").grid(
            row=13, column=0, columnspan=2, sticky="w", pady=(8, 0))
        droite.columnconfigure(1, weight=1)
        self.v = {}
        champs = (("login", "Identifiant", None), ("mdp", "Mot de passe", "*"), ("nom", "Nom", None),
                  ("prenom", "Prénom", None), ("cin", "CIN", None), ("naissance", "Naissance", None))
        for i, (cle, libelle, masque) in enumerate(champs, start=1):
            self.v[cle] = champ(droite, libelle, i, show=masque)
        self.sexe = tk.StringVar(value="F")
        ttk.Label(droite, text="Sexe", style="Carte.TLabel").grid(row=7, column=0, sticky="w", pady=4)
        ttk.Combobox(droite, textvariable=self.sexe, values=["M", "F"], width=5, state="readonly").grid(
            row=7, column=1, sticky="w", pady=4)
        for i, (cle, libelle) in enumerate((("telephone", "Téléphone"), ("email", "E-mail"),
                                            ("adresse", "Adresse"), ("allergies", "Allergies connues")), start=8):
            self.v[cle] = champ(droite, libelle, i)
        ttk.Button(droite, text="Créer le compte", style="Action.TButton", command=self.creer).grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    def rafraichir(self):
        mot = sans_accents(self.recherche.get().strip())
        lignes = []
        for p in self.app.utilisateurs.afficher_patients():
            if not p["actif"] and not self.archives.get():
                continue
            if mot and mot not in sans_accents(" ".join((p["nom"], p["prenom"], p["cin"]))):
                continue
            lignes.append({"id": p["id_user"], "cin": p["cin"], "nom": p["nom"], "prenom": p["prenom"],
                           "naissance": lire(p, "date_naissance"), "sexe": lire(p, "sexe"),
                           "telephone": lire(p, "telephone"), "allergies": lire(p, "allergies"),
                           "actif": p["actif"]})
        self.table.charger(lignes, lambda p: "ANNULE" if not p["actif"] else None)
        self.afficher_fiche()

    def afficher_fiche(self):
        identifiant = self.table.selection()
        if identifiant is None:
            ecrire_texte(self.fiche, "Sélectionnez un patient pour voir sa fiche.")
            return
        p = self.app.utilisateurs.chercher_par_id(identifiant)
        if p is None:
            return
        lignes = ["%s %s  —  CIN %s%s" % (p["prenom"], str(p["nom"]).upper(), p["cin"],
                                          "" if p["actif"] else "  (archivé)"),
                  "E-mail : %s   Tél. : %s" % (lire(p, "email", "—"), lire(p, "telephone", "—")),
                  "Allergies : " + (lire(p, "allergies") or "aucune connue"), "", "Historique :"]
        historique = [r for r in self.app.rdv.afficher_par_patient(identifiant) if r["statut"] == "HONORE"]
        if not historique:
            lignes.append("  • aucune consultation")
        for r in historique[:6]:
            lignes.append("  • %s — %s" % (r["date_heure"][:10], lire(r, "diagnostic", r["motif"]).strip()[:60]))
        ecrire_texte(self.fiche, "\n".join(lignes))

    def archiver(self):
        identifiant = self.choisir(self.table)
        if identifiant is None:
            return

        def action():
            p = self.app.utilisateurs.chercher_par_id(identifiant)
            if p["actif"]:
                maintenant = horloge.maintenant()
                for r in self.app.rdv.afficher_par_patient(identifiant):       # RG10
                    if r["statut"] in ("DEMANDE", "PLANIFIE") and r["date_heure"] >= maintenant:
                        raise ValueError("Archivage impossible : ce patient a des rendez-vous à venir.")
                self.app.utilisateurs.desactiver_utilisateur(identifiant)
            else:
                self.app.utilisateurs.reactiver_utilisateur(identifiant)
        self.agir(action, "Compte mis à jour.")

    def creer(self):
        d = {cle: variable.get().strip() for cle, variable in self.v.items()}

        def action():
            exiger(d, (("login", "L'identifiant"), ("mdp", "Le mot de passe"), ("nom", "Le nom"),
                       ("prenom", "Le prénom"), ("cin", "Le CIN"), ("email", "L'e-mail"),
                       ("naissance", "La date de naissance")))
            if len(d["mdp"]) < 6:
                raise ValueError("Le mot de passe doit contenir au moins 6 caractères.")
            if "@" not in d["email"]:
                raise ValueError("Adresse e-mail invalide.")
            if verifier_date(d["naissance"]) > date.today():
                raise ValueError("La date de naissance ne peut pas être dans le futur.")
            self.app.utilisateurs.ajouter_patient(
                d["login"], d["mdp"], d["cin"], d["nom"], d["prenom"], d["email"],
                d["telephone"] or None, d["adresse"] or None, d["naissance"],
                self.sexe.get() or None, d["allergies"] or None)
        if self.agir(action, "Compte patient créé."):
            for variable in self.v.values():
                variable.set("")


# ---------------------------------------------------------------- MÉDECIN : rendez-vous
class PageRendezVous(Page):
    titre, sous_titre = "Rendez-vous", "Agenda, demandes et planification"

    def construire(self):
        barre = ttk.Frame(self)
        barre.pack(fill="x")
        self.filtre, self.nom = tk.StringVar(value="semaine"), tk.StringVar()
        ttk.Label(barre, text="Afficher :", style="Titre.TLabel").pack(side="left")
        for valeur, texte in (("jour", "Aujourd'hui"), ("semaine", "Cette semaine"), ("tous", "Tous")):
            ttk.Radiobutton(barre, text=texte, value=valeur, variable=self.filtre,
                            command=self.rafraichir).pack(side="left", padx=6)
        ttk.Label(barre, text="Patient :").pack(side="left", padx=(18, 4))
        ttk.Entry(barre, textvariable=self.nom, width=18).pack(side="left")
        self.nom.trace_add("write", lambda *_: self.rafraichir())

        plan = carte(self, padding=(16, 12))
        plan.pack(fill="x", pady=12)
        ttk.Label(plan, text="Planifier un rendez-vous", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ligne = ttk.Frame(plan, style="Interne.TFrame")
        ligne.pack(fill="x")
        self.patient, self.jour = tk.StringVar(), tk.StringVar(value=horloge.aujourdhui())
        self.heure, self.motif = tk.StringVar(), tk.StringVar()
        ttk.Label(ligne, text="Patient", style="Carte.TLabel").pack(side="left", padx=(0, 6))
        self.liste_patients = ttk.Combobox(ligne, textvariable=self.patient, state="readonly", width=24)
        self.liste_patients.pack(side="left")
        ttk.Label(ligne, text="Date", style="Carte.TLabel").pack(side="left", padx=(14, 6))
        entree = ttk.Entry(ligne, textvariable=self.jour, width=11)
        entree.pack(side="left")
        entree.bind("<FocusOut>", lambda _e: self.maj_creneaux())
        entree.bind("<Return>", lambda _e: self.maj_creneaux())
        ttk.Label(ligne, text="Heure", style="Carte.TLabel").pack(side="left", padx=(14, 6))
        self.liste_heures = ttk.Combobox(ligne, textvariable=self.heure, state="readonly", width=7)
        self.liste_heures.pack(side="left")
        ligne2 = ttk.Frame(plan, style="Interne.TFrame")
        ligne2.pack(fill="x", pady=(8, 0))
        ttk.Label(ligne2, text="Motif", style="Carte.TLabel").pack(side="left", padx=(0, 6))
        ttk.Entry(ligne2, textvariable=self.motif).pack(side="left", fill="x", expand=True)
        ttk.Button(ligne2, text="Planifier", style="Action.TButton", command=self.planifier).pack(side="left", padx=(12, 0))

        self.table = Table(self, [("date_heure", "Date et heure", 140), ("patient", "Patient", 190),
                                  ("motif", "Motif", 260), ("statut", "Statut", 100)], 9)
        self.table.pack(fill="both", expand=True)
        pied = ttk.Frame(self)
        pied.pack(fill="x", pady=(10, 0))
        self.attente = ttk.Label(pied, style="Titre.TLabel")
        self.attente.pack(side="left")
        ttk.Button(pied, text="Annuler le rendez-vous", style="Danger.TButton", command=self.annuler).pack(side="right")
        ttk.Button(pied, text="Confirmer la demande", style="Action.TButton", command=self.confirmer).pack(side="right", padx=8)

    def rafraichir(self):
        actifs = [p for p in self.app.utilisateurs.afficher_patients() if p["actif"]]
        self.patients = {p["nom"] + " " + p["prenom"]: p["id_user"] for p in actifs}
        self.liste_patients["values"] = list(self.patients)
        self.maj_creneaux()

        aujourdhui = date.today()
        lundi = aujourdhui - timedelta(days=aujourdhui.weekday())
        debut, fin = lundi.isoformat(), (lundi + timedelta(days=6)).isoformat()
        mot, filtre, lignes = sans_accents(self.nom.get().strip()), self.filtre.get(), []
        toutes = self.app.rdv.afficher_par_medecin(self.app.user.id)
        for r in toutes:
            jour = r["date_heure"][:10]
            if filtre == "jour" and jour != aujourdhui.isoformat():
                continue
            if filtre == "semaine" and not debut <= jour <= fin:
                continue
            nom_patient = r["nom_patient"] + " " + r["prenom_patient"]
            if mot and mot not in sans_accents(nom_patient):
                continue
            lignes.append({"id": r["id_rendezvous"], "date_heure": r["date_heure"], "patient": nom_patient,
                           "motif": r["motif"], "statut": LIBELLE_STATUT[r["statut"]], "_code": r["statut"]})
        self.table.charger(lignes, lambda l: l["_code"])
        n = sum(1 for r in toutes if r["statut"] == "DEMANDE")
        self.attente.config(text="%d demande(s) de patient en attente de confirmation" % n)

    def maj_creneaux(self):
        try:
            libres = creneaux_libres(self.app, self.app.user.id, self.jour.get().strip())
        except ValueError:
            libres = []
        self.liste_heures["values"] = libres
        if self.heure.get() not in libres:
            self.heure.set("")

    def planifier(self):
        id_patient = self.patients.get(self.patient.get())

        def action():
            if id_patient is None:
                raise ValueError("Choisissez un patient.")
            date_heure = verifier_creneau(self.app, self.app.user.id, id_patient, self.jour.get().strip(),
                                          self.heure.get(), self.motif.get())
            id_rdv = self.app.rdv.ajouter_rdv(id_patient, self.app.user.id, date_heure, self.motif.get().strip())
            self.app.rdv.modifier_statut(id_rdv, "PLANIFIE")
        if self.agir(action, "Rendez-vous planifié."):
            self.motif.set("")

    def confirmer(self):
        identifiant = self.choisir(self.table)
        if identifiant is None:
            return

        def action():
            if self.app.rdv.chercher_par_id(identifiant)["statut"] != "DEMANDE":
                raise ValueError("Seule une demande en attente peut être confirmée.")
            self.app.rdv.modifier_statut(identifiant, "PLANIFIE")
        self.agir(action, "Demande confirmée.")

    def annuler(self):
        identifiant = self.choisir(self.table)
        if identifiant is None or not messagebox.askyesno("MediGest", "Annuler ce rendez-vous ?"):
            return

        def action():
            if self.app.rdv.chercher_par_id(identifiant)["statut"] not in ("DEMANDE", "PLANIFIE"):
                raise ValueError("Ce rendez-vous ne peut plus être annulé.")
            self.app.rdv.annuler_rdv(identifiant)
        self.agir(action, "Rendez-vous annulé.")


# ---------------------------------------------------------------- MÉDECIN : consultations
class PageConsultations(Page):
    titre, sous_titre = "Consultations", "Diagnostic et ordonnance : le stock diminue à la validation"

    def construire(self):
        haut = carte(self, padding=(16, 12))
        haut.pack(fill="x")
        ttk.Label(haut, text="1. Rendez-vous à honorer", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.table = Table(haut, [("date_heure", "Date et heure", 140), ("patient", "Patient", 220),
                                  ("motif", "Motif", 260)], 4)
        self.table.pack(fill="x")
        self.table.surselection(self.changer_rdv)
        self.allergie = ttk.Label(self, style="Alerte.TLabel")
        self.allergie.pack(anchor="w", pady=4)

        corps = ttk.Frame(self)
        corps.pack(fill="both", expand=True)
        corps.columnconfigure(0, weight=2, uniform="c")
        corps.columnconfigure(1, weight=3, uniform="c")
        corps.rowconfigure(0, weight=1)
        gauche = carte(corps)
        gauche.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(gauche, text="2. Diagnostic", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.diagnostic = zone_texte(gauche, height=8, width=30, wrap="word")
        self.diagnostic.pack(fill="both", expand=True)

        droite = carte(corps)
        droite.grid(row=0, column=1, sticky="nsew")
        ttk.Label(droite, text="3. Ordonnance", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.medicament, self.qte, self.posologie = tk.StringVar(), tk.IntVar(value=1), tk.StringVar()
        ligne = ttk.Frame(droite, style="Interne.TFrame")
        ligne.pack(fill="x")
        self.liste_med = ttk.Combobox(ligne, textvariable=self.medicament, state="readonly")
        self.liste_med.pack(side="left", fill="x", expand=True)
        ttk.Label(ligne, text="Boîtes", style="Carte.TLabel").pack(side="left", padx=(10, 4))
        ttk.Spinbox(ligne, from_=1, to=20, textvariable=self.qte, width=4).pack(side="left")
        ligne2 = ttk.Frame(droite, style="Interne.TFrame")
        ligne2.pack(fill="x", pady=(6, 8))
        ttk.Entry(ligne2, textvariable=self.posologie).pack(side="left", fill="x", expand=True)
        ttk.Label(ligne2, text="← posologie", style="CarteDoux.TLabel").pack(side="left", padx=(6, 10))
        ttk.Button(ligne2, text="Ajouter à l'ordonnance", style="Action.TButton", command=self.ajouter_ligne).pack(side="left")
        self.lignes = []
        self.table_lignes = Table(droite, [("id", "N°", 35), ("nom", "Médicament", 160), ("qte", "Qté", 45),
                                           ("posologie", "Posologie", 170)], 4)
        self.table_lignes.pack(fill="both", expand=True)
        bas = ttk.Frame(droite, style="Interne.TFrame")
        bas.pack(fill="x", pady=(8, 0))
        self.total = ttk.Label(bas, style="CarteGras.TLabel")
        self.total.pack(side="left")
        ttk.Button(bas, text="Retirer la ligne", command=self.retirer_ligne).pack(side="right")

        pied = ttk.Frame(self)
        pied.pack(fill="x", pady=(10, 0))
        ttk.Button(pied, text="Valider la consultation", style="Action.TButton", command=self.valider).pack(side="right")

    def rafraichir(self):
        rows = [r for r in self.app.rdv.afficher_par_medecin(self.app.user.id) if r["statut"] == "PLANIFIE"]
        self.table.charger([{"id": r["id_rendezvous"], "date_heure": r["date_heure"],
                             "patient": r["nom_patient"] + " " + r["prenom_patient"], "motif": r["motif"]}
                            for r in rows])
        self.catalogue = {"%s (stock %d)" % (m["designation"], m["stock"]): m
                          for m in self.app.medicaments.afficher_medicaments() if m["stock"] > 0}
        self.liste_med["values"] = list(self.catalogue)
        self.medicament.set("")
        self.lignes = []
        self.maj_lignes()
        self.diagnostic.delete("1.0", "end")
        self.allergie.config(text="")

    def patient_du_rdv(self, id_rdv):
        rdv = self.app.rdv.chercher_par_id(id_rdv)
        return self.app.utilisateurs.chercher_par_id(rdv["id_patient"]) if rdv else None

    def changer_rdv(self):
        identifiant = self.table.selection()
        if identifiant:
            p = self.patient_du_rdv(identifiant)
            allergies = lire(p, "allergies") if p else ""
            self.allergie.config(text="⚠ Allergies connues du patient : " + allergies if allergies else "")

    def ajouter_ligne(self):
        med, id_rdv = self.catalogue.get(self.medicament.get()), self.table.selection()
        if med is None or id_rdv is None:
            messagebox.showinfo("MediGest", "Choisissez d'abord un rendez-vous puis un médicament.")
            return
        try:
            qte = int(self.qte.get())
        except (tk.TclError, ValueError):
            messagebox.showwarning("MediGest", "La quantité doit être un nombre entier.")
            return
        if qte < 1 or qte > med["stock"]:
            messagebox.showwarning("MediGest", "Quantité invalide : %d boîte(s) en stock." % med["stock"])
            return
        if any(l.id_med == med["id_med"] for l in self.lignes):
            messagebox.showwarning("MediGest", "Ce médicament figure déjà dans l'ordonnance.")
            return
        alerte = alerte_allergie(self.patient_du_rdv(id_rdv), med)                           # RG13
        if alerte and not messagebox.askyesno("⚠ Allergie", alerte + "\n\nPrescrire quand même ?"):
            return
        objet = Medicament(med["id_med"], med["designation"], med["famille_med"], med["prix"],
                           med["stock"], med["seuil"])
        ligne = LigneOrdonnance(objet, qte, med["prix"])
        ligne.posologie = self.posologie.get().strip()
        self.lignes.append(ligne)
        self.posologie.set("")
        self.maj_lignes()

    def retirer_ligne(self):
        position = self.table_lignes.selection()
        if position is not None:
            del self.lignes[position - 1]
            self.maj_lignes()

    def maj_lignes(self):
        self.table_lignes.charger([{"id": i + 1, "nom": l.nom, "qte": l.qte, "posologie": l.posologie}
                                   for i, l in enumerate(self.lignes)])
        total = sum(l.total() for l in self.lignes)
        self.total.config(text="Médicaments : %.2f MAD" % total if self.lignes else "")

    def valider(self):
        id_rdv = self.choisir(self.table, "Sélectionnez le rendez-vous à honorer.")
        if id_rdv is None:
            return
        diagnostic = self.diagnostic.get("1.0", "end").strip()

        def action():
            if not diagnostic:
                raise ValueError("Le diagnostic est obligatoire.")
            ordonnance = Ordonnance()
            courant = {}
            for ligne in self.lignes:                         # on relit le stock réel avant de valider
                med = self.app.medicaments.chercher_par_id(ligne.id_med)
                courant[ligne.id_med] = med
                ligne.medicament.stock = med["stock"]
                try:
                    ordonnance.ajouter_ligne(ligne)
                except ValueError:
                    raise ValueError("Stock insuffisant pour " + ligne.nom + ".")
            contenu = json.dumps([{"id_med": l.id_med, "nom": l.nom, "qte": l.qte,
                                   "posologie": l.posologie, "prix": l.prix} for l in ordonnance.lignes],
                                 ensure_ascii=False)
            montant = tarif_de(self.app.user) + ordonnance.total()
            for ligne in ordonnance.lignes:
                self.app.medicaments.modifier_stock(ligne.id_med, courant[ligne.id_med]["stock"] - ligne.qte)
            self.app.rdv.enregistrer_consultation(id_rdv, diagnostic, contenu if ordonnance.lignes else None, montant)
        self.agir(action, "Consultation enregistrée et facturée.")


# ---------------------------------------------------------------- MÉDECIN : stock
class PageStock(Page):
    titre, sous_titre = "Stock", "Catalogue des médicaments et alertes de seuil"

    def construire(self):
        self.table = Table(self, [("designation", "Désignation", 190), ("famille", "Famille", 140),
                                  ("forme", "Forme", 100), ("prix", "Prix (MAD)", 90),
                                  ("stock", "Stock", 70), ("seuil", "Seuil d'alerte", 100)], 9)
        self.table.pack(fill="both", expand=True)
        self.bilan = ttk.Label(self, style="Alerte.TLabel")
        self.bilan.pack(anchor="w", pady=6)
        ligne = ttk.Frame(self)
        ligne.pack(fill="x")
        self.quantite = tk.StringVar(value="20")
        ttk.Label(ligne, text="Quantité reçue :").pack(side="left")
        ttk.Spinbox(ligne, from_=1, to=500, textvariable=self.quantite, width=6).pack(side="left", padx=6)
        ttk.Button(ligne, text="Réapprovisionner le médicament sélectionné", style="Action.TButton",
                   command=self.reapprovisionner).pack(side="left", padx=6)
        ttk.Button(ligne, text="Supprimer", style="Danger.TButton", command=self.supprimer).pack(side="right")

        cadre = carte(self)
        cadre.pack(fill="x", pady=(12, 0))
        ttk.Label(cadre, text="Nouveau médicament", style="Section.TLabel").grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 6))
        for c in (1, 3, 5):
            cadre.columnconfigure(c, weight=1)
        self.v = {"designation": champ(cadre, "Désignation", 1, espace=16),
                  "famille_med": champ(cadre, "Famille", 1, 2, espace=16),
                  "forme": champ(cadre, "Forme", 1, 4), "prix": champ(cadre, "Prix (MAD)", 2, espace=16),
                  "stock": champ(cadre, "Stock initial", 2, 2, espace=16), "seuil": champ(cadre, "Seuil d'alerte", 2, 4)}
        for w in cadre.grid_slaves():
            if isinstance(w, ttk.Label) and w.grid_info()["column"] in (2, 4):
                w.grid_configure(padx=(0, 10))
        ttk.Button(cadre, text="Ajouter au catalogue", style="Action.TButton", command=self.ajouter).grid(
            row=3, column=4, columnspan=2, sticky="e", pady=(8, 0))

    def rafraichir(self):
        meds = self.app.medicaments.afficher_medicaments()
        self.table.charger([{"id": m["id_med"], "designation": m["designation"], "famille": m["famille_med"],
                             "forme": m["forme"], "prix": "%.2f" % m["prix"], "stock": m["stock"],
                             "seuil": m["seuil"], "_alerte": m["stock"] <= m["seuil"]} for m in meds],
                           lambda l: "alerte" if l["_alerte"] else None)
        n = sum(1 for m in meds if m["stock"] <= m["seuil"])
        self.bilan.config(text="⚠ %d médicament(s) sous le seuil d'alerte (lignes rouges)" % n if n else "")

    def reapprovisionner(self):
        identifiant = self.choisir(self.table)
        if identifiant is None:
            return

        def action():
            qte = en_nombre(self.quantite.get(), "La quantité", entier=True)
            if qte < 1:
                raise ValueError("La quantité doit être au moins 1.")
            med = self.app.medicaments.chercher_par_id(identifiant)
            self.app.medicaments.modifier_stock(identifiant, med["stock"] + qte)
        self.agir(action, "Stock mis à jour.")

    def supprimer(self):
        identifiant = self.choisir(self.table)
        if identifiant is None or not messagebox.askyesno("MediGest", "Supprimer ce médicament du catalogue ?"):
            return
        self.agir(lambda: self.app.medicaments.supprimer_medicament(identifiant), "Médicament supprimé.")

    def ajouter(self):
        d = {cle: variable.get().strip() for cle, variable in self.v.items()}

        def action():
            exiger(d, (("designation", "La désignation"), ("famille_med", "La famille"), ("forme", "La forme"),
                       ("prix", "Le prix"), ("stock", "Le stock initial"), ("seuil", "Le seuil d'alerte")))
            self.app.medicaments.ajouter_medicament(
                d["designation"], d["famille_med"], d["forme"], en_nombre(d["prix"], "Le prix"),
                en_nombre(d["stock"], "Le stock", True), en_nombre(d["seuil"], "Le seuil", True))
        if self.agir(action, "Médicament ajouté."):
            for variable in self.v.values():
                variable.set("")


# ---------------------------------------------------------------- MÉDECIN : facturation
class PageFacturation(Page):
    titre, sous_titre = "Facturation", "Tarif de consultation + médicaments, encaissement"

    def construire(self):
        haut = ttk.Frame(self)
        haut.pack(fill="x")
        self.tarif = tk.StringVar(value="%.2f" % tarif_de(self.app.user))
        ttk.Label(haut, text="Mon tarif de consultation (MAD) :").pack(side="left")
        ttk.Entry(haut, textvariable=self.tarif, width=9).pack(side="left", padx=6)
        ttk.Button(haut, text="Modifier", command=self.changer_tarif).pack(side="left")
        ttk.Button(haut, text="Exporter en CSV", command=self.exporter).pack(side="right")
        self.table = Table(self, [("date", "Date", 90), ("patient", "Patient", 150), ("diagnostic", "Diagnostic", 220),
                                  ("montant", "Montant (MAD)", 110), ("paiement", "Paiement", 90),
                                  ("mode", "Mode", 90)], 10)
        self.table.pack(fill="both", expand=True, pady=10)
        self.total = ttk.Label(self, style="Alerte.TLabel")
        self.total.pack(anchor="w")
        bas = ttk.Frame(self)
        bas.pack(fill="x", pady=(8, 0))
        self.mode = tk.StringVar(value="Espèces")
        ttk.Combobox(bas, textvariable=self.mode, values=["Espèces", "Carte", "Chèque"],
                     state="readonly", width=10).pack(side="left")
        ttk.Button(bas, text="Encaisser", style="Action.TButton", command=self.encaisser).pack(side="left", padx=8)
        ttk.Button(bas, text="Imprimer la facture", command=lambda: self.imprimer("facture")).pack(side="right")
        ttk.Button(bas, text="Imprimer l'ordonnance", command=lambda: self.imprimer("ordonnance")).pack(side="right", padx=8)

    def lignes(self):
        res = []
        for r in self.app.rdv.afficher_par_medecin(self.app.user.id):
            if r["statut"] != "HONORE":
                continue
            res.append({"id": r["id_rendezvous"], "date": r["date_heure"][:10],
                        "patient": r["nom_patient"] + " " + r["prenom_patient"],
                        "diagnostic": lire(r, "diagnostic").strip()[:50],
                        "montant": "%.2f" % (lire(r, "montant", 0) or 0),
                        "paiement": "Payé" if statut_paiement(r) == "PAYE" else "Impayé",
                        "mode": lire(r, "mode_paiement"), "_paye": statut_paiement(r) == "PAYE",
                        "_montant": float(lire(r, "montant", 0) or 0)})
        return sorted(res, key=lambda l: l["date"], reverse=True)

    def rafraichir(self):
        lignes = self.lignes()
        self.table.charger(lignes, lambda l: "HONORE" if l["_paye"] else "DEMANDE")
        impaye = sum(l["_montant"] for l in lignes if not l["_paye"])
        self.total.config(text="Total des factures impayées : %.2f MAD" % impaye)

    def changer_tarif(self):
        def action():
            nouveau = en_nombre(self.tarif.get(), "Le tarif")
            self.app.utilisateurs.modifier_utilisateur(self.app.user.id, tarif=nouveau)
            self.app.user.Tarif = nouveau
        self.agir(action, "Tarif mis à jour (appliqué aux prochaines consultations).")

    def encaisser(self):
        identifiant = self.choisir(self.table)
        if identifiant is None:
            return

        def action():
            r = self.app.rdv.chercher_par_id(identifiant)
            if statut_paiement(r) == "PAYE":
                raise ValueError("Cette facture est déjà payée.")
            self.app.rdv.enregistrer_paiement(identifiant, self.mode.get(), horloge.aujourdhui())
        self.agir(action, "Paiement enregistré.")

    def imprimer(self, quoi):
        identifiant = self.choisir(self.table)
        if identifiant is not None:
            exports.ouvrir_dans_navigateur(self.app.document_html(identifiant, quoi))

    def exporter(self):
        lignes = [{"Date": l["date"], "Patient": l["patient"], "Diagnostic": l["diagnostic"],
                   "Montant (MAD)": l["montant"], "Paiement": l["paiement"], "Mode": l["mode"]}
                  for l in self.lignes()]
        try:
            chemin = exports.exporter_csv(lignes)
        except ValueError as erreur:
            messagebox.showinfo("MediGest", str(erreur))
            return
        messagebox.showinfo("MediGest", "Fichier créé :\n" + chemin)


# ---------------------------------------------------------------- MÉDECIN : tableau de bord
class PageTableauDeBord(Page):
    titre, sous_titre = "Tableau de bord", "Indicateurs clés de votre activité"

    def construire(self):
        cartes = ttk.Frame(self)
        cartes.pack(fill="x")
        self.chiffres = {}
        accents = {"patients": VERT, "consultations": VERT_CLAIR, "ca": "#16a34a",
                   "impayes": ORANGE, "alertes": ROUGE, "demandes": JAUNE}
        for i, (cle, libelle) in enumerate((("patients", "Patients actifs"), ("consultations", "Consultations"),
                                            ("ca", "CA encaissé"), ("impayes", "Impayés"),
                                            ("alertes", "Stocks en alerte"), ("demandes", "Demandes"))):
            c = tk.Frame(cartes, bg=CARTE, highlightthickness=1, highlightbackground=BORDURE)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            cartes.columnconfigure(i, weight=1, uniform="kpi")
            tk.Frame(c, bg=accents[cle], height=4).pack(fill="x")
            self.chiffres[cle] = ttk.Label(c, style="Chiffre.TLabel")
            self.chiffres[cle].pack(anchor="w", padx=14, pady=(10, 0))
            ttk.Label(c, text=libelle, style="CarteDoux.TLabel").pack(anchor="w", padx=14, pady=(0, 10))

        milieu = ttk.Frame(self)
        milieu.pack(fill="both", expand=True, pady=12)
        milieu.columnconfigure(0, weight=3)
        milieu.columnconfigure(1, weight=2)
        milieu.rowconfigure(1, weight=1)
        ttk.Label(milieu, text="Chiffre d'affaires encaissé par mois (MAD)", style="Titre.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(milieu, text="Répartition de mes visites", style="Titre.TLabel").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.histogramme, self.anneau = Histogramme(milieu, height=190), Anneau(milieu, height=190)
        self.histogramme.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.anneau.grid(row=1, column=1, sticky="nsew", pady=(4, 0), padx=(10, 0))

        ttk.Label(self, text="Médicaments les plus prescrits", style="Titre.TLabel").pack(anchor="w")
        self.barres = BarresHorizontales(self, height=140)
        self.barres.pack(fill="x", pady=(4, 0))
        ttk.Button(self, text="Sauvegarder la base", command=self.sauvegarder).pack(anchor="e", pady=(10, 0))

    def rafraichir(self):
        rows = self.app.rdv.afficher_par_medecin(self.app.user.id)
        honores = [r for r in rows if r["statut"] == "HONORE"]
        paye = [r for r in honores if statut_paiement(r) == "PAYE"]
        valeurs = {"patients": self.app.stats.nombre_patients(), "consultations": len(honores),
                   "ca": "%.0f MAD" % sum(lire(r, "montant", 0) or 0 for r in paye),
                   "impayes": "%.0f MAD" % sum(lire(r, "montant", 0) or 0 for r in honores if statut_paiement(r) == "IMPAYE"),
                   "alertes": self.app.stats.stock_en_alerte(),
                   "demandes": sum(1 for r in rows if r["statut"] == "DEMANDE")}
        for cle, valeur in valeurs.items():
            self.chiffres[cle].config(text=str(valeur))

        # CA encaissé sur les 6 derniers mois
        aujourdhui, mois = date.today(), []
        a, m = aujourdhui.year, aujourdhui.month
        for _ in range(6):
            mois.append((a, m))
            m -= 1
            if m == 0:
                a, m = a - 1, 12
        mois.reverse()
        somme = {k: 0.0 for k in mois}
        for r in paye:
            jour = lire(r, "date_paiement") or r["date_heure"][:10]
            try:
                cle = (int(jour[:4]), int(jour[5:7]))
            except ValueError:
                continue
            if cle in somme:
                somme[cle] += lire(r, "montant", 0) or 0
        self.histogramme.dessiner([(MOIS_COURTS[m - 1], somme[(a, m)]) for a, m in mois])
        self.anneau.dessiner({s: sum(1 for r in rows if r["statut"] == s)
                              for s in ("ANNULE", "DEMANDE", "HONORE", "PLANIFIE")})
        total = {}
        for r in honores:
            for ligne in lire_ordonnance(lire(r, "ordonnance")):
                try:
                    total[ligne.get("nom", "?")] = total.get(ligne.get("nom", "?"), 0) + int(ligne.get("qte") or 0)
                except (TypeError, ValueError):
                    pass
        self.barres.dessiner(sorted(total.items(), key=lambda x: -x[1])[:5])

    def sauvegarder(self):
        nom = "MediGest_sauvegarde_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".db"
        try:
            copie = sqlite3.connect(nom)
            self.app.db.backup(copie)
            copie.close()
        except sqlite3.Error as erreur:
            messagebox.showwarning("MediGest", "Sauvegarde impossible : " + str(erreur))
            return
        messagebox.showinfo("MediGest", "Sauvegarde créée :\n" + nom)


# ---------------------------------------------------------------- PATIENT
class PageMesRendezVous(Page):
    titre, sous_titre = "Mes rendez-vous", "Demandez un créneau, le médecin le confirmera"

    def construire(self):
        cadre = carte(self, padding=(16, 12))
        cadre.pack(fill="x")
        ttk.Label(cadre, text="Demander un rendez-vous", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ligne = ttk.Frame(cadre, style="Interne.TFrame")
        ligne.pack(fill="x")
        self.medecin, self.jour = tk.StringVar(), tk.StringVar(value=horloge.aujourdhui())
        self.heure, self.motif = tk.StringVar(), tk.StringVar()
        ttk.Label(ligne, text="Médecin", style="Carte.TLabel").pack(side="left", padx=(0, 6))
        self.liste_medecins = ttk.Combobox(ligne, textvariable=self.medecin, state="readonly", width=34)
        self.liste_medecins.pack(side="left")
        self.liste_medecins.bind("<<ComboboxSelected>>", lambda _e: self.maj_creneaux())
        ttk.Label(ligne, text="Date", style="Carte.TLabel").pack(side="left", padx=(12, 6))
        entree = ttk.Entry(ligne, textvariable=self.jour, width=11)
        entree.pack(side="left")
        entree.bind("<FocusOut>", lambda _e: self.maj_creneaux())
        entree.bind("<Return>", lambda _e: self.maj_creneaux())
        ttk.Label(ligne, text="Heure", style="Carte.TLabel").pack(side="left", padx=(12, 6))
        self.liste_heures = ttk.Combobox(ligne, textvariable=self.heure, state="readonly", width=7)
        self.liste_heures.pack(side="left")
        ligne2 = ttk.Frame(cadre, style="Interne.TFrame")
        ligne2.pack(fill="x", pady=(8, 0))
        ttk.Label(ligne2, text="Motif", style="Carte.TLabel").pack(side="left", padx=(0, 6))
        ttk.Entry(ligne2, textvariable=self.motif, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(ligne2, text="Demander", style="Action.TButton", command=self.demander).pack(side="left", padx=(12, 0))

        self.table = Table(self, [("date_heure", "Date et heure", 130), ("medecin", "Médecin", 160),
                                  ("specialite", "Spécialité", 140), ("motif", "Motif", 190), ("statut", "Statut", 90)], 9)
        self.table.pack(fill="both", expand=True, pady=12)
        ttk.Button(self, text="Annuler le rendez-vous sélectionné", style="Danger.TButton",
                   command=self.annuler).pack(anchor="e")

    def rafraichir(self):
        self.medecins = {}
        for m in self.app.utilisateurs.afficher_medecins():
            if m["actif"]:
                self.medecins["Dr %s %s — %s" % (m["prenom"], str(m["nom"]).upper(), lire(m, "specialite"))] = m["id_user"]
        self.liste_medecins["values"] = list(self.medecins)
        if len(self.medecins) == 1 and not self.medecin.get():
            self.medecin.set(next(iter(self.medecins)))
        self.maj_creneaux()
        specialites = {m["id_user"]: lire(m, "specialite") for m in self.app.utilisateurs.afficher_medecins()}
        self.table.charger([{"id": r["id_rendezvous"], "date_heure": r["date_heure"],
                             "medecin": "Dr %s %s" % (r["prenom_medecin"], r["nom_medecin"]),
                             "specialite": specialites.get(r["id_medecin"], ""), "motif": r["motif"],
                             "statut": LIBELLE_STATUT[r["statut"]], "_code": r["statut"]}
                            for r in self.app.rdv.afficher_par_patient(self.app.user.id)],
                           lambda l: l["_code"])

    def maj_creneaux(self):
        id_medecin = self.medecins.get(self.medecin.get())
        try:
            libres = creneaux_libres(self.app, id_medecin, self.jour.get().strip()) if id_medecin else []
        except ValueError:
            libres = []
        self.liste_heures["values"] = libres
        if self.heure.get() not in libres:
            self.heure.set("")

    def demander(self):
        id_medecin = self.medecins.get(self.medecin.get())

        def action():
            if id_medecin is None:
                raise ValueError("Choisissez un médecin.")
            en_attente = [r for r in self.app.rdv.afficher_par_patient(self.app.user.id) if r["statut"] == "DEMANDE"]
            if len(en_attente) >= 2:                                                           # RG14
                raise ValueError("Vous avez déjà 2 demandes en attente de confirmation.")
            date_heure = verifier_creneau(self.app, id_medecin, self.app.user.id, self.jour.get().strip(),
                                          self.heure.get(), self.motif.get())
            self.app.rdv.ajouter_rdv(self.app.user.id, id_medecin, date_heure, self.motif.get().strip())
        if self.agir(action, "Demande envoyée : le médecin doit la confirmer."):
            self.motif.set("")

    def annuler(self):
        identifiant = self.choisir(self.table)
        if identifiant is None or not messagebox.askyesno("MediGest", "Annuler ce rendez-vous ?"):
            return

        def action():
            r = self.app.rdv.chercher_par_id(identifiant)
            if r is None or r["id_patient"] != self.app.user.id:
                raise ValueError("Rendez-vous introuvable.")
            if r["statut"] not in ("DEMANDE", "PLANIFIE"):
                raise ValueError("Ce rendez-vous ne peut plus être annulé.")
            if datetime.strptime(r["date_heure"], "%Y-%m-%d %H:%M") - datetime.now() < timedelta(hours=24):   # RG15
                raise ValueError("Annulation impossible moins de 24 h avant le rendez-vous. Contactez la clinique.")
            self.app.rdv.annuler_rdv(identifiant)
        self.agir(action, "Rendez-vous annulé.")


class PageMesOrdonnances(Page):
    titre, sous_titre = "Mes ordonnances", "Prescriptions de vos consultations"

    def construire(self):
        self.table = Table(self, [("date_heure", "Date", 140), ("medecin", "Médecin", 160),
                                  ("diagnostic", "Diagnostic", 300)], 7)
        self.table.pack(fill="x")
        self.table.surselection(self.afficher)
        ttk.Label(self, text="Ordonnance", style="Titre.TLabel").pack(anchor="w", pady=(14, 4))
        self.texte = zone_texte(self, height=9, state="disabled")
        self.texte.pack(fill="both", expand=True)
        ttk.Button(self, text="Imprimer l'ordonnance", command=self.imprimer).pack(anchor="e", pady=(8, 0))

    def rafraichir(self):
        self.table.charger([{"id": r["id_rendezvous"], "date_heure": r["date_heure"],
                             "medecin": "Dr %s %s" % (r["prenom_medecin"], r["nom_medecin"]),
                             "diagnostic": lire(r, "diagnostic").strip()[:70]}
                            for r in self.app.rdv.afficher_par_patient(self.app.user.id) if r["statut"] == "HONORE"])
        self.afficher()

    def afficher(self):
        identifiant = self.table.selection()
        if identifiant is None:
            ecrire_texte(self.texte, "Sélectionnez une consultation pour lire son ordonnance.")
            return
        r = self.app.rdv.chercher_par_id(identifiant)
        lignes = lire_ordonnance(lire(r, "ordonnance"))
        corps = "\n".join("• %s  —  %s boîte(s)  —  %s" % (l.get("nom", "?"), l.get("qte", ""), l.get("posologie") or "—")
                          for l in lignes)
        ecrire_texte(self.texte, corps or "Aucun médicament prescrit.")

    def imprimer(self):
        identifiant = self.choisir(self.table)
        if identifiant is not None:
            exports.ouvrir_dans_navigateur(self.app.document_html(identifiant, "ordonnance"))


class PageMesFactures(Page):
    titre, sous_titre = "Mes factures", "Montants et paiements"

    def construire(self):
        self.table = Table(self, [("date", "Date", 100), ("medecin", "Médecin", 170), ("montant", "Montant (MAD)", 120),
                                  ("statut", "Statut", 100), ("mode", "Paiement", 110)], 10)
        self.table.pack(fill="both", expand=True)
        self.reste = ttk.Label(self, style="Alerte.TLabel")
        self.reste.pack(anchor="w", pady=6)
        ttk.Button(self, text="Imprimer la facture sélectionnée", command=self.imprimer).pack(anchor="e")

    def rafraichir(self):
        lignes, reste = [], 0.0
        for r in self.app.rdv.afficher_par_patient(self.app.user.id):
            if r["statut"] != "HONORE":
                continue
            paye = statut_paiement(r) == "PAYE"
            montant = float(lire(r, "montant", 0) or 0)
            reste += 0 if paye else montant
            lignes.append({"id": r["id_rendezvous"], "date": r["date_heure"][:10],
                           "medecin": "Dr %s %s" % (r["prenom_medecin"], r["nom_medecin"]),
                           "montant": "%.2f" % montant, "statut": "Payé" if paye else "Impayé",
                           "mode": lire(r, "mode_paiement"), "_paye": paye})
        self.table.charger(lignes, lambda l: "HONORE" if l["_paye"] else "DEMANDE")
        self.reste.config(text="Reste à payer : %.2f MAD" % reste)

    def imprimer(self):
        identifiant = self.choisir(self.table)
        if identifiant is not None:
            exports.ouvrir_dans_navigateur(self.app.document_html(identifiant, "facture"))


# ---------------------------------------------------------------- commun aux 2 profils
class PageProfil(Page):
    titre, sous_titre = "Mon profil", "Vos informations et votre mot de passe"

    def construire(self):
        u = self.app.user
        self.columnconfigure(0, weight=1, uniform="p")
        self.columnconfigure(1, weight=1, uniform="p")
        identite = carte(self)
        identite.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 14))
        ttk.Label(identite, text="Mon identité (non modifiable)", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        infos = [("Nom", nom_affiche(u)), ("CIN", u.cin), ("Identifiant", u.login), ("Rôle", role_de(u).capitalize())]
        if est_medecin(u):
            infos.append(("Spécialité", u.specialite))
        else:
            infos += [("Naissance", "%s (%d ans)" % (u.date_naissance.isoformat(), u.age())),
                      ("Sexe", u.sexe or "—"), ("Allergies", u.allergies or "aucune connue")]
        for libelle, valeur in infos:
            ligne = ttk.Frame(identite, style="Interne.TFrame")
            ligne.pack(fill="x", pady=2)
            ttk.Label(ligne, text=libelle, style="CarteDoux.TLabel", width=12).pack(side="left")
            ttk.Label(ligne, text=str(valeur), style="CarteGras.TLabel").pack(side="left")

        coord = carte(self)
        coord.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 14))
        coord.columnconfigure(1, weight=1)
        ttk.Label(coord, text="Mes coordonnées", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.tel, self.mail, self.adresse = (champ(coord, "Téléphone", 1, largeur=28), champ(coord, "E-mail", 2, largeur=28),
                                             champ(coord, "Adresse", 3, largeur=28))
        self.tel.set(u.telephone or "")
        self.mail.set(u.email or "")
        self.adresse.set(u.adresse or "")
        ttk.Button(coord, text="Enregistrer", style="Action.TButton", command=self.enregistrer).grid(
            row=4, column=1, sticky="e", pady=(10, 0))

        secret = carte(self)
        secret.grid(row=1, column=0, columnspan=2, sticky="ew")
        secret.columnconfigure((1, 3, 5), weight=1)
        ttk.Label(secret, text="Changer mon mot de passe", style="Section.TLabel").grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 8))
        self.ancien = champ(secret, "Ancien", 1, show="*", espace=16)
        self.nouveau = champ(secret, "Nouveau", 1, 2, show="*", espace=16)
        self.confirme = champ(secret, "Confirmer", 1, 4, show="*")
        for w in secret.grid_slaves(row=1):
            if isinstance(w, ttk.Label) and w.grid_info()["column"] in (2, 4):
                w.grid_configure(padx=(0, 10))
        ttk.Button(secret, text="Changer le mot de passe", command=self.changer_mdp).grid(
            row=2, column=5, sticky="e", pady=(10, 0))

    def enregistrer(self):
        u = self.app.user

        def action():
            mail = self.mail.get().strip()
            if "@" not in mail:
                raise ValueError("Adresse e-mail invalide.")
            tel, adresse = self.tel.get().strip() or None, self.adresse.get().strip() or None
            self.app.utilisateurs.modifier_utilisateur(u.id, telephone=tel, email=mail, adresse=adresse)
            u.telephone, u.email, u.adresse = tel, mail, adresse
        self.agir(action, "Coordonnées enregistrées.")

    def changer_mdp(self):
        def action():
            if len(self.nouveau.get()) < 6:
                raise ValueError("Le nouveau mot de passe doit contenir au moins 6 caractères.")
            if self.nouveau.get() != self.confirme.get():
                raise ValueError("La confirmation ne correspond pas au nouveau mot de passe.")
            if not self.app.utilisateurs.changer_mot_de_passe(self.app.user.id, self.ancien.get(), self.nouveau.get()):
                raise ValueError("L'ancien mot de passe est incorrect.")
        if self.agir(action, "Mot de passe modifié."):
            for v in (self.ancien, self.nouveau, self.confirme):
                v.set("")


PAGES = {
    "Patients": PagePatients, "Rendez-vous": PageRendezVous, "Consultations": PageConsultations,
    "Stock": PageStock, "Facturation": PageFacturation, "Tableau de bord": PageTableauDeBord,
    "Mes rendez-vous": PageMesRendezVous, "Mes ordonnances": PageMesOrdonnances,
    "Mes factures": PageMesFactures, "Mon profil": PageProfil,
}


# ====================================================================== menu latéral
class ItemMenu(tk.Frame):
    def __init__(self, parent, texte, commande):
        super().__init__(parent, bg=LATERAL, cursor="hand2")
        self.actif = False
        self.barre = tk.Frame(self, bg=LATERAL, width=4)
        self.barre.pack(side="left", fill="y")
        self.label = tk.Label(self, text=texte, bg=LATERAL, fg="#b7d9d4", font=police(11), anchor="w", padx=18, pady=11)
        self.label.pack(side="left", fill="x", expand=True)
        for w in (self, self.label, self.barre):
            w.bind("<Button-1>", lambda _e: commande())
            w.bind("<Enter>", lambda _e: self.colorer(survol=True))
            w.bind("<Leave>", lambda _e: self.colorer(survol=False))

    def colorer(self, survol=False):
        fond = VERT if self.actif else (LATERAL_SURVOL if survol else LATERAL)
        for w in (self, self.label):
            w.configure(bg=fond)
        self.barre.configure(bg="#5eead4" if self.actif else fond)
        self.label.configure(fg="white" if (self.actif or survol) else "#b7d9d4",
                             font=police(11, self.actif))

    def definir(self, actif):
        self.actif = actif
        self.colorer()


class DialogueAccueil(tk.Toplevel):
    """Résumé affiché juste après la connexion."""

    def __init__(self, app, titre, lignes):
        super().__init__(app, bg=CARTE)
        self.title("Bienvenue")
        self.resizable(False, False)
        self.transient(app)
        bandeau = tk.Frame(self, bg=VERT)
        bandeau.pack(fill="x")
        tk.Label(bandeau, text=titre, bg=VERT, fg="white", font=police(13, True), padx=22, pady=14).pack(anchor="w")
        corps = tk.Frame(self, bg=CARTE, padx=22, pady=16)
        corps.pack(fill="both")
        tk.Label(corps, text="Résumé de votre journée", bg=CARTE, fg=VERT, font=police(12, True)).pack(anchor="w", pady=(0, 10))
        for couleur, texte in lignes:
            ligne = tk.Frame(corps, bg=CARTE)
            ligne.pack(fill="x", pady=3)
            tk.Label(ligne, text="●", bg=CARTE, fg=couleur, font=police(10)).pack(side="left")
            tk.Label(ligne, text=texte, bg=CARTE, fg=TEXTE, font=police(10), justify="left", wraplength=360).pack(side="left", padx=8)
        ttk.Button(corps, text="Commencer", style="Action.TButton", command=self.destroy).pack(anchor="e", pady=(16, 0))
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        self.grab_set()
        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Escape>", lambda _e: self.destroy())


# ====================================================================== fenêtre principale
class Application(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.title("MediGest — Clinique Al Amal")
        self.minsize(1100, 720)
        largeur, hauteur = 1220, 780
        x = max((self.winfo_screenwidth() - largeur) // 2, 0)
        y = max((self.winfo_screenheight() - hauteur) // 2 - 20, 0)
        self.geometry("%dx%d+%d+%d" % (largeur, hauteur, x, y))
        appliquer_style(self)
        self.db = db
        self.utilisateurs, self.medicaments = UtilisateurDAO(db), MedicamentDAO(db)
        self.rdv, self.stats = RendezVousDAO(db), StatistiquesDAO(db)
        self.user, self.page, self.pages, self.menu = None, None, {}, {}
        self.courante, self.minuteur = None, None
        self.afficher_connexion()

    def report_callback_exception(self, exc, val, tb):
        """Une erreur inattendue est affichée au lieu de laisser l'écran vide."""
        import traceback
        traceback.print_exception(exc, val, tb)
        messagebox.showerror("MediGest — erreur inattendue", "%s : %s" % (exc.__name__, val))

    # ------------------------------------------------------------ connexion
    def afficher_connexion(self):
        if self.page:
            self.page.destroy()
        self.user, self.pages, self.menu, self.courante = None, {}, {}, None
        self.page = tk.Frame(self, bg=FOND)
        self.page.pack(fill="both", expand=True)
        bordure = tk.Frame(self.page, bg=BORDURE, padx=1, pady=1)
        bordure.place(relx=0.5, rely=0.5, anchor="center")
        boite = tk.Frame(bordure, bg=CARTE)
        boite.pack()

        marque = tk.Canvas(boite, width=360, height=470, bg=VERT_FONCE, highlightthickness=0)
        marque.pack(side="left")
        marque.create_oval(180, -120, 480, 180, fill="#0f6a63", outline="")
        marque.create_oval(-110, 300, 190, 600, fill="#0e655e", outline="")
        marque.create_rectangle(44, 70, 100, 90, fill="white", outline="")
        marque.create_rectangle(62, 52, 82, 108, fill="white", outline="")
        marque.create_text(44, 160, anchor="w", text="MediGest", fill="white", font=police(30, True))
        marque.create_text(46, 202, anchor="w", text="Clinique Al Amal", fill="#ccfbf1", font=police(13))
        marque.create_text(46, 250, anchor="nw", fill="#99f6e4", font=police(10), width=270,
                           text="Rendez-vous, consultations, ordonnances, stock et facturation : "
                                "tout votre cabinet au même endroit.")

        formulaire = tk.Frame(boite, bg=CARTE, padx=44, pady=44)
        formulaire.pack(side="left", fill="both")
        self.login, self.mdp = tk.StringVar(), tk.StringVar()
        ttk.Label(formulaire, text="Bienvenue", style="CarteTitre.TLabel").pack(anchor="w")
        ttk.Label(formulaire, text="Connectez-vous pour accéder à votre espace.", style="CarteDoux.TLabel").pack(anchor="w", pady=(2, 22))
        ttk.Label(formulaire, text="Identifiant", style="CarteGras.TLabel").pack(anchor="w")
        entree = ttk.Entry(formulaire, textvariable=self.login, width=34)
        entree.pack(fill="x", pady=(4, 0))
        ttk.Label(formulaire, text="Mot de passe", style="CarteGras.TLabel").pack(anchor="w", pady=(14, 0))
        self.champ_mdp = ttk.Entry(formulaire, textvariable=self.mdp, show="*", width=34)
        self.champ_mdp.pack(fill="x", pady=(4, 0))
        self.voir = tk.BooleanVar()
        ttk.Checkbutton(formulaire, text="Afficher le mot de passe", variable=self.voir, style="Carte.TCheckbutton",
                        command=lambda: self.champ_mdp.config(show="" if self.voir.get() else "*")).pack(anchor="w", pady=(8, 0))
        self.erreur = ttk.Label(formulaire, text="", style="Erreur.TLabel")
        self.erreur.pack(anchor="w", pady=(10, 0))
        ttk.Button(formulaire, text="Se connecter", style="Action.TButton", command=self.connecter).pack(fill="x", pady=(8, 16))
        ttk.Button(
            formulaire,
            text="Créer un compte",
            style="Lateral.TButton",
            command=self.afficher_inscription
        ).pack(fill="x", pady=(0, 12))
        if self.utilisateurs.chercher_par_login("dr.alaoui"):
            ttk.Label(formulaire, text="Comptes d'essai :  dr.alaoui / medecin123   ·   s.tazi / patient123",
                      style="CarteDoux.TLabel").pack(anchor="w")
        self.bind("<Return>", lambda _e: self.connecter() if self.user is None else None)
        entree.focus_set()

    def connecter(self):
        login, mdp = self.login.get().strip(), self.mdp.get()
        if not login or not mdp:
            self.erreur.config(text="Saisissez votre identifiant et votre mot de passe.")
            return
        ligne = self.utilisateurs.authentifier(login, mdp)
        if ligne is None:
            self.erreur.config(text="Identifiant ou mot de passe incorrect (ou compte archivé).")
            self.mdp.set("")
            return
        self.ouvrir_session(construire_utilisateur(ligne))
    
    def afficher_inscription(self):
        fenetre = tk.Toplevel(self)
        fenetre.title("Créer un compte — MediGest")
        fenetre.geometry("450x650")
        fenetre.resizable(False, False)
        fenetre.transient(self)
        fenetre.grab_set()

        formulaire = tk.Frame(fenetre, bg=CARTE, padx=30, pady=20)
        formulaire.pack(fill="both", expand=True)

        ttk.Label(
            formulaire,
            text="Créer un compte patient",
            style="CarteTitre.TLabel"
        ).pack(anchor="w", pady=(0, 15))

        champs = {}

        donnees = [
            ("Identifiant", "login"),
            ("Mot de passe", "mdp"),
            ("CIN", "cin"),
            ("Nom", "nom"),
            ("Prénom", "prenom"),
            ("Email", "email"),
            ("Téléphone", "telephone"),
            ("Adresse", "adresse"),
            ("Date de naissance (AAAA-MM-JJ)", "date_naissance")
        ]

        for label, cle in donnees:
            ttk.Label(
                formulaire,
                text=label,
                style="CarteGras.TLabel"
            ).pack(anchor="w", pady=(5, 2))

            entree = ttk.Entry(
                formulaire,
                width=35,
                show="*" if cle == "mdp" else ""
            )
            entree.pack(fill="x")
            champs[cle] = entree

        def creer():
            valeurs = {
                cle: entree.get().strip()
                for cle, entree in champs.items()
            }

            if any(not valeur for valeur in valeurs.values()):
                messagebox.showwarning(
                    "Inscription",
                    "Veuillez remplir tous les champs."
                )
                return

            try:
                self.utilisateurs.ajouter_patient(
                    valeurs["login"],
                    valeurs["mdp"],
                    valeurs["cin"],
                    valeurs["nom"],
                    valeurs["prenom"],
                    valeurs["email"],
                    valeurs["telephone"],
                    valeurs["adresse"],
                    valeurs["date_naissance"]
                )

                messagebox.showinfo(
                    "Inscription réussie",
                    "Votre compte patient a été créé avec succès."
                )

                fenetre.destroy()
                self.login.set(valeurs["login"])
                self.mdp.set("")

            except (ValueError, sqlite3.Error) as e:
                messagebox.showerror("Erreur d'inscription", str(e))

        ttk.Button(
            formulaire,
            text="Créer mon compte",
            style="Action.TButton",
            command=creer
        ).pack(fill="x", pady=(15, 0))

    def ouvrir_session(self, user):
        self.user = user
        self.unbind("<Return>")
        self.page.destroy()
        self.page = tk.Frame(self, bg=FOND)
        self.page.pack(fill="both", expand=True)

        lateral = tk.Frame(self.page, bg=LATERAL, width=240)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        marque = tk.Frame(lateral, bg=LATERAL)
        marque.pack(fill="x", padx=22, pady=(24, 22))
        tk.Label(marque, text="✚", bg=LATERAL, fg="#5eead4", font=police(18, True)).pack(side="left")
        bloc = tk.Frame(marque, bg=LATERAL)
        bloc.pack(side="left", padx=10)
        tk.Label(bloc, text="MediGest", bg=LATERAL, fg="white", font=police(15, True)).pack(anchor="w")
        tk.Label(bloc, text="Clinique Al Amal", bg=LATERAL, fg="#8fc4bd", font=police(9)).pack(anchor="w")

        for nom in (ECRANS_MEDECIN if est_medecin(user) else ECRANS_PATIENT):
            self.menu[nom] = ItemMenu(lateral, nom, lambda n=nom: self.aller(n))
            self.menu[nom].pack(fill="x")

        profil = tk.Frame(lateral, bg=LATERAL)
        profil.pack(side="bottom", fill="x", padx=18, pady=18)
        ttk.Button(profil, text="Déconnexion", style="Lateral.TButton", command=self.afficher_connexion).pack(
            side="bottom", fill="x", pady=(14, 0))
        ligne = tk.Frame(profil, bg=LATERAL)
        ligne.pack(side="bottom", fill="x")
        avatar = tk.Canvas(ligne, width=42, height=42, bg=LATERAL, highlightthickness=0)
        avatar.create_oval(1, 1, 41, 41, fill=VERT, outline="#5eead4")
        avatar.create_text(21, 21, text=initiales(user), fill="white", font=police(11, True))
        avatar.pack(side="left")
        infos = tk.Frame(ligne, bg=LATERAL)
        infos.pack(side="left", padx=10)
        tk.Label(infos, text=nom_affiche(user), bg=LATERAL, fg="white", font=police(10, True), anchor="w").pack(anchor="w")
        tk.Label(infos, text=role_de(user), bg=LATERAL, fg="#8fc4bd", font=police(8, True)).pack(anchor="w")

        principal = tk.Frame(self.page, bg=FOND)
        principal.pack(side="left", fill="both", expand=True)
        entete = tk.Frame(principal, bg=FOND)
        entete.pack(fill="x", padx=28, pady=(20, 8))
        textes = tk.Frame(entete, bg=FOND)
        textes.pack(side="left")
        self.titre = tk.Label(textes, bg=FOND, fg=TEXTE, font=police(20, True), anchor="w")
        self.titre.pack(anchor="w")
        self.sous_titre = tk.Label(textes, bg=FOND, fg=TEXTE_DOUX, font=police(10), anchor="w")
        self.sous_titre.pack(anchor="w")
        droite = tk.Frame(entete, bg=FOND)
        droite.pack(side="right")
        tk.Label(droite, text=date_longue(date.today()), bg=FOND, fg=TEXTE_DOUX, font=police(10)).pack(anchor="e")
        self.notice = tk.Label(droite, bg=FOND, fg=VERT, font=police(10, True))
        self.notice.pack(anchor="e")
        self.zone = ttk.Frame(principal, padding=(28, 6, 28, 22))
        self.zone.pack(fill="both", expand=True)

        self.aller(ECRANS_MEDECIN[0] if est_medecin(user) else ECRANS_PATIENT[0])
        self.after(150, self.message_accueil)

    def aller(self, nom):
        if self.courante:
            self.courante.pack_forget()
        if nom not in self.pages:
            self.pages[nom] = PAGES[nom](self.zone, self)
        else:
            self.pages[nom].rafraichir()
        self.courante = self.pages[nom]
        self.courante.pack(fill="both", expand=True)
        for n, item in self.menu.items():
            item.definir(n == nom)
        self.titre.config(text=self.courante.titre)
        self.sous_titre.config(text=self.courante.sous_titre)

    def rafraichir_tout(self):
        for page in self.pages.values():
            page.rafraichir()

    def notifier(self, texte):
        """Petit message de confirmation dans l'en-tête, effacé au bout de 4 secondes."""
        self.notice.config(text="✓ " + texte)
        if self.minuteur:
            self.after_cancel(self.minuteur)
        self.minuteur = self.after(4000, lambda: self.notice.config(text=""))

    def message_accueil(self):
        if self.user is None:
            return
        maintenant, aujourdhui = horloge.maintenant(), horloge.aujourdhui()
        if est_medecin(self.user):
            rows = self.rdv.afficher_par_medecin(self.user.id)
            n_jour = sum(1 for r in rows if r["statut"] in ("PLANIFIE", "DEMANDE") and r["date_heure"][:10] == aujourdhui)
            n_dem = sum(1 for r in rows if r["statut"] == "DEMANDE")
            n_stock = self.stats.stock_en_alerte()
            n_fact = sum(1 for r in rows if r["statut"] == "HONORE" and statut_paiement(r) == "IMPAYE")
            lignes = [(VERT, "%d rendez-vous aujourd'hui" % n_jour),
                      (ORANGE, "%d demande(s) de rendez-vous à confirmer" % n_dem),
                      (ROUGE, "%d médicament(s) sous le seuil d'alerte" % n_stock),
                      (JAUNE, "%d consultation(s) honorée(s) en attente de paiement" % n_fact)]
        else:
            rows = self.rdv.afficher_par_patient(self.user.id)
            futurs = sorted((r for r in rows if r["statut"] in ("PLANIFIE", "DEMANDE") and r["date_heure"] >= maintenant),
                            key=lambda r: r["date_heure"])
            if futurs:
                p = futurs[0]
                lignes = [(VERT, "Prochain rendez-vous : %s avec Dr %s %s (%s)" % (
                    p["date_heure"], p["prenom_medecin"], p["nom_medecin"], LIBELLE_STATUT[p["statut"]].lower()))]
            else:
                lignes = [(TEXTE_DOUX, "Aucun rendez-vous à venir.")]
            reste = sum(float(lire(r, "montant", 0) or 0) for r in rows
                        if r["statut"] == "HONORE" and statut_paiement(r) == "IMPAYE")
            if reste:
                lignes.append((ORANGE, "Reste à payer : %.2f MAD" % reste))
        DialogueAccueil(self, "Bonjour " + nom_affiche(self.user), lignes)

    # ------------------------------------------------------------ impressions
    def document_html(self, id_rdv, quoi):
        """HTML imprimable d'une facture ou d'une ordonnance (ouvert dans le navigateur)."""
        r = self.rdv.chercher_par_id(id_rdv)
        if r is None or (not est_medecin(self.user) and r["id_patient"] != self.user.id):
            raise ValueError("Document introuvable.")
        patient = self.utilisateurs.chercher_par_id(r["id_patient"])
        medecin = self.utilisateurs.chercher_par_id(r["id_medecin"])
        e = html.escape
        lignes = lire_ordonnance(lire(r, "ordonnance"))
        if quoi == "ordonnance":
            titre = "Ordonnance"
            corps = "<table><tr><th>Médicament</th><th>Quantité</th><th>Posologie</th></tr>" + "".join(
                "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(str(l.get("nom", ""))), e(str(l.get("qte", ""))),
                                                                 e(str(l.get("posologie", "")))) for l in lignes) + "</table>"
            if not lignes:
                corps = "<p>Aucun médicament prescrit.</p>"
        else:
            titre = "Facture"
            total = float(lire(r, "montant", 0) or 0)
            sous_totaux = [float(l.get("prix") or 0) * int(l.get("qte") or 0) for l in lignes]
            detail = "".join("<tr><td>%s × %s</td><td class='d'>%.2f</td></tr>" % (
                e(str(l.get("nom", ""))), e(str(l.get("qte", ""))), s) for l, s in zip(lignes, sous_totaux))
            paiement = ""
            if statut_paiement(r) == "PAYE":
                paiement = " (%s, le %s)" % (e(lire(r, "mode_paiement")), e(lire(r, "date_paiement")))
            corps = ("<table><tr><th>Désignation</th><th class='d'>Montant (MAD)</th></tr>"
                     "<tr><td>Consultation</td><td class='d'>%.2f</td></tr>%s"
                     "<tr><th>Total</th><th class='d'>%.2f</th></tr></table><p>Statut : <b>%s</b>%s</p>") % (
                         total - sum(sous_totaux), detail, total,
                         "Payé" if statut_paiement(r) == "PAYE" else "Impayé", paiement)
        return ("<!doctype html><html lang='fr'><meta charset='utf-8'><title>%s</title><style>"
                "body{font-family:Segoe UI,Arial,sans-serif;max-width:720px;margin:40px auto;color:#1f2937}"
                "h1{color:#0f766e;border-bottom:3px solid #0f766e;padding-bottom:8px}"
                "table{width:100%%;border-collapse:collapse;margin:16px 0}th,td{padding:8px 10px;border-bottom:1px solid #dbe4e2;text-align:left}"
                "th{background:#e6efed}.d{text-align:right}.s{color:#6b7280}</style>"
                "<h1>%s</h1><p class='s'>Clinique Al Amal</p>"
                "<p><b>Médecin :</b> Dr %s %s<br><b>Patient :</b> %s %s (CIN %s)<br><b>Date :</b> %s</p>%s"
                "<p class='s'>Diagnostic : %s</p></html>") % (
                    titre, titre, e(medecin["prenom"]), e(str(medecin["nom"]).upper()), e(patient["prenom"]),
                    e(str(patient["nom"]).upper()), e(patient["cin"]), e(r["date_heure"]), corps, e(lire(r, "diagnostic")))


# ====================================================================== jeu d'essai (créé seulement si la base est vide)
def jeu_essai(app):
    """Si la base ne contient aucun utilisateur, crée des comptes et données fictifs pour pouvoir tester.

    Comptes : dr.alaoui / medecin123  et  s.tazi / patient123.
    Pour ne plus créer ces données, supprimez simplement l'appel jeu_essai(self) dans Application.__init__.
    """
    if app.db.execute("SELECT COUNT(*) FROM Users").fetchone()[0] > 0:
        return
    u, m, r = app.utilisateurs, app.medicaments, app.rdv
    medecin = u.ajouter_medecin("dr.alaoui", "medecin123", "BK100200", "Alaoui", "Karim", "k.alaoui@alamal.ma",
                                "0661000001", "Casablanca", "Médecine générale", 200.0)
    sara = u.ajouter_patient("s.tazi", "patient123", "AB123456", "Tazi", "Sara", "sara.tazi@mail.ma", "0612345678",
                             "Settat", "1992-03-14", "F", None)
    omar = u.ajouter_patient("o.berrada", "patient123", "GH901234", "Berrada", "Omar", "omar.b@mail.ma", "0655987654",
                             "Casablanca", "1978-01-09", "M", "Aspirine")
    nadia = u.ajouter_patient("n.fassi", "patient123", "EF345678", "Fassi", "Nadia", "nadia.f@mail.ma", "0670123456",
                              "Settat", "2001-11-21", "F", "Pénicillines")
    for des, fam, forme, prix, stock, seuil in (
            ("Paracétamol 500 mg", "Antalgiques", "Comprimé", 12.0, 150, 40),
            ("Amoxicilline 1 g", "Pénicillines", "Comprimé", 38.0, 60, 20),
            ("Ibuprofène 400 mg", "Anti-inflammatoires", "Comprimé", 22.0, 6, 15),
            ("Vitamine D3", "Vitamines", "Ampoule", 55.0, 25, 10),
            ("Sirop antitussif", "Antitussifs", "Flacon", 30.0, 12, 10),
            ("Oméprazole 20 mg", "Antiacides", "Gélule", 45.0, 40, 15),
            ("Atorvastatine 20 mg", "Statines", "Comprimé", 70.0, 8, 10)):
        m.ajouter_medicament(des, fam, forme, prix, stock, seuil)
    today = date.today()
    consultations = ((150, sara, "Fièvre", "Syndrome grippal", [("Paracétamol 500 mg", 2, 12.0), ("Sirop antitussif", 1, 30.0)]),
                     (120, omar, "Maux de tête", "Céphalée de tension", [("Paracétamol 500 mg", 2, 12.0)]),
                     (90, nadia, "Toux", "Bronchite", [("Sirop antitussif", 1, 30.0), ("Vitamine D3", 1, 55.0)]),
                     (60, sara, "Contrôle", "RAS", []),
                     (30, omar, "Douleurs", "Lombalgie commune", [("Ibuprofène 400 mg", 2, 22.0)]),
                     (14, nadia, "Fatigue", "Anémie légère", [("Vitamine D3", 1, 55.0), ("Paracétamol 500 mg", 1, 12.0)]),
                     (4, sara, "Fièvre", "Rhinopharyngite", [("Paracétamol 500 mg", 3, 12.0)]))
    for i, (jours, patient, motif, diag, meds) in enumerate(consultations):
        jour = today - timedelta(days=jours)
        if jour.weekday() == 6:
            jour -= timedelta(days=1)
        id_rdv = r.ajouter_rdv(patient, medecin, "%s %02d:00" % (jour.isoformat(), 9 + i), motif)
        contenu = json.dumps([{"nom": n, "qte": q, "posologie": "1 prise, 3 fois par jour", "prix": p} for n, q, p in meds],
                             ensure_ascii=False) if meds else None
        r.enregistrer_consultation(id_rdv, diag, contenu, 200.0 + sum(q * p for _, q, p in meds))
        if i < len(consultations) - 1:
            r.enregistrer_paiement(id_rdv, ("Espèces", "Carte", "Chèque")[i % 3], jour.isoformat())
    futur = today + timedelta(days=1 if (today + timedelta(days=1)).weekday() != 6 else 2)
    r.modifier_statut(r.ajouter_rdv(sara, medecin, futur.isoformat() + " 09:30", "Suivi"), "PLANIFIE")
    r.modifier_statut(r.ajouter_rdv(omar, medecin, futur.isoformat() + " 11:00", "Bilan annuel"), "PLANIFIE")
    r.ajouter_rdv(nadia, medecin, futur.isoformat() + " 15:00", "Douleurs articulaires")