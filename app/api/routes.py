"""
Routes API du projet.

Ce fichier contient les endpoints FastAPI lies a l'analyse d'incidents.

Pour l'instant, il contient :

    POST /realtime
    POST /batch
    POST /event
    POST /streaming

Important :
- on ne cree pas de route GET ici ;
- `POST /realtime` analyse un seul incident ;
- `POST /batch` analyse plusieurs incidents ;
- `POST /event` simule un declenchement automatique par evenement ;
- `POST /streaming` renvoie progressivement les evenements du graphe ;
- les endpoints appellent le workflow LangGraph minimal.

-------------------------------------------------------------------------------
Qu'est-ce qu'une Request ?
-------------------------------------------------------------------------------

Une `Request` est la requete envoyee par le client vers l'API.

Pour un endpoint POST, la request contient souvent un corps JSON.

Exemple de request envoyee a `POST /realtime` :

{
  "title": "Erreur 500 sur l'API",
  "description": "La creation de compte retourne une erreur serveur.",
  "severity": "critical",
  "source": "monitoring"
}

Dans ce fichier, la request est representee par le schema Pydantic
`IncidentRequest` pour le mode temps reel, et par `BatchRequest` pour le mode
batch.

FastAPI utilise ce schema pour :
- lire le JSON envoye par le client ;
- verifier que les champs obligatoires existent ;
- verifier que les types sont corrects ;
- afficher la structure attendue dans Swagger ;
- retourner une erreur claire si la request est invalide.

-------------------------------------------------------------------------------
Qu'est-ce qu'une Response ?
-------------------------------------------------------------------------------

Une `Response` est la reponse envoyee par l'API vers le client.

Dans FastAPI, si une fonction retourne un dictionnaire Python, FastAPI le
convertit automatiquement en JSON.

Exemple de response possible :

{
  "analysis": "Resume : ..."
}

Dans cette etape, on retourne principalement l'analyse produite par LangGraph.

-------------------------------------------------------------------------------
Quelle difference entre Real-Time et Batch ?
-------------------------------------------------------------------------------

Le mode Real-Time (`POST /realtime`) traite un seul incident.

Il est utile quand :
- un incident vient d'arriver ;
- on veut une reponse immediate ;
- le client attend une analyse pour une seule situation.

Le mode Batch (`POST /batch`) traite plusieurs incidents dans une seule requete.

Il est utile quand :
- on a une liste d'incidents a analyser ;
- on veut eviter d'appeler l'API une fois par incident depuis le client ;
- on veut obtenir une liste de resultats en une seule response.

Dans ce TP, le mode batch reste simple : il utilise une boucle Python.
Pour chaque incident de la liste, on appelle le meme workflow LangGraph.

-------------------------------------------------------------------------------
Qu'est-ce que graph.invoke() ?
-------------------------------------------------------------------------------

`graph.invoke()` est la methode qui execute un graphe LangGraph compile.

Dans notre projet :

    incident_workflow.invoke(initial_state)

signifie :
1. prendre le State initial ;
2. demarrer au point d'entree du graphe ;
3. executer le node `analyze_incident` ;
4. appeler le service Groq depuis ce node ;
5. recuperer la mise a jour `{"analysis": ...}` ;
6. fusionner cette mise a jour dans le State ;
7. retourner le State final.

Le endpoint ne parle donc pas directement a Groq.
Il appelle le graphe.
Le graphe appelle le node.
Le node appelle le service Groq.

Cette separation rend le projet plus clair.

-------------------------------------------------------------------------------
Pourquoi utiliser une boucle en mode Batch ?
-------------------------------------------------------------------------------

Une request batch contient plusieurs incidents :

{
  "items": [
    {"title": "...", "description": "...", "severity": "...", "source": "..."},
    {"title": "...", "description": "...", "severity": "...", "source": "..."}
  ]
}

Le workflow actuel sait analyser un State d'incident a la fois.

On utilise donc une boucle pour :
1. prendre le premier incident ;
2. le transformer en State initial ;
3. appeler `graph.invoke()` ;
4. stocker le resultat ;
5. passer a l'incident suivant.

Cette approche est volontairement pedagogique. Plus tard, on pourra etudier des
strategies plus avancees : parallelisation, file de jobs, workers, retries,
limitation de debit, etc.

-------------------------------------------------------------------------------
Pourquoi appeler graph.invoke() plusieurs fois ?
-------------------------------------------------------------------------------

Chaque appel a `graph.invoke()` represente une execution independante du graphe.

En mode batch, chaque incident doit avoir son propre State :
- incident 1 -> State 1 -> graph.invoke(State 1) -> resultat 1 ;
- incident 2 -> State 2 -> graph.invoke(State 2) -> resultat 2 ;
- incident 3 -> State 3 -> graph.invoke(State 3) -> resultat 3.

On evite ainsi de melanger les donnees de plusieurs incidents dans une seule
execution du graphe.

-------------------------------------------------------------------------------
Qu'est-ce qu'un Webhook ?
-------------------------------------------------------------------------------

Un webhook est un appel HTTP envoye automatiquement par un systeme externe vers
notre API.

Au lieu que notre application demande regulierement :
"Est-ce qu'il y a un nouvel incident ?"

le systeme externe appelle directement notre endpoint quand quelque chose se
produit.

Exemple :
- un outil de monitoring detecte une erreur ;
- il envoie automatiquement une requete POST vers `/event` ;
- notre API recoit l'evenement ;
- notre API lance le workflow LangGraph ;
- l'incident est analyse sans intervention manuelle.

-------------------------------------------------------------------------------
Qu'est-ce qu'un Evenement ?
-------------------------------------------------------------------------------

Un evenement est un message qui signale qu'une chose vient de se produire.

Exemples :
- CPU trop eleve ;
- erreur 500 detectee ;
- latence anormale ;
- modele ML qui retourne trop d'erreurs ;
- chute de qualite d'un modele ;
- alerte de monitoring.

Dans une architecture event-driven, les traitements sont declenches par ces
evenements.

-------------------------------------------------------------------------------
Quel lien avec le Monitoring ?
-------------------------------------------------------------------------------

Le monitoring observe un systeme en continu.

Il peut surveiller :
- la disponibilite d'une API ;
- les temps de reponse ;
- les erreurs ;
- l'utilisation CPU ou memoire ;
- les performances d'un modele ML ;
- les anomalies dans les predictions.

Quand le monitoring detecte un probleme, il peut emettre un evenement.
Cet evenement peut ensuite declencher automatiquement une analyse.

-------------------------------------------------------------------------------
Qu'est-ce qu'un declenchement automatique ?
-------------------------------------------------------------------------------

Un declenchement automatique signifie qu'un traitement commence sans action
humaine directe.

Dans ce projet :
- Real-Time : un client appelle volontairement `/realtime` ;
- Batch : un client envoie volontairement une liste a `/batch` ;
- Event-Driven : un systeme externe appelle automatiquement `/event`.

Le mode event-driven est important en MLOps, car les systemes de machine
learning doivent souvent reagir a des signaux de production :
- derive de donnees ;
- baisse de performance ;
- erreurs d'inference ;
- indisponibilite d'un service ;
- alertes de monitoring.

L'objectif est de rapprocher l'observation, l'alerte et l'action.

-------------------------------------------------------------------------------
Qu'est-ce que le Streaming ?
-------------------------------------------------------------------------------

Le streaming consiste a envoyer une reponse progressivement au lieu d'attendre
que tout le traitement soit termine.

Avec une reponse classique :
1. le serveur recoit la request ;
2. le serveur fait tout le travail ;
3. le serveur renvoie une seule response finale.

Avec une reponse streaming :
1. le serveur recoit la request ;
2. le serveur commence le travail ;
3. le serveur envoie un premier morceau ;
4. le serveur continue le travail ;
5. le serveur envoie d'autres morceaux ;
6. le serveur finit quand le workflow est termine.

Le streaming est utile quand :
- un traitement peut prendre du temps ;
- on veut montrer la progression ;
- on veut recevoir les resultats intermediaires ;
- on veut eviter une impression de blocage cote client.

-------------------------------------------------------------------------------
Qu'est-ce qu'un Event dans le streaming LangGraph ?
-------------------------------------------------------------------------------

Dans `graph.stream()`, un event est un morceau d'information produit pendant
l'execution du graphe.

Un event peut indiquer par exemple :
- qu'un node vient de produire une mise a jour ;
- quelles cles du State ont ete modifiees ;
- quelle etape du graphe vient de se terminer.

Dans notre workflow minimal, il n'y a qu'un seul node. Le streaming sera donc
tres court, mais il montre deja le principe.

-------------------------------------------------------------------------------
Qu'est-ce que yield ?
-------------------------------------------------------------------------------

`yield` est un mot-cle Python utilise dans les generateurs.

Une fonction classique avec `return` renvoie une seule valeur puis s'arrete.

Une fonction avec `yield` peut renvoyer plusieurs valeurs, une par une.

Dans FastAPI, `StreamingResponse` peut consommer un generateur :
- chaque `yield` devient un morceau envoye au client ;
- le client peut recevoir les donnees progressivement ;
- le serveur n'a pas besoin de construire toute la response avant d'envoyer.

-------------------------------------------------------------------------------
Quelle difference entre invoke() et stream() ?
-------------------------------------------------------------------------------

`graph.invoke(initial_state)` :
- execute le graphe complet ;
- attend la fin ;
- retourne le State final ;
- convient aux endpoints classiques comme `/realtime`.

`graph.stream(initial_state)` :
- execute aussi le graphe ;
- renvoie des events progressivement ;
- permet d'observer les etapes intermediaires ;
- convient aux endpoints streaming comme `/streaming`.

En resume :
- `invoke()` donne le resultat final ;
- `stream()` donne le deroulement progressif.
"""

