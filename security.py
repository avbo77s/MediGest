# Fonctions de sécurité pour le hachage et la vérification des mots de passe
import hashlib  # Bibliothèque de fonctions de hachage cryptographique
import hmac     # Permet de comparer les empreintes sans fuite d'informations
import secrets  # Générateur cryptographiquement sûr pour créer le sel aléatoire


def hash_password(mot_de_passe):
    # On génère un sel aléatoire de 16 octets (hexadécimal)
    # Deux utilisateurs avec le même mot de passe auront un sel et donc un hash différent
    sel = secrets.token_hex(16)

    # On hache le mot de passe avec l'algorithme PBKDF2 et SHA-256 avec 200 000 itérations
    empreinte = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel.encode("utf-8"),
        200000
    ).hex()

    # On enregistre le sel et l'empreinte ensemble, séparés par un dollar
    return sel + "$" + empreinte


def verifier_mot_de_passe(mot_de_passe, stockage):
    # Découpe la chaîne enregistrée pour récupérer le sel et le hash
    try:
        sel, empreinte_stockee = stockage.split("$", 1)
    except ValueError:
        return False

    # On recalcule le hash du mot de passe saisi avec le sel d'origine
    empreinte = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel.encode("utf-8"),
        200000
    ).hex()

    # On compare les deux empreintes de manière sécurisée contre les attaques de timing
    return hmac.compare_digest(empreinte, empreinte_stockee)


if __name__ == "__main__":
    # Test rapide de hachage et vérification
    mdp_test = "MediGest123"
    hache = hash_password(mdp_test)
    assert verifier_mot_de_passe(mdp_test, hache) is True
    assert verifier_mot_de_passe("mauvais_mdp", hache) is False
    print("Test security.py OK : Hachage et vérification réussis.")
