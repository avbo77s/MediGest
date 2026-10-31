
#pour ce fichier on etude le contenu de mot de passe cad on verifie si le mot depasse est bien ou il est facile et aussi on fait le hashage de motdepasse dans la base de donnes pour qu on obtient une base de donnee securisee
import hashlib #librarie des fonctions de hachage 
import secrets #nous donne la possiblite de faire hachage avec des variables cryptographiquement cad securise et ne permet pas l acces direct 

import hmac #il fait la comparaison 

"""Fonction	                   Rôle
hash_password()	         Transforme le mot de passe en empreinte sécurisée.
secrets.token_hex()	     Génère un sel aléatoire (salt).
hashlib.pbkdf2_hmac()	 Effectue le hachage avec SHA-256 et 200 000 itérations.
verifier_mot_de_passe()	 Vérifie si le mot de passe saisi est correct.
hmac.compare_digest()	 Compare les empreintes de manière sécurisée."""

def hash_password(mot_de_passe):
    # Generer un sel aleatoire un sel est comme une chose qui est unique  qui peut apparaitre dune facon multiple  multiple cad avec un exemple un motdepasse peut apparaitre dans plusieurs compte mais ils ont des empreintes differents
    sel = secrets.token_hex(16)

    # Hasher le mot de passe
    empreinte = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel.encode("utf-8"),
        200000
    ).hex()

    # Retourner le sel et le hash
    return sel + "$" + empreinte


def verifier_mot_de_passe(mot_de_passe, stockage):
    try:
        sel, empreinte_stockee = stockage.split("$", 1)
    except ValueError:
        return False

    # Recalculer le hash du mot de passe saisi
    empreinte = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel.encode("utf-8"),
        200000
    ).hex()

    # Comparer les deux empreintes
    return hmac.compare_digest(empreinte, empreinte_stockee)

# un exemple pour que vous bien comprendre le concept 
#mot_de_passe = "MediGest123"

# Hasher
#stockage = hash_password(mot_de_passe)

#print("Hash :", stockage)

# Tester le bon mot de passe
#print(verifier_mot_de_passe("MediGest123", stockage))

# Tester un mauvais mot de passe
#print(verifier_mot_de_passe("123456", stockage))