import json
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.incident_schema import BatchRequest, IncidentRequest


# -----------------------------------------------------------------------------
# Creation du router
# -----------------------------------------------------------------------------
# `APIRouter` permet de regrouper des routes dans un fichier dedie.
#
# Au lieu de declarer toutes les routes dans `app/main.py`, on les place ici.
# Ensuite, `main.py` branche ce router dans l'application principale avec :
#
#     app.include_router(router)
#
# Cela garde `main.py` simple et prepare une meilleure organisation du projet.
router = APIRouter()


# -----------------------------------------------------------------------------
# Endpoint POST /realtime
# -----------------------------------------------------------------------------
# `@router.post("/realtime")` enregistre une route HTTP POST.
#
# POST est utilise quand le client envoie des donnees a l'API.
# Ici, le client envoie un incident a analyser.
#
# Chemin complet :
#
#     POST http://localhost:8000/realtime
#
# Ce endpoint est visible dans Swagger apres lancement de l'application :
#
#     http://localhost:8000/docs
@router.post("/realtime")
def analyze_realtime_incident(request: IncidentRequest) -> dict[str, str]:
    """
    Analyse un incident en temps reel avec le workflow LangGraph.

    Parametre :
        request:
            Objet Pydantic construit automatiquement par FastAPI a partir du
            JSON envoye par le client.

            Exemple JSON :

            {
              "title": "Erreur 500 sur l'API",
              "description": "La creation de compte retourne une erreur serveur.",
              "severity": "critical",
              "source": "monitoring"
            }

    Retour :
        Dictionnaire converti automatiquement en JSON par FastAPI.

        Exemple :

        {
          "analysis": "Resume : ..."
        }
    """

    # -------------------------------------------------------------------------
    # 1. Transformation de la Request en State initial
    # -------------------------------------------------------------------------
    # FastAPI nous donne `request` sous forme d'objet Pydantic.
    #
    # LangGraph, lui, travaille avec un State, c'est-a-dire un dictionnaire.
    #
    # On convertit donc explicitement la request en dictionnaire compatible avec
    # `IncidentState`.
    #
    # Pydantic v2 fournit `.model_dump()` pour convertir un modele en dict.
    initial_state = request.model_dump()

    # -------------------------------------------------------------------------
    # 2. Import du workflow LangGraph
    # -------------------------------------------------------------------------
    # On importe le workflow ici, a l'interieur du endpoint.
    #
    # Pourquoi ?
    # Le workflow finit par utiliser le service Groq, qui depend de variables
    # d'environnement comme `GROQ_API_KEY` et `GROQ_MODEL`.
    #
    # En important le workflow au moment de l'appel, l'application FastAPI peut
    # encore demarrer et afficher Swagger meme si la configuration Groq n'est pas
    # encore prete.
    #
    # Quand le client appelle vraiment `POST /realtime`, la configuration doit
    # alors etre correcte.
    from app.graph.workflow import incident_workflow

    # -------------------------------------------------------------------------
    # 3. Execution du graphe avec graph.invoke()
    # -------------------------------------------------------------------------
    # `incident_workflow` est le graphe compile dans `app/graph/workflow.py`.
    #
    # `.invoke(initial_state)` lance le graphe avec le State initial.
    #
    # Dans notre workflow minimal :
    # - LangGraph commence par le node `analyze_incident` ;
    # - le node appelle `analyze_with_groq()` ;
    # - le node retourne `{"analysis": analysis}` ;
    # - LangGraph fusionne cette analyse dans le State ;
    # - le graphe atteint END ;
    # - LangGraph retourne le State final.
    final_state = incident_workflow.invoke(initial_state)

    # -------------------------------------------------------------------------
    # 4. Construction de la Response
    # -------------------------------------------------------------------------
    # Le State final contient les champs d'entree plus les champs ajoutes par le
    # graphe.
    #
    # Ici, on choisit de retourner uniquement `analysis` pour garder la response
    # simple et claire.
    #
    # `final_state.get("analysis", "")` evite une erreur si, pour une raison
    # inattendue, le graphe ne produit pas la cle `analysis`.
    return {
        "analysis": final_state.get("analysis", ""),
    }


