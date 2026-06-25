"""
Script de test massif pour l'endpoint streaming.

Objectif :
Envoyer automatiquement un incident toutes les 3 secondes vers :

    http://127.0.0.1:8001/streaming

Ce script sert a demontrer un flux continu d'incidents, comme dans un contexte
MLOps ou DevOps :
- monitoring ;
- alerting ;
- incidents de deploiement ;
- erreurs d'inference ;
- indisponibilites de services ;
- derive de donnees.

Le script tourne en boucle infinie et s'arrete proprement avec Ctrl + C.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

import requests


# URL par defaut de l'endpoint streaming.
#
# Elle correspond a l'API FastAPI lancee localement sur le port 8001.
API_URL = "http://127.0.0.1:8001/streaming"


# Timeout HTTP en secondes.
#
# Meme si le script attend 3 secondes entre deux envois, chaque requete HTTP a
# aussi besoin d'un timeout pour eviter de rester bloquee indefiniment si l'API
# ne repond pas.
TIMEOUT_SECONDS = 60


# Intervalle entre deux incidents.
#
# La valeur est centralisee ici pour etre reutilisee dans les messages et dans
# `time.sleep(...)`.
SLEEP_SECONDS = 3


# Liste d'incidents MLOps / DevOps.
#
# Le script enverra ces incidents un par un, puis recommencera au debut de la
# liste. Cela permet de simuler un flux continu.
INCIDENTS = [
    "Le deploiement Kubernetes echoue.",
    "Le serveur PostgreSQL ne repond plus depuis le service API.",
    "Le taux d'erreur HTTP 500 depasse 20% sur le backend.",
    "La latence du modele d'inference depasse 8 secondes.",
    "Redis est indisponible, les sessions utilisateurs expirent.",
    "Le pipeline CI/CD echoue pendant l'etape de tests unitaires.",
    "Le taux de predictions invalides augmente brutalement.",
    "La derive de donnees est detectee sur la variable transaction_amount.",
    "Le service de feature store retourne des timeouts repetes.",
    "La consommation CPU du worker d'inference reste a 100%.",
    "Le endpoint de monitoring Prometheus ne repond plus.",
    "Le volume de logs d'erreur augmente apres le dernier deploy.",
]


def format_json(data: Any) -> str:
    """
    Formate une donnee Python en JSON lisible.

    Cette fonction est utilisee pour afficher proprement les reponses recues.
    Si la donnee n'est pas serialisable en JSON, on la convertit en texte.
    """

    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except TypeError:
        return str(data)


def send_streaming_incident(incident: str) -> None:
    """
    Envoie un incident vers l'endpoint `/streaming`.

    Le format envoye respecte la consigne :

        {
          "text": "incident ici"
        }

    L'endpoint streaming renvoie plusieurs lignes JSON. On lit donc la reponse
    avec `stream=True` et `iter_lines()`.
    """

    payload = {"text": incident}
    sent_at = datetime.now()

    print("=" * 80)
    print(f"Date/heure d'envoi : {sent_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Incident envoye    : {incident}")
    print(f"Endpoint           : {API_URL}")
    print("-" * 80)

    try:
        # `stream=True` indique a requests de ne pas attendre toute la reponse
        # avant de nous rendre la main.
        #
        # C'est important pour un endpoint streaming : on veut lire les morceaux
        # au fur et a mesure.
        response = requests.post(
            API_URL,
            json=payload,
            timeout=TIMEOUT_SECONDS,
            stream=True,
        )

        print(f"Status HTTP        : {response.status_code}")
        print("Reponse JSON formatee :")

        # `iter_lines()` permet de lire la reponse ligne par ligne.
        #
        # Dans ce projet, `/streaming` renvoie du NDJSON :
        # une ligne JSON par event.
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            try:
                event = json.loads(line)
                print(format_json(event))
            except json.JSONDecodeError:
                print(line)

    except requests.RequestException as exc:
        # Cette exception couvre les erreurs reseau :
        # - API eteinte ;
        # - mauvais port ;
        # - timeout ;
        # - connexion refusee ;
        # - probleme HTTP bas niveau.
        print("Erreur : l'API ne repond pas.")
        print(f"Detail : {exc}")


def main() -> None:
    """
    Boucle principale du script.

    Le script parcourt la liste d'incidents en boucle infinie.

    Ctrl + C declenche `KeyboardInterrupt`, ce qui permet d'arreter proprement
    le programme avec un message clair.
    """

    print("Demarrage du test streaming massif.")
    print("Un incident sera envoye automatiquement toutes les 3 secondes.")
    print("Appuyez sur Ctrl + C pour arreter le script.")
    print()

    index = 0

    try:
        while True:
            incident = INCIDENTS[index % len(INCIDENTS)]
            send_streaming_incident(incident)

            index += 1

            print("-" * 80)
            print(f"Attente de {SLEEP_SECONDS} secondes avant le prochain incident...")
            print()

            # Pause entre deux incidents.
            #
            # On utilise volontairement `time.sleep(SLEEP_SECONDS)` pour simuler
            # un flux periodique simple.
            time.sleep(SLEEP_SECONDS)

    except KeyboardInterrupt:
        print()
        print("Arret demande avec Ctrl + C.")
        print("Fin propre du test streaming massif.")


if __name__ == "__main__":
    main()
