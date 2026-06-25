"""
Configuration centrale du projet.

Ce module a une responsabilite simple :
- charger les variables definies dans le fichier `.env` ;
- lire les valeurs importantes pour l'application ;
- verifier que les variables obligatoires existent ;
- exposer ces valeurs au reste du code de maniere claire.

Important :
Ce fichier ne doit pas contenir de logique metier. Il ne doit pas appeler le
modele, creer de workflow LangGraph ou definir d'endpoint FastAPI.
"""

import os

from dotenv import load_dotenv


# `load_dotenv()` lit automatiquement le fichier `.env` s'il existe a la racine
# du projet, puis ajoute les variables trouvees dans l'environnement Python.
#
# Exemple :
# Si le fichier `.env` contient :
#
# GROQ_API_KEY=gsk_xxxxxxxxx
# GROQ_MODEL=llama-3.1-8b-instant
#
# alors Python pourra ensuite lire ces valeurs avec `os.getenv(...)`.
#
# Le fichier `.env` est pratique en developpement local, car il evite d'ecrire
# des secrets directement dans le code source.
load_dotenv()


def _get_required_env(name: str) -> str:
    """
    Recupere une variable d'environnement obligatoire.

    Pourquoi utiliser une fonction dediee ?
    - cela evite de repeter la meme verification partout ;
    - cela rend les messages d'erreur plus clairs ;
    - cela permet d'echouer tot si la configuration est incomplete.

    Une variable absente ou vide provoque une erreur explicite. C'est mieux que
    laisser l'application demarrer puis echouer plus tard avec une erreur moins
    comprehensible.
    """

    value = os.getenv(name)

    # `os.getenv` renvoie `None` si la variable n'existe pas.
    # On verifie aussi `not value.strip()` pour refuser les valeurs vides ou
    # composees uniquement d'espaces.
    if value is None or not value.strip():
        raise RuntimeError(
            f"La variable d'environnement obligatoire `{name}` est absente. "
            "Ajoutez-la dans un fichier `.env` a la racine du projet."
        )

    # `.strip()` nettoie les espaces accidentels au debut ou a la fin.
    # Exemple : "  abc  " devient "abc".
    return value.strip()


# Cle API Groq.
#
# Cette cle permet d'authentifier les appels vers l'API Groq.
# Elle est volontairement lue depuis l'environnement et jamais ecrite en dur
# dans le code.
GROQ_API_KEY = _get_required_env("GROQ_API_KEY")


# Nom du modele Groq a utiliser.
#
# Le modele est aussi place dans `.env` pour rester facile a changer sans
# modifier le code. C'est utile en pedagogie : on peut comparer plusieurs
# modeles en changeant uniquement la configuration.
GROQ_MODEL = _get_required_env("GROQ_MODEL")


# Cette constante regroupe les variables exposees par ce module.
# Elle n'est pas indispensable, mais elle aide a lire rapidement ce que la
# configuration fournit au reste du projet.
__all__ = ["GROQ_API_KEY", "GROQ_MODEL"]