# -----------------------------------------------------------------------------
# Endpoint POST /batch
# -----------------------------------------------------------------------------
# `@router.post("/batch")` enregistre une deuxieme route HTTP POST.
#
# Cette route recoit plusieurs incidents dans une seule request.
#
# Chemin complet :
#
#     POST http://localhost:8000/batch
#
# Exemple de request :
#
# {
#   "items": [
#     {
#       "title": "Erreur 500 sur l'API",
#       "description": "La creation de compte retourne une erreur serveur.",
#       "severity": "critical",
#       "source": "monitoring"
#     },
#     {
#       "title": "Application lente",
#       "description": "Les pages mettent plus de 10 secondes a charger.",
#       "severity": "medium",
#       "source": "support"
#     }
#   ]
# }
@router.post("/batch")
def analyze_batch_incidents(request: BatchRequest) -> dict[str, list[dict[str, str]]]:
    """
    Analyse plusieurs incidents avec le workflow LangGraph.

    Parametre :
        request:
            Objet Pydantic de type `BatchRequest`.

            Il contient une liste `items`.
            Chaque element de `items` est un `IncidentRequest`.

    Retour :
        Un dictionnaire contenant une liste de resultats.

        Exemple :

        {
          "results": [
            {
              "title": "Erreur 500 sur l'API",
              "analysis": "Resume : ..."
            },
            {
              "title": "Application lente",
              "analysis": "Resume : ..."
            }
          ]
        }

    Difference avec `POST /realtime` :
        - `/realtime` recoit un seul incident et retourne une seule analyse ;
        - `/batch` recoit plusieurs incidents et retourne plusieurs analyses.
    """

    # -------------------------------------------------------------------------
    # 1. Import du workflow LangGraph
    # -------------------------------------------------------------------------
    # Comme dans `/realtime`, on importe le workflow dans le endpoint.
    #
    # Cela garde le demarrage de FastAPI plus souple : Swagger peut s'afficher
    # meme si la configuration Groq n'est pas encore prete.
    #
    # Le workflow sera vraiment charge quand le client appellera `/batch`.
    from app.graph.workflow import incident_workflow

    # -------------------------------------------------------------------------
    # 2. Preparation de la liste des resultats
    # -------------------------------------------------------------------------
    # En mode batch, la response doit contenir plusieurs analyses.
    #
    # On cree donc une liste vide, puis on y ajoutera le resultat de chaque
    # execution du graphe.
    results: list[dict[str, str]] = []

    # -------------------------------------------------------------------------
    # 3. Boucle sur les incidents
    # -------------------------------------------------------------------------
    # `request.items` contient la liste des incidents envoyes par le client.
    #
    # Pourquoi une boucle ?
    # Parce que le workflow actuel analyse un incident a la fois.
    #
    # La boucle permet de repeter exactement le meme traitement pour chaque
    # incident :
    # - convertir l'incident en State ;
    # - appeler LangGraph ;
    # - recuperer l'analyse ;
    # - stocker le resultat.
    for incident in request.items:
        # ---------------------------------------------------------------------
        # 3.1. Transformation de l'incident en State initial
        # ---------------------------------------------------------------------
        # Chaque `incident` est un modele Pydantic `IncidentRequest`.
        #
        # LangGraph attend un dictionnaire de State.
        #
        # `.model_dump()` transforme donc :
        #
        # IncidentRequest(...)
        #
        # en :
        #
        # {
        #   "title": "...",
        #   "description": "...",
        #   "severity": "...",
        #   "source": "..."
        # }
        initial_state = incident.model_dump()

        # ---------------------------------------------------------------------
        # 3.2. Execution independante du graphe
        # ---------------------------------------------------------------------
        # On appelle `graph.invoke()` une fois par incident.
        #
        # Pourquoi plusieurs appels ?
        # Parce que chaque incident doit etre analyse dans son propre contexte.
        #
        # Si on mettait tous les incidents dans un seul State, le node actuel ne
        # saurait pas les traiter correctement : il attend les champs d'un seul
        # incident (`title`, `description`, `severity`, `source`).
        #
        # Ici, chaque appel produit son propre State final.
        final_state = incident_workflow.invoke(initial_state)

        # ---------------------------------------------------------------------
        # 3.3. Stockage du resultat
        # ---------------------------------------------------------------------
        # On garde le titre pour aider le client a relier chaque analyse a
        # l'incident d'origine.
        #
        # On garde aussi l'analyse produite par le graphe.
        results.append(
            {
                "title": initial_state.get("title", ""),
                "analysis": final_state.get("analysis", ""),
            }
        )

    # -------------------------------------------------------------------------
    # 4. Construction de la Response batch
    # -------------------------------------------------------------------------
    # La response batch contient une cle `results`.
    #
    # Cette cle contient une liste, car il y a potentiellement plusieurs
    # incidents analyses.
    #
    # FastAPI transformera automatiquement ce dictionnaire Python en JSON.
    return {
        "results": results,
    }


