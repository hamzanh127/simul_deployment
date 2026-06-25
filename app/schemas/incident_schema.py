"""
Schemas Pydantic pour les incidents.

Un schema de donnees sert a decrire la forme attendue d'un objet.
Dans ce fichier, on ne traite pas encore les incidents et on n'appelle aucun
modele d'IA. On definit seulement les donnees qui pourront entrer plus tard
dans l'application.

Qu'est-ce que Pydantic ?

Pydantic est une bibliotheque Python qui permet de creer des modeles de donnees
avec des types explicites.

Exemple :
- `title: str` signifie que `title` doit etre une chaine de caracteres ;
- `items: list[IncidentRequest]` signifie que `items` doit etre une liste
  contenant des objets qui respectent le schema `IncidentRequest`.

Pydantic est tres utile avec FastAPI, car FastAPI peut l'utiliser pour :
- lire automatiquement le JSON envoye par un client ;
- verifier que les champs attendus existent ;
- verifier que les types sont corrects ;
- produire une documentation automatique de l'API ;
- retourner des erreurs claires quand une requete est invalide.
"""

from pydantic import BaseModel, Field


class IncidentRequest(BaseModel):
    """
    Schema representant un incident unique.

    Cette classe ne contient pas de logique metier. Elle ne decide pas comment
    analyser, classer ou resoudre un incident. Elle dit seulement :
    "voici les champs attendus pour decrire un incident".

    Exemple JSON minimal :

    {
      "title": "Application indisponible",
      "description": "Les utilisateurs ne peuvent plus acceder au portail.",
      "severity": "high",
      "source": "support"
    }

    Exemple JSON avec une severite faible :

    {
      "title": "Bouton mal aligne",
      "description": "Le bouton de validation est legerement decale sur mobile.",
      "severity": "low",
      "source": "qa"
    }

    Exemple JSON avec une source technique :

    {
      "title": "Erreur 500 sur l'API",
      "description": "Une erreur serveur apparait lors de la creation de compte.",
      "severity": "critical",
      "source": "monitoring"
    }
    """

    # Titre court de l'incident.
    #
    # `str` indique que la valeur attendue est du texte.
    # `Field(...)` permet d'ajouter des informations utiles au schema :
    # - `...` signifie que le champ est obligatoire ;
    # - `description` documente le champ ;
    # - `examples` donne des exemples lisibles dans la documentation FastAPI.
    title: str = Field(
        ...,
        description="Titre court et lisible de l'incident.",
        examples=["Application indisponible"],
    )

    # Description detaillee de l'incident.
    #
    # Ce champ contiendra plus de contexte que le titre :
    # symptomes observes, impact utilisateur, message d'erreur, moment ou le
    # probleme est apparu, etc.
    description: str = Field(
        ...,
        description="Description detaillee du probleme observe.",
        examples=["Les utilisateurs ne peuvent plus acceder au portail."],
    )

    # Niveau de gravite fourni par le client ou le systeme appelant.
    #
    # Pour l'instant, on utilise une simple chaine de caracteres afin de garder
    # le TP accessible. Plus tard, on pourra remplacer ce champ par une enum
    # pour limiter les valeurs possibles a `low`, `medium`, `high`, `critical`.
    severity: str = Field(
        ...,
        description="Niveau de gravite de l'incident.",
        examples=["low", "medium", "high", "critical"],
    )

    # Origine de l'incident.
    #
    # Ce champ aide a savoir d'ou vient l'information :
    # - ticket support ;
    # - outil de monitoring ;
    # - test QA ;
    # - retour utilisateur ;
    # - autre systeme interne.
    source: str = Field(
        ...,
        description="Source ou canal ayant signale l'incident.",
        examples=["support", "monitoring", "qa"],
    )


class BatchRequest(BaseModel):
    """
    Schema representant un lot d'incidents.

    Un batch est utile lorsqu'un client veut envoyer plusieurs incidents dans
    une seule requete au lieu d'appeler l'API une fois par incident.

    Ici encore, cette classe ne traite rien. Elle decrit uniquement la forme du
    JSON attendu.

    Exemple JSON avec deux incidents :

    {
      "items": [
        {
          "title": "Application indisponible",
          "description": "Les utilisateurs ne peuvent plus acceder au portail.",
          "severity": "high",
          "source": "support"
        },
        {
          "title": "Erreur 500 sur l'API",
          "description": "La creation de compte retourne une erreur serveur.",
          "severity": "critical",
          "source": "monitoring"
        }
      ]
    }

    Exemple JSON avec un seul incident dans le lot :

    {
      "items": [
        {
          "title": "Notification non envoyee",
          "description": "Les emails de confirmation ne partent plus.",
          "severity": "medium",
          "source": "support"
        }
      ]
    }

    Exemple JSON vide, techniquement possible selon ce schema :

    {
      "items": []
    }

    Remarque pedagogique :
    Si le projet veut interdire les lots vides, on pourra ajouter plus tard une
    validation Pydantic. Pour l'instant, on reste volontairement simple.
    """

    # Liste des incidents a traiter plus tard.
    #
    # `list[IncidentRequest]` signifie :
    # - la valeur doit etre une liste JSON ;
    # - chaque element de la liste doit respecter le schema IncidentRequest ;
    # - Pydantic verifiera chaque incident individuellement.
    items: list[IncidentRequest] = Field(
        ...,
        description="Liste des incidents envoyes dans la requete.",
        examples=[
            [
                {
                    "title": "Application indisponible",
                    "description": "Les utilisateurs ne peuvent plus acceder au portail.",
                    "severity": "high",
                    "source": "support",
                }
            ]
        ],
    )
