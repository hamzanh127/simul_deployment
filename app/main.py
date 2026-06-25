"""
Point d'entree principal de l'application FastAPI.

Ce fichier est le point de depart de l'API web.

Important :
- on cree ici l'application FastAPI ;
- on cree une route directe `GET /` ;
- on branche le router qui expose les endpoints API ;
- le workflow LangGraph est appele par les endpoints du router ;
- on ne fait aucun appel Groq depuis cette route.

L'objectif est pedagogique : comprendre FastAPI avant d'ajouter des routes plus
avancees.

-------------------------------------------------------------------------------
Qu'est-ce que FastAPI ?
-------------------------------------------------------------------------------

FastAPI est un framework Python qui permet de creer des APIs HTTP.

Une API HTTP permet a un client d'envoyer des requetes a une application.
Exemples de clients :
- un navigateur ;
- une application frontend ;
- un script Python ;
- Postman ;
- un autre service backend.

FastAPI permet de declarer des routes comme :
- `GET /` pour lire une ressource ou verifier que l'API fonctionne ;
- `POST /incidents` pour envoyer des donnees, plus tard dans le projet.

Dans cette etape, on cree seulement `GET /`.

-------------------------------------------------------------------------------
Qu'est-ce qu'une Application FastAPI ?
-------------------------------------------------------------------------------

L'application FastAPI est l'objet central de l'API.

Dans le code, cet objet s'appelle souvent `app` :

    app = FastAPI()

Cet objet contient :
- le nom de l'API ;
- sa description ;
- ses routes ;
- sa documentation automatique ;
- sa configuration web.

Quand on lancera le serveur avec Uvicorn, Uvicorn cherchera cet objet `app` :

    uvicorn app.main:app --reload

Cette commande signifie :
- `app.main` : va dans le fichier Python `app/main.py` ;
- `app` : recupere la variable appelee `app` ;
- `--reload` : recharge automatiquement le serveur pendant le developpement.

-------------------------------------------------------------------------------
Qu'est-ce que Swagger ?
-------------------------------------------------------------------------------

Swagger est une interface web de documentation interactive.

Avec FastAPI, Swagger est genere automatiquement a partir des routes, des types
Python et des schemas Pydantic.

Une fois le serveur lance, Swagger est disponible par defaut ici :

    http://localhost:8000/docs

Swagger permet de :
- voir la liste des endpoints ;
- lire les parametres attendus ;
- tester les routes directement depuis le navigateur ;
- comprendre rapidement le contrat de l'API.

Dans cette etape, Swagger affichera :
- `GET /` ;
- `POST /realtime`.
- `POST /batch`.
- `POST /event`.
- `POST /streaming`.

-------------------------------------------------------------------------------
Qu'est-ce qu'un Router ?
-------------------------------------------------------------------------------

Un Router est un objet qui regroupe plusieurs routes.

Dans un projet plus grand, on evite souvent de mettre toutes les routes dans
`main.py`. On cree plutot des fichiers separes, par exemple :

    app/api/incidents.py

Puis on connecte ces routes a l'application principale.

Exemple :

    app.include_router(incident_router)

Le projet utilise maintenant un router separe dans `app/api/routes.py` pour les
routes `POST /realtime`, `POST /batch`, `POST /event` et `POST /streaming`.

Mais il est important de comprendre l'idee :
- `FastAPI` cree l'application principale ;
- un `Router` regroupe des routes par domaine ;
- `include_router` branche ces routes dans l'application.
"""

from fastapi import FastAPI

from app.api.routes import router


# -----------------------------------------------------------------------------
# Creation de l'application FastAPI
# -----------------------------------------------------------------------------
# `app` est l'objet principal que le serveur Uvicorn executera.
#
# Le nom `app` est une convention tres courante. Il permet d'ecrire ensuite :
#
#     uvicorn app.main:app --reload
#
# Le premier `app` correspond au dossier Python `app/`.
# `main` correspond au fichier `main.py`.
# Le dernier `app` correspond a cette variable.
app = FastAPI(
    # `title` apparaitra dans la documentation Swagger.
    # Il aide a identifier rapidement l'API.
    title="tp_langgraph_deployment",

    # `description` apparait aussi dans Swagger.
    # Elle donne le contexte general du projet.
    description=(
        "API pedagogique pour apprendre FastAPI, LangGraph et le deploiement."
    ),

    # `version` permet de documenter l'etat de l'API.
    # Ici, on demarre volontairement a une version initiale.
    version="0.1.0",
)


# -----------------------------------------------------------------------------
# Branchement du router API
# -----------------------------------------------------------------------------
# `include_router` connecte les routes declarees dans `app/api/routes.py` a
# l'application principale.
#
# Sans cette ligne, les endpoints declares dans `routes.py` existeraient dans
# leur fichier, mais FastAPI ne les exposerait pas dans l'application.
#
# En branchant le router ici :
# - Swagger affichera `POST /realtime`, `POST /batch`, `POST /event` et
#   `POST /streaming` ;
# - l'API acceptera les requetes vers `/realtime`, `/batch`, `/event` et
#   `/streaming` ;
# - `main.py` reste lisible, car les routes metier sont dans `app/api/routes.py`.
app.include_router(router)


# -----------------------------------------------------------------------------
# Route GET /
# -----------------------------------------------------------------------------
# `@app.get("/")` est un decorateur FastAPI.
#
# Un decorateur modifie ou enregistre une fonction.
# Ici, il dit a FastAPI :
#
# "Quand un client envoie une requete HTTP GET sur le chemin `/`,
# execute la fonction `read_root`."
#
# Exemple de requete :
#
#     GET http://localhost:8000/
#
# Cette route est souvent utilisee comme route d'accueil ou de verification.
@app.get("/")
def read_root() -> dict[str, str]:
    """
    Route d'accueil de l'API.

    Cette fonction est executee lorsqu'un client appelle `GET /`.

    Pourquoi retourner un dictionnaire ?
        FastAPI convertit automatiquement les dictionnaires Python en JSON.

        Le retour Python :

            {"message": "API tp_langgraph_deployment active"}

        devient une reponse HTTP JSON :

            {
              "message": "API tp_langgraph_deployment active"
            }

    Pourquoi ne pas appeler LangGraph ici ?
        Parce que cette route sert seulement a verifier que l'application web
        demarre correctement.

        La route qui recoit un incident et lance le workflow est maintenant
        `POST /realtime`.

    Pourquoi ce fichier ne definit-il pas directement le POST ?
        Le POST existe maintenant dans `app/api/routes.py`.
        Cette route `GET /` reste volontairement une route de verification.
    """

    # Ce dictionnaire sera automatiquement transforme en JSON par FastAPI.
    # Aucun workflow, aucun service IA et aucune logique metier ne sont appeles.
    return {
        "message": "API tp_langgraph_deployment active",
    }
