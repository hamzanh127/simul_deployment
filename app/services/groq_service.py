"""
Service Groq pour l'analyse d'incidents.

Ce fichier introduit le premier service IA du projet.

Important :
- Ce fichier ne cree pas de workflow LangGraph.
- Ce fichier ne cree pas d'endpoint FastAPI.
- Ce fichier ne modifie pas encore le node existant.
- Ce fichier isole uniquement la communication avec Groq.

-------------------------------------------------------------------------------
Qu'est-ce que Groq ?
-------------------------------------------------------------------------------

Groq est une plateforme qui permet d'executer des modeles de langage, souvent
avec une latence tres faible.

Dans ce projet, Groq jouera le role de fournisseur LLM :
- l'application prepare un prompt ;
- l'application envoie ce prompt a un modele via Groq ;
- Groq retourne une reponse generee par le modele ;
- l'application utilise cette reponse dans son workflow.

Groq n'est pas le workflow.
Groq n'est pas FastAPI.
Groq est le fournisseur qui execute le modele de langage.

-------------------------------------------------------------------------------
Qu'est-ce que ChatGroq ?
-------------------------------------------------------------------------------

`ChatGroq` est une classe fournie par la bibliotheque `langchain-groq`.

Elle sert d'adaptateur entre LangChain et Groq.

Au lieu d'appeler directement l'API HTTP de Groq nous-memes, on utilise
`ChatGroq` pour obtenir une interface plus simple et plus coherente avec
l'ecosysteme LangChain.

Concretement, `ChatGroq` permet de :
- choisir un modele Groq ;
- fournir une cle API ;
- envoyer un prompt au modele ;
- recevoir une reponse sous forme d'objet LangChain.

-------------------------------------------------------------------------------
Pourquoi separer le service IA du workflow ?
-------------------------------------------------------------------------------

Le workflow LangGraph doit decrire l'orchestration :
- quel node commence ;
- quel node vient ensuite ;
- quand le graphe se termine ;
- quelles donnees circulent dans le State.

Le service IA doit decrire la communication avec le modele :
- quel fournisseur est utilise ;
- quel modele est appele ;
- quel prompt est envoye ;
- comment on recupere la reponse.

Separer les deux apporte plusieurs avantages :
- le workflow reste lisible ;
- le code d'appel au LLM est centralise ;
- il devient plus facile de remplacer Groq par un autre fournisseur ;
- les tests sont plus simples, car on peut mocker le service IA ;
- le prompt peut evoluer sans modifier la structure du graphe ;
- la responsabilite de chaque fichier reste claire.

En architecture logicielle, cette separation aide a eviter qu'un node LangGraph
devienne un gros bloc melangeant orchestration, prompt, configuration, appel
reseau et traitement de reponse.

-------------------------------------------------------------------------------
Notes de Prompt Engineering
-------------------------------------------------------------------------------

Le Prompt Engineering consiste a formuler clairement les instructions donnees
au modele.

Un bon prompt precise generalement :
- le role que le modele doit jouer ;
- le contexte de la tache ;
- les donnees disponibles ;
- le format de sortie attendu ;
- les limites a respecter ;
- le niveau de detail souhaite.

Dans ce service, le prompt est volontairement tres detaille pour rendre le
comportement du modele plus previsible.
"""

from langchain_groq import ChatGroq

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.graph.state import IncidentState