# -----------------------------------------------------------------------------
# Endpoint POST /event
# -----------------------------------------------------------------------------
# `@router.post("/event")` enregistre une route HTTP POST pour le mode
# event-driven.
#
# "Event-driven" signifie "declenche par evenement".
#
# Dans un systeme reel, cette route pourrait etre appelee automatiquement par :
# - un outil de monitoring ;
# - une plateforme d'alerting ;
# - un outil MLOps ;
# - un systeme de logs ;
# - un orchestrateur ;
# - un webhook GitOps ou DevOps.
#
# Chemin complet :
#
#     POST http://localhost:8000/event
#
# Exemple de request envoyee automatiquement par GitHub :
#
# {
#   "ref": "refs/heads/main",
#   "repository": {
#     "name": "tp_langgraph_deployment"
#   },
#   "head_commit": {
#     "message": "fix: update deployment workflow"
#   }
# }
@router.post("/event")
async def event_driven(request: Request) -> dict[str, object]:
    """
    Analyse un evenement recu par webhook.

    Parametre :
        request:
            Requete HTTP brute recue par FastAPI.

            Ici, on n'utilise pas `IncidentRequest`, car un webhook GitHub ne
            suit pas notre schema d'incident classique.

            GitHub envoie un payload avec des champs comme :
            - repository ;
            - ref ;
            - head_commit.

            Un webhook generique peut aussi envoyer un payload plus simple,
            par exemple :

            {
              "text": "Le pipeline CI a echoue sur la branche main."
            }

    Retour :
        Une response JSON indiquant :
        - le mode utilise ;
        - la source detectee ;
        - si l'evenement a ete recu ;
        - le texte envoye au graphe ;
        - l'analyse produite.

        Exemple :

        {
          "mode": "event-driven",
          "source": "github-webhook",
          "event_received": true,
          "input_event": "Webhook GitHub recu. Repository: ...",
          "result": "Resume : ..."
        }

    Pourquoi cette route est plus proche d'un vrai event ?
        Parce qu'elle accepte le JSON brut d'un outil externe, ici GitHub, puis
        transforme ce payload technique en texte d'incident analysable par le
        workflow LangGraph.

        C'est le principe d'un webhook : un service externe declenche notre API
        automatiquement quand un evenement se produit.
    """

    # -------------------------------------------------------------------------
    # 1. Lecture du payload JSON brut
    # -------------------------------------------------------------------------
    # `Request` est l'objet FastAPI/Starlette qui represente la requete HTTP
    # complete.
    #
    # `await request.json()` lit le body JSON envoye par le webhook.
    #
    # Pourquoi `await` ?
    # La lecture du body est une operation d'entree/sortie. FastAPI permet de la
    # faire en asynchrone pour ne pas bloquer inutilement le serveur.
    payload = await request.json()

    # -------------------------------------------------------------------------
    # 2. Detection d'un webhook GitHub
    # -------------------------------------------------------------------------
    # Un webhook GitHub de type push contient generalement `head_commit`.
    #
    # Si cette cle existe, on considere que l'evenement vient de GitHub.
    #
    # On transforme ensuite le payload GitHub en texte comprehensible par le LLM.
    # Cela evite d'envoyer tout le JSON brut au modele.
    if "head_commit" in payload:
        incident_text = (
            "Webhook GitHub recu. "
            f"Repository: {payload.get('repository', {}).get('name', 'unknown')}. "
            f"Branche: {payload.get('ref', 'unknown')}. "
            f"Commit: {payload.get('head_commit', {}).get('message', 'no message')}."
        )

    # -------------------------------------------------------------------------
    # 3. Detection d'un webhook generique avec champ text
    # -------------------------------------------------------------------------
    # Certains outils d'alerte ou de monitoring envoient simplement un champ
    # `text`.
    #
    # Exemple :
    #
    # {
    #   "text": "Le pipeline CI a echoue sur main."
    # }
    #
    # Dans ce cas, on utilise directement ce texte comme incident.
    elif "text" in payload:
        incident_text = payload["text"]

    # -------------------------------------------------------------------------
    # 4. Fallback pour payload inconnu
    # -------------------------------------------------------------------------
    # Si le payload n'est ni un webhook GitHub reconnu ni un message textuel
    # simple, on garde tout de meme une trace lisible de l'evenement.
    #
    # Cela permet au workflow de recevoir quelque chose a analyser, meme si le
    # format n'est pas encore explicitement supporte.
    else:
        incident_text = f"Webhook recu : {payload}"

    # -------------------------------------------------------------------------
    # 5. Import du workflow LangGraph
    # -------------------------------------------------------------------------
    # On importe le graphe compile ici, au moment ou l'evenement arrive.
    #
    # On le renomme en `graph` pour rendre la ligne demandee tres lisible :
    #
    #     result = graph.invoke(...)
    from app.graph.workflow import incident_workflow as graph

    # -------------------------------------------------------------------------
    # 6. Declenchement automatique du graphe
    # -------------------------------------------------------------------------
    # Cette ligne est le coeur du mode event-driven.
    #
    # Un evenement externe arrive.
    # On le transforme en texte.
    # Puis on lance LangGraph automatiquement.
    #
    # Le State envoye au graphe contient ici une seule cle :
    #
    # {
    #   "incident": incident_text
    # }
    #
    # Le node `analyze_incident_node` sait maintenant transformer cette cle en
    # entree compatible avec le service Groq.
    result = graph.invoke({"incident": incident_text})

    # -------------------------------------------------------------------------
    # 7. Construction de la response
    # -------------------------------------------------------------------------
    # `source` indique si l'evenement ressemble a un webhook GitHub ou a un
    # webhook generique.
    #
    # `event_received` confirme que l'API a bien recu et traite l'evenement.
    #
    # `input_event` montre le texte qui a ete donne au graphe.
    #
    # `result` contient l'analyse ajoutee au State par LangGraph.
    return {
        "mode": "event-driven",
        "source": "github-webhook" if "head_commit" in payload else "generic-webhook",
        "event_received": True,
        "input_event": incident_text,
        "result": result["analysis"],
    }


