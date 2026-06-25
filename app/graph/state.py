"""
Definition du State LangGraph pour le traitement d'incidents.

Important :
Ce fichier ne cree aucun workflow LangGraph.
Il ne cree aucun node.
Il ne compile aucun graphe.
Il definit uniquement la structure des donnees qui circuleront plus tard dans
un graphe.

-------------------------------------------------------------------------------
Qu'est-ce qu'un State dans LangGraph ?
-------------------------------------------------------------------------------

Dans LangGraph, un `State` est la memoire partagee d'une execution de graphe.

On peut l'imaginer comme un dictionnaire Python qui accompagne le traitement du
debut a la fin :

{
    "title": "Application indisponible",
    "description": "Les utilisateurs ne peuvent plus acceder au portail.",
    "severity": "high",
    "source": "support",
    "classification": None,
    "suggested_action": None,
    "final_answer": None
}

Chaque etape du graphe, appelee `Node`, peut lire ce State et produire une mise
a jour partielle.

-------------------------------------------------------------------------------
Pourquoi LangGraph utilise un State ?
-------------------------------------------------------------------------------

LangGraph utilise un State pour rendre le workflow explicite et controlable.

Sans State partage, chaque fonction devrait passer manuellement toutes les
donnees a la fonction suivante. Cela devient vite difficile a maintenir quand :
- le workflow contient plusieurs etapes ;
- certaines etapes ajoutent de nouvelles informations ;
- certaines etapes ne lisent qu'une partie des donnees ;
- le chemin peut changer selon une condition ;
- on veut reprendre, inspecter ou deboguer l'execution.

Le State donne donc un contrat commun a toutes les etapes du graphe.

Exemple pedagogique :

1. Un premier node lit `title`, `description`, `severity` et `source`.
2. Il ajoute une nouvelle information : `classification`.
3. Un deuxieme node lit `classification` et `description`.
4. Il ajoute une recommandation : `suggested_action`.
5. Un dernier node produit une reponse finale : `final_answer`.

Le State evolue progressivement. Il commence avec les donnees d'entree, puis il
est enrichi par les nodes.

-------------------------------------------------------------------------------
Comment les donnees circulent entre les Nodes ?
-------------------------------------------------------------------------------

Dans LangGraph, un node recoit le State courant en entree.

Exemple conceptuel, sans creer de vrai node ici :

def classify_incident(state):
    # Le node lit des informations existantes.
    description = state["description"]
    severity = state["severity"]

    # Le node retourne uniquement ce qu'il veut ajouter ou modifier.
    return {
        "classification": "incident_technique"
    }

LangGraph applique ensuite cette mise a jour au State global.

Avant le node :

{
    "description": "Erreur 500 lors de la creation de compte",
    "severity": "critical",
    "classification": None
}

Retour du node :

{
    "classification": "incident_technique"
}

Apres fusion par LangGraph :

{
    "description": "Erreur 500 lors de la creation de compte",
    "severity": "critical",
    "classification": "incident_technique"
}

Ce mecanisme est important :
- un node n'a pas besoin de retourner tout le State ;
- il peut retourner seulement les champs qu'il met a jour ;
- le graphe garde une memoire commune de l'execution ;
- chaque node reste plus simple et plus facile a tester.
"""

from typing import TypedDict


class IncidentState(TypedDict, total=False):
    """
    State partage pour un futur graphe LangGraph de traitement d'incidents.

    `TypedDict` permet de decrire la structure d'un dictionnaire Python.

    Pourquoi utiliser `TypedDict` ici ?
    - LangGraph travaille tres naturellement avec des dictionnaires de state.
    - Les annotations aident a comprendre quelles cles peuvent exister.
    - Les editeurs de code peuvent proposer de meilleures autocompletions.
    - Le projet reste simple : on definit un contrat sans ajouter de logique.

    Que signifie `total=False` ?
    - Toutes les cles ne sont pas obligatoires au meme moment.
    - Au debut du workflow, seules les donnees d'entree peuvent exister.
    - Plus tard, certains nodes ajouteront des champs supplementaires.

    Exemple de State au debut d'un futur workflow :

    {
      "title": "Application indisponible",
      "description": "Les utilisateurs ne peuvent plus acceder au portail.",
      "severity": "high",
      "source": "support"
    }

    Exemple de State apres une future etape de classification :

    {
      "title": "Application indisponible",
      "description": "Les utilisateurs ne peuvent plus acceder au portail.",
      "severity": "high",
      "source": "support",
      "classification": "indisponibilite_service"
    }

    Exemple de State apres plusieurs futures etapes :

    {
      "title": "Erreur 500 sur l'API",
      "description": "La creation de compte retourne une erreur serveur.",
      "severity": "critical",
      "source": "monitoring",
      "classification": "incident_backend",
      "suggested_action": "Verifier les logs applicatifs et la base de donnees.",
      "final_answer": "Incident critique detecte sur l'API de creation de compte."
    }

    Remarque importante :
    Cette classe ne lance rien. Elle ne definit que les noms et types des champs
    que les futurs nodes pourront lire ou enrichir.
    """

    # -------------------------------------------------------------------------
    # Donnees d'entree
    # -------------------------------------------------------------------------
    # Ces champs correspondent aux informations de base recues pour un incident.
    # Ils viennent conceptuellement du schema `IncidentRequest`, mais on ne cree
    # pas encore de lien automatique avec l'API.

    # Texte libre d'incident.
    #
    # Cette cle est utile pour les webhooks event-driven, par exemple GitHub.
    # Un webhook GitHub n'envoie pas naturellement `title`, `description`,
    # `severity` et `source`. La route `/event` transforme donc le payload GitHub
    # en un texte unique :
    #
    # {
    #   "incident": "Webhook GitHub recu. Repository: ..."
    # }
    #
    # Le node peut ensuite convertir ce texte en entree analysable par Groq.
    incident: str

    # Titre court de l'incident.
    # Exemple : "Application indisponible"
    title: str

    # Description detaillee du probleme observe.
    # Exemple : "Les utilisateurs ne peuvent plus acceder au portail."
    description: str

    # Gravite declaree ou estimee au moment de l'entree.
    # Exemple : "low", "medium", "high" ou "critical"
    severity: str

    # Source de l'incident.
    # Exemple : "support", "monitoring", "qa" ou "user_feedback"
    source: str

    # -------------------------------------------------------------------------
    # Donnees ajoutees plus tard par de futurs nodes
    # -------------------------------------------------------------------------
    # Ces champs ne sont pas encore produits par du code. Ils anticipent les
    # informations qu'un futur graphe pourrait ajouter progressivement.

    # Analyse produite par le premier node minimal `analyze_incident_node`.
    #
    # Pour l'instant, cette analyse vaut simplement "Test".
    # Plus tard, elle pourra contenir une vraie analyse generee par une logique
    # applicative ou par un modele LLM.
    analysis: str

    # Resultat d'une future etape de classification.
    # Exemple : "incident_backend", "incident_reseau", "bug_interface"
    classification: str

    # Recommandation ou prochaine action proposee par une future etape.
    # Exemple : "Verifier les logs applicatifs."
    suggested_action: str

    # Reponse finale qui pourra etre retournee a l'utilisateur ou a l'API.
    # Exemple : "Incident critique detecte, escalade recommandee."
    final_answer: str