def analyze_with_groq(state: IncidentState) -> str:
    """
    Analyse un incident avec un modele Groq.

    Parametre :
        state:
            Le State courant du graphe LangGraph.

            Pour l'instant, on s'interesse surtout aux champs d'entree :
            - title ;
            - description ;
            - severity ;
            - source.

            Exemple :

            {
              "title": "Erreur 500 sur l'API",
              "description": "La creation de compte retourne une erreur serveur.",
              "severity": "critical",
              "source": "monitoring"
            }

    Retour :
        Une chaine de caracteres contenant l'analyse generee par le LLM.

    Pourquoi retourner une chaine et pas directement le State ?
        Ce service est responsable de l'appel IA, pas de la mise a jour du
        State LangGraph.

        Plus tard, un node pourra appeler ce service puis retourner :

        {
            "analysis": analyse
        }

        Cela garde une separation claire :
        - le service produit l'analyse ;
        - le node adapte cette analyse au State ;
        - le workflow orchestre les nodes.
    """

    # -------------------------------------------------------------------------
    # 1. Lecture prudente des donnees du State
    # -------------------------------------------------------------------------
    # `IncidentState` est un `TypedDict` avec `total=False`.
    # Cela signifie que certaines cles peuvent etre absentes a certains moments
    # du workflow.
    #
    # On utilise donc `.get(...)` au lieu de `state["title"]`.
    #
    # Difference :
    # - `state["title"]` provoque une erreur si la cle n'existe pas ;
    # - `state.get("title", "...")` retourne une valeur par defaut.
    #
    # Cette approche rend le service plus robuste pendant les etapes
    # pedagogiques, ou le State peut encore evoluer.
    # `incident` est un texte libre optionnel.
    #
    # Il est notamment utilise par le endpoint `/event`, qui transforme un
    # webhook GitHub en phrase comprehensible avant d'appeler LangGraph.
    incident = state.get("incident", "Incident non fourni")
    title = state.get("title", "Titre non fourni")
    description = state.get("description", "Description non fournie")
    severity = state.get("severity", "Gravite non fournie")
    source = state.get("source", "Source non fournie")

    # -------------------------------------------------------------------------
    # 2. Creation du client ChatGroq
    # -------------------------------------------------------------------------
    # `ChatGroq` represente le modele de chat que nous allons appeler.
    #
    # `model=GROQ_MODEL`
    # - le nom du modele vient de `app/config.py` ;
    # - `app/config.py` lit cette valeur depuis `.env` ;
    # - cela permet de changer de modele sans modifier le code.
    #
    # `api_key=GROQ_API_KEY`
    # - la cle API vient aussi de `.env` ;
    # - elle ne doit jamais etre ecrite directement dans le code ;
    # - cela evite de l'exposer dans Git.
    #
    # `temperature=0`
    # - une temperature basse rend les reponses plus stables ;
    # - c'est utile pour un TP et pour des analyses operationnelles ;
    # - plus la temperature est haute, plus le modele peut etre creatif.
    llm = ChatGroq(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0,
    )

    # -------------------------------------------------------------------------
    # 3. Construction du prompt
    # -------------------------------------------------------------------------
    # Le prompt est le texte envoye au LLM.
    #
    # Ici, on ne se contente pas d'envoyer la description brute de l'incident.
    # On donne un cadre clair au modele :
    # - son role ;
    # - son objectif ;
    # - les donnees disponibles ;
    # - les consignes d'analyse ;
    # - le format de sortie attendu ;
    # - les limites a respecter.
    #
    # C'est une pratique importante de Prompt Engineering :
    # plus les attentes sont explicites, plus la reponse a de chances d'etre
    # utile, structuree et stable.
    prompt = f"""
Tu es un assistant specialise dans l'analyse d'incidents informatiques.

Ton objectif est d'aider une equipe technique a comprendre rapidement un
incident signale, sans inventer d'informations absentes.

Contexte de l'incident :
- Texte brut de l'incident ou evenement : {incident}
- Titre : {title}
- Description : {description}
- Gravite declaree : {severity}
- Source du signalement : {source}

Consignes d'analyse :
1. Reformule l'incident en une phrase claire.
2. Identifie l'impact potentiel pour les utilisateurs ou le systeme.
3. Propose une hypothese technique plausible, mais indique clairement qu'il
   s'agit d'une hypothese si les donnees sont insuffisantes.
4. Liste les premieres verifications recommandees.
5. Signale les informations manquantes qui seraient utiles pour diagnostiquer
   correctement l'incident.

Contraintes importantes :
- Ne pretend pas connaitre des logs, metriques ou causes qui ne sont pas fournis.
- Ne donne pas de conclusion definitive si les informations sont insuffisantes.
- Reste concis, structure et operationnel.
- Reponds en francais.

Format de reponse attendu :

Resume :
<resume court de l'incident>

Impact potentiel :
<impact probable>

Hypothese :
<hypothese prudente>

Verifications recommandees :
- <verification 1>
- <verification 2>
- <verification 3>

Informations manquantes :
- <information manquante 1>
- <information manquante 2>
""".strip()

    # -------------------------------------------------------------------------
    # 4. Envoi du prompt au modele
    # -------------------------------------------------------------------------
    # `.invoke(prompt)` envoie le prompt au modele et attend une reponse.
    #
    # Dans un vrai environnement, cette ligne declenche un appel reseau vers
    # Groq. Elle a donc besoin :
    # - d'une connexion internet ;
    # - d'une cle API valide ;
    # - d'un modele disponible.
    response = llm.invoke(prompt)

    # -------------------------------------------------------------------------
    # 5. Extraction du texte de la reponse
    # -------------------------------------------------------------------------
    # LangChain retourne un objet message, pas seulement une chaine brute.
    #
    # Le texte genere par le modele se trouve generalement dans `response.content`.
    # On le convertit explicitement en `str` pour garantir que la fonction
    # retourne bien une chaine de caracteres.
    return str(response.content)