# -----------------------------------------------------------------------------
# Endpoint POST /streaming
# -----------------------------------------------------------------------------
# `@router.post("/streaming")` enregistre une route HTTP POST qui renvoie une
# reponse progressive.
#
# Cette route illustre `graph.stream()`.
#
# Chemin complet :
#
#     POST http://localhost:8000/streaming
#
# Exemple de request :
#
# {
#   "title": "Erreur 500 sur l'API",
#   "description": "La creation de compte retourne une erreur serveur.",
#   "severity": "critical",
#   "source": "monitoring"
# }
@router.post("/streaming")
def stream_incident_analysis(request: IncidentRequest) -> StreamingResponse:
    """
    Analyse un incident en mode streaming avec LangGraph.

    Parametre :
        request:
            Incident envoye par le client.

            Comme pour `/realtime`, on utilise `IncidentRequest`.

    Retour :
        Une `StreamingResponse`.

        Contrairement aux endpoints qui retournent un dictionnaire, une
        `StreamingResponse` envoie plusieurs morceaux de texte au client.

        Dans ce TP, chaque morceau est une ligne JSON.

        Exemple de flux :

        {"event": "start", "message": "Demarrage du streaming"}
        {"event": "graph_event", "data": {...}}
        {"event": "end", "message": "Streaming termine"}

    Pourquoi utiliser le streaming ici ?
        Pour montrer que LangGraph peut exposer les etapes d'execution au fur et
        a mesure, au lieu de retourner seulement le State final.
    """

    # -------------------------------------------------------------------------
    # 1. Transformation de la Request en State initial
    # -------------------------------------------------------------------------
    # Le client envoie un JSON valide par Pydantic.
    #
    # LangGraph attend un dictionnaire de State.
    #
    # On transforme donc l'objet `IncidentRequest` en dictionnaire.
    initial_state = request.model_dump()

    # -------------------------------------------------------------------------
    # 2. Definition d'un generateur Python
    # -------------------------------------------------------------------------
    # Une `StreamingResponse` attend un iterable ou un generateur.
    #
    # Ici, on cree une fonction interne `event_generator`.
    #
    # Cette fonction utilise `yield` pour envoyer plusieurs morceaux de reponse.
    #
    # Pourquoi une fonction interne ?
    # - elle garde le code du streaming proche du endpoint ;
    # - elle a acces a `initial_state` ;
    # - elle permet a FastAPI d'envoyer la reponse progressivement.
    def event_generator() -> Iterator[str]:
        # ---------------------------------------------------------------------
        # 2.1. Premier event : demarrage
        # ---------------------------------------------------------------------
        # On envoie un premier morceau au client pour signaler que le traitement
        # commence.
        #
        # `json.dumps(...)` transforme un dictionnaire Python en texte JSON.
        #
        # `+ "\n"` ajoute une fin de ligne.
        # Le format obtenu s'appelle souvent NDJSON :
        # une ligne JSON par event.
        yield json.dumps(
            {
                "event": "start",
                "message": "Demarrage du streaming LangGraph.",
            }
        ) + "\n"

        # ---------------------------------------------------------------------
        # 2.2. Import du workflow
        # ---------------------------------------------------------------------
        # Comme pour les autres endpoints, on importe le workflow au moment de
        # l'appel.
        #
        # Cela evite de charger la configuration Groq au demarrage de FastAPI.
        from app.graph.workflow import incident_workflow

        # ---------------------------------------------------------------------
        # 2.3. Execution progressive du graphe avec graph.stream()
        # ---------------------------------------------------------------------
        # `graph.stream(initial_state)` execute le graphe et renvoie des events
        # au fur et a mesure.
        #
        # Avec `invoke()`, on attendrait la fin pour obtenir un seul State final.
        #
        # Avec `stream()`, on peut parcourir les events dans une boucle `for`.
        #
        # Chaque `chunk` represente une information intermediaire produite par
        # LangGraph pendant l'execution.
        for chunk in incident_workflow.stream(initial_state):
            # -----------------------------------------------------------------
            # 2.4. Envoi de chaque event au client
            # -----------------------------------------------------------------
            # Le chunk peut contenir des dictionnaires imbriques.
            #
            # On l'emballe dans un objet avec :
            # - `event`: le type pedagogique de l'event ;
            # - `data`: le contenu brut renvoye par LangGraph.
            #
            # `default=str` aide `json.dumps` si un objet n'est pas directement
            # serialisable en JSON.
            yield json.dumps(
                {
                    "event": "graph_event",
                    "data": chunk,
                },
                default=str,
            ) + "\n"

        # ---------------------------------------------------------------------
        # 2.5. Dernier event : fin
        # ---------------------------------------------------------------------
        # Quand la boucle `for` est terminee, cela signifie que LangGraph a fini
        # d'executer le workflow.
        #
        # On envoie un dernier event pour que le client sache que le flux est
        # termine.
        yield json.dumps(
            {
                "event": "end",
                "message": "Streaming termine.",
            }
        ) + "\n"

    # -------------------------------------------------------------------------
    # 3. Retour de la StreamingResponse
    # -------------------------------------------------------------------------
    # `StreamingResponse` prend le generateur et envoie chaque `yield` au client.
    #
    # `media_type="application/x-ndjson"` indique que la reponse est composee de
    # plusieurs lignes JSON independantes.
    #
    # Ce format est pratique pour apprendre le streaming :
    # - il reste lisible dans un terminal ;
    # - chaque ligne est un objet JSON complet ;
    # - le client peut traiter les lignes une par une.
    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
    )
