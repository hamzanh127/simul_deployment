"""
Workflow LangGraph minimal du projet.

Ce fichier construit un graphe avec :
- un State : `IncidentState` ;
- un seul Node : `analyze_incident_node` ;
- un Entry Point : le node par lequel le graphe commence ;
- un Edge : le lien qui indique ou aller apres le node ;
- END : le marqueur de fin du graphe ;
- compile() : l'etape qui transforme la definition du graphe en objet executable.

Important :
Ce workflow reste volontairement minimal.
Il ne fait pas encore appel a Groq.
Il ne contient pas plusieurs nodes.
Il ne contient pas de conditions.
Il ne contient pas de logique metier avancee.

L'objectif est de comprendre chaque ligne avant d'ajouter de la complexite.

-------------------------------------------------------------------------------
1. StateGraph
-------------------------------------------------------------------------------

`StateGraph` est la classe LangGraph qui sert a construire un graphe base sur
un State.

Quand on cree un `StateGraph`, on lui donne le type du State :

    StateGraph(IncidentState)

Cela signifie :
"Ce graphe va faire circuler un dictionnaire qui respecte la structure
IncidentState."

Le State est la memoire commune de l'execution. Les nodes lisent ce State et
retournent des mises a jour partielles.

-------------------------------------------------------------------------------
2. Node
-------------------------------------------------------------------------------

Un Node est une etape du graphe.

Dans ce projet, le premier node est :

    analyze_incident_node

Il recoit le State courant et retourne :

    {
        "analysis": "Test"
    }

Dans LangGraph, on ajoute un node au builder avec :

    builder.add_node("analyze_incident", analyze_incident_node)

Le premier argument est le nom du node dans le graphe.
Le deuxieme argument est la fonction Python executee par ce node.

-------------------------------------------------------------------------------
3. Edge
-------------------------------------------------------------------------------

Un Edge est une liaison entre deux points du graphe.

Il repond a la question :
"Apres cette etape, ou doit aller le workflow ?"

Dans ce workflow minimal :

    analyze_incident -> END

Cela signifie :
1. execute le node `analyze_incident` ;
2. termine le workflow.

-------------------------------------------------------------------------------
4. Entry Point
-------------------------------------------------------------------------------

L'Entry Point est le point de depart du graphe.

Quand on lance un graphe, LangGraph doit savoir quel node executer en premier.
Ici, on indique :

    builder.set_entry_point("analyze_incident")

Cela signifie :
"Quand ce graphe demarre, commence par le node analyze_incident."

-------------------------------------------------------------------------------
5. END
-------------------------------------------------------------------------------

`END` est un marqueur special fourni par LangGraph.

Il ne represente pas une fonction Python.
Il represente la fin du workflow.

Quand un edge pointe vers `END`, cela veut dire :
"Apres cette etape, il n'y a plus rien a executer."

-------------------------------------------------------------------------------
6. compile()
-------------------------------------------------------------------------------

Pendant la construction, `builder` est comme un plan du graphe.

On y ajoute :
- les nodes ;
- les edges ;
- le point d'entree ;
- les regles de circulation.

Mais ce plan n'est pas encore l'objet final que l'on execute.

La methode `compile()` transforme ce plan en graphe executable.

Apres compilation, on obtient un objet que l'on pourra plus tard appeler avec
un State initial.

-------------------------------------------------------------------------------
7. builder
-------------------------------------------------------------------------------

Dans ce fichier, la variable `builder` contient le constructeur du graphe.

Le mot "builder" signifie "constructeur".

On l'utilise etape par etape :
1. creer le StateGraph ;
2. ajouter un node ;
3. definir le point d'entree ;
4. ajouter un edge vers END ;
5. compiler le graphe.

Cette separation est pedagogique : elle permet de voir clairement chaque etape
de construction du workflow.
"""

# `END` est le marqueur de fin fourni par LangGraph.
# `StateGraph` est le constructeur utilise pour definir un graphe base sur un
# State partage.
from langgraph.graph import END, StateGraph

# `analyze_incident_node` est le seul node du workflow pour l'instant.
# Il est defini dans `nodes.py` afin de separer :
# - la definition des etapes de traitement ;
# - la construction du graphe.
from app.graph.nodes import analyze_incident_node

# `IncidentState` decrit les cles qui peuvent circuler dans le graphe.
# C'est le contrat commun entre les nodes.
from app.graph.state import IncidentState


# -----------------------------------------------------------------------------
# Creation du builder
# -----------------------------------------------------------------------------
# Ici, on cree un constructeur de graphe.
#
# `StateGraph(IncidentState)` signifie :
# "Je veux construire un graphe dont la memoire partagee respecte IncidentState."
#
# A ce stade, le graphe n'a encore :
# - aucun node ;
# - aucun edge ;
# - aucun point d'entree ;
# - aucune compilation.
builder = StateGraph(IncidentState)


# -----------------------------------------------------------------------------
# Ajout du Node
# -----------------------------------------------------------------------------
# On ajoute le node minimal au graphe.
#
# Premier argument : "analyze_incident"
# - c'est le nom interne du node dans le graphe ;
# - ce nom servira pour definir les edges ;
# - ce nom peut etre different du nom de la fonction Python.
#
# Deuxieme argument : analyze_incident_node
# - c'est la fonction Python qui sera executee ;
# - elle recoit le State courant ;
# - elle retourne un dictionnaire de mise a jour.
builder.add_node("analyze_incident", analyze_incident_node)


# -----------------------------------------------------------------------------
# Definition de l'Entry Point
# -----------------------------------------------------------------------------
# Le point d'entree indique quel node doit etre execute en premier.
#
# Ici, le workflow commence directement par le seul node existant :
# `analyze_incident`.
#
# Sans point d'entree, LangGraph ne saurait pas par ou commencer.
builder.set_entry_point("analyze_incident")


# -----------------------------------------------------------------------------
# Ajout de l'Edge vers END
# -----------------------------------------------------------------------------
# Un edge indique la direction du workflow.
#
# Ici, on dit :
# "Apres le node analyze_incident, aller vers END."
#
# Comme END represente la fin, cela signifie que le workflow s'arrete apres
# l'execution du node.
builder.add_edge("analyze_incident", END)


# -----------------------------------------------------------------------------
# Compilation du graphe
# -----------------------------------------------------------------------------
# `compile()` transforme le builder en graphe executable.
#
# Avant cette ligne :
# - `builder` est un plan de construction ;
# - on peut encore ajouter des nodes ou des edges.
#
# Apres cette ligne :
# - `incident_workflow` est le graphe pret a etre invoque plus tard ;
# - LangGraph connait l'ordre d'execution ;
# - LangGraph sait que le workflow commence par `analyze_incident` ;
# - LangGraph sait que le workflow se termine ensuite avec END.
#
# Ce fichier compile le graphe, mais ne l'execute pas.
# L'execution sera ajoutee plus tard, par exemple depuis un service ou un
# endpoint FastAPI.
incident_workflow = builder.compile()
