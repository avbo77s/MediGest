create table if not exists Users (
    id_user integer primary key ,
    login varchar not null unique,
    mot_de_passe_hash varchar not null,
    role varchar check (lower(role) in ('medecin','patient')) not null,
    cin varchar not null unique ,
    nom varchar not null,
    prenom varchar not null,
    telephone varchar unique,
    email varchar unique not null,
    adresse varchar,
    actif INTEGER NOT NULL DEFAULT 1
        CHECK (actif IN (0, 1)),
    date_naissance date ,
    sexe varchar check(lower(sexe) in('m','f')) ,
    allergies varchar,
    specialite varchar,
    tarif REAL CHECK (tarif IS NULL OR tarif >= 0)

);
create table if not exists rendez_vous(
    id_rendezvous integer primary key,
    id_patient integer not null references Users(id_user),
    id_medecin integer not null references Users(id_user),
    date_heure datetime not null ,
    statut text not null default "DEMANDE"
        CHECK (statut IN ('DEMANDE', 'PLANIFIE', 'HONORE', 'ANNULE')),
    motif text not null,
    ordonnance text,
    diagnostic text,
    montant REAL CHECK (montant IS NULL OR montant >= 0),
    paiement check(lower(paiement) in ('impaye','paye')) default 'impaye' not null ,
    mode_paiement varchar,
    date_paiement date,
    CHECK (id_patient <> id_medecin)

);
create table if not exists medicament(
    id_med integer primary key,
    designation varchar not null unique ,
    famille_med varchar not null,
    forme varchar not null,
    prix real not null CHECK (prix >= 0),
    stock integer CHECK(stock >= 0) default 1 not null,
    seuil INTEGER NOT NULL DEFAULT 0 CHECK (seuil >= 0)
);