"""
Premier node LangGraph du projet.

Important :
Ce fichier ne cree pas de workflow.
Ce fichier ne compile pas de graphe.
Ce fichier ne configure pas directement Groq.
Ce fichier contient le node qui appelle le service IA dedie.

Il contient uniquement une fonction de node :

    analyze_incident_node()

L'objectif est pedagogique : comprendre ce qu'est un node avant de construire
un vrai workflow LangGraph.

-------------------------------------------------------------------------------
Qu'est-ce qu'un Node dans LangGraph ?
-------------------------------------------------------------------------------

Dans LangGraph, un `Node` est une etape de traitement.

On peut le voir comme une fonction Python qui represente une action precise :
- analyser un incident ;
- classifier une demande ;
- appeler un modele de langage ;
- enrichir des donnees ;
- choisir une prochaine action ;
- preparer une reponse finale.

Un workflow LangGraph est compose de plusieurs nodes relies entre eux.
Chaque node fait une petite partie du travail.

Dans ce fichier, nous creons le premier node du workflow :

    analyze_incident_node

Ce node suit maintenant le chemin suivant :

    State entrant
        -> extraction des donnees de l'incident
        -> appel du service `analyze_with_groq`
        -> retour d'un dictionnaire contenant `analysis`

Le node ne construit pas lui-meme le client Groq et ne contient pas le prompt.
Ces responsabilites restent dans `app/services/groq_service.py`.

-------------------------------------------------------------------------------
Pourquoi un Node recoit un State ?
-------------------------------------------------------------------------------

Un node recoit le `State` courant parce que le State contient la memoire de
l'execution du graphe.

Le State peut contenir les donnees deja disponibles, par exemple :

{
    "title": "Application indisponible",
    "description": "Les utilisateurs ne peuvent plus acceder au portail.",
    "severity": "high",
    "source": "support"
}

Quand LangGraph execute un node, il lui donne ce State en argument.
Le node peut alors lire les informations dont il a besoin.

Exemple conceptuel :

def example_node(state):
    title = state["title"]
    description = state["description"]
    ...

Cela permet a chaque node de travailler avec le contexte courant, sans avoir a
recevoir une longue liste de parametres separes.

-------------------------------------------------------------------------------
Pourquoi un Node retourne un dictionnaire ?
-------------------------------------------------------------------------------

Un node LangGraph retourne generalement un dictionnaire parce qu'il ne doit pas
necessairement reconstruire tout le State.

Il retourne seulement les champs qu'il veut ajouter ou modifier.

Exemple :

State avant le node :

{
    "title": "Application indisponible",
    "description": "Les utilisateurs ne peuvent plus acceder au portail."
}

Retour du node :

{
    "analysis": "<analyse generee par le service Groq>"
}

State apres fusion par LangGraph :

{
    "title": "Application indisponible",
    "description": "Les utilisateurs ne peuvent plus acceder au portail.",
    "analysis": "<analyse generee par le service Groq>"
}

Ce principe est tres important :
- le node lit le State courant ;
- le node retourne une mise a jour partielle ;
- LangGraph fusionne cette mise a jour avec le State existant ;
- le node suivant recoit le State enrichi.

Ainsi, chaque node reste petit, lisible et facile a tester.
"""

from app.graph.state import IncidentState
from app.services.groq_service import analyze_with_groq


def analyze_incident_node(state: IncidentState) -> dict[str, str]:
    """
    Node d'analyse d'incident.

    Parametre :
        state:
            Le State courant du graphe.

            Dans un futur workflow, ce State pourra contenir par exemple :

            {
              "title": "Erreur 500 sur l'API",
              "description": "La creation de compte retourne une erreur serveur.",
              "severity": "critical",
              "source": "monitoring"
            }

            Le node recoit ce State automatiquement quand LangGraph execute
            l'etape `analyze_incident`.

            Le State est la memoire courante du workflow. Il contient les
            donnees deja connues et peut etre enrichi au fur et a mesure.

    Retour :
        Un dictionnaire contenant uniquement les champs a ajouter ou modifier
        dans le State.

        Ici, le node retourne :

        {
          "analysis": "<texte produit par Groq>"
        }

    Pourquoi ne pas retourner tout le State ?
        Parce que LangGraph sait fusionner la mise a jour retournee par le node
        avec le State existant. Le node peut donc rester concentre sur ce qu'il
        produit.

    Pourquoi le node appelle un service au lieu d'ecrire tout le code ici ?
        Parce que le node doit rester une etape d'orchestration.

        Le service Groq gere :
        - le client `ChatGroq` ;
        - la configuration du modele ;
        - le prompt ;
        - l'appel au LLM ;
        - l'extraction de la reponse.

        Le node gere :
        - la lecture du State ;
        - la decision d'appeler le service ;
        - la mise a jour du State avec le resultat.
    """

    # -------------------------------------------------------------------------
    # 1. Reception du State
    # -------------------------------------------------------------------------
    # LangGraph appelle automatiquement cette fonction avec le State courant.
    #
    # Exemple de State recu :
    #
    # {
    #   "title": "Erreur 500 sur l'API",
    #   "description": "La creation de compte retourne une erreur serveur.",
    #   "severity": "critical",
    #   "source": "monitoring"
    # }
    #
    # Le node n'a pas besoin de savoir qui a cree ce State. Il sait seulement
    # qu'il recoit le contexte courant du workflow.

    # -------------------------------------------------------------------------
    # 2. Extraction des donnees de l'incident
    # -------------------------------------------------------------------------
    # Ici, "extraire incident" signifie recuperer dans le State les informations
    # qui decrivent l'incident.
    #
    # Deux formats sont acceptes :
    #
    # 1. Format API classique :
    #
    # {
    #   "title": "...",
    #   "description": "...",
    #   "severity": "...",
    #   "source": "..."
    # }
    #
    # 2. Format event-driven / webhook :
    #
    # {
    #   "incident": "Webhook GitHub recu. Repository: ..."
    # }
    #
    # Le deuxieme format est utile car un webhook GitHub ne ressemble pas a un
    # formulaire d'incident classique. La route `/event` le transforme donc en
    # texte libre, puis le graphe recoit ce texte sous la cle `incident`.
    #
    # On utilise `.get(...)` car `IncidentState` est declare avec `total=False`.
    # Certaines cles peuvent donc etre absentes si le State est incomplet.
    incident_text = state.get("incident", "").strip()

    # Si `incident_text` existe, on construit une entree compatible avec le
    # service Groq a partir de ce texte.
    #
    # Pourquoi ajouter title/severity/source ici ?
    # Le service Groq a ete concu pour recevoir un contexte structure.
    # Le webhook, lui, fournit un texte libre. Le node fait donc l'adaptation
    # entre les deux mondes :
    # - entree event-driven ;
    # - analyse IA structuree.
    if incident_text:
        incident = {
            "incident": incident_text,
            "title": "Evenement webhook",
            "description": incident_text,
            "severity": "unknown",
            "source": "webhook",
        }
    else:
        # Si aucun texte libre n'est fourni, on garde le format classique utilise
        # par `/realtime`, `/batch` et `/streaming`.
        incident = {
            "title": state.get("title", ""),
            "description": state.get("description", ""),
            "severity": state.get("severity", ""),
            "source": state.get("source", ""),
        }

    # Cette verification rend l'erreur plus comprehensible si le node est appele
    # avec un State incomplet.
    #
    # Sans cela, le service Groq recevrait des valeurs vides et produirait une
    # analyse peu utile. Ici, on echoue tot avec un message clair.
    missing_fields = [
        field_name
        for field_name, field_value in incident.items()
        if not field_value.strip()
    ]

    if missing_fields:
        raise ValueError(
            "Impossible d'analyser l'incident : champs manquants dans le State "
            f"({', '.join(missing_fields)})."
        )

    # -------------------------------------------------------------------------
    # 3. Appel du service Groq
    # -------------------------------------------------------------------------
    # Le node delegue l'analyse au service IA.
    #
    # Pourquoi passer `incident` au service ?
    # - `incident` contient les champs propres et verifies ;
    # - le service n'a pas besoin de connaitre les details du State complet ;
    # - cela montre clairement la frontiere entre orchestration et appel IA.
    #
    # Le service retourne une chaine de caracteres contenant l'analyse produite
    # par le LLM.
    analysis = analyze_with_groq(incident)

    # -------------------------------------------------------------------------
    # 4. Mise a jour du State
    # -------------------------------------------------------------------------
    # Un node LangGraph retourne un dictionnaire partiel.
    #
    # Ici, on ne retourne pas tout le State.
    # On retourne uniquement la nouvelle information produite par ce node :
    # `analysis`.
    #
    # LangGraph fusionnera automatiquement ce dictionnaire avec le State courant.
    #
    # Exemple :
    #
    # State avant :
    # {
    #   "title": "Erreur 500 sur l'API",
    #   "description": "...",
    #   "severity": "critical",
    #   "source": "monitoring"
    # }
    #
    # Retour du node :
    # {
    #   "analysis": "Resume : ..."
    # }
    #
    # State apres fusion :
    # {
    #   "title": "Erreur 500 sur l'API",
    #   "description": "...",
    #   "severity": "critical",
    #   "source": "monitoring",
    #   "analysis": "Resume : ..."
    # }
    return {
        "analysis": analysis,
    }
