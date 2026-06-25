# tp_langgraph_deployment

Projet pedagogique pour apprendre a organiser, developper puis deployer une
application Python utilisant potentiellement LangGraph.

Ce depot avance progressivement comme support pedagogique. Un workflow
LangGraph minimal existe maintenant, ainsi qu'un service Groq isole. L'API
expose maintenant une route de verification `GET /`, un mode temps reel
`POST /realtime`, un mode batch `POST /batch` et un mode event-driven
`POST /event`, ainsi qu'un mode streaming `POST /streaming`.

## Structure du projet

```text
tp_langgraph_deployment/
|-- app/
|   |-- api/
|   |-- graph/
|   |   |-- nodes.py
|   |   |-- state.py
|   |   `-- workflow.py
|   |-- schemas/
|   |-- services/
|   |   `-- groq_service.py
|   |-- utils/
|   |-- main.py
|   `-- config.py
|-- tests/
|-- docs/
|-- .env.example
|-- requirements.txt
|-- README.md
|-- Dockerfile
|-- docker-compose.yml
`-- .gitignore
```

## Installation

Les commandes suivantes permettent de preparer un environnement Python local.

```bash
# 1. Se placer dans le dossier du projet.
cd tp_langgraph_deployment

# 2. Creer un environnement virtuel Python.
python -m venv .venv

# 3. Activer l'environnement virtuel.
# Sur Windows PowerShell :
.venv\Scripts\Activate.ps1

# Sur macOS ou Linux :
source .venv/bin/activate

# 4. Installer les dependances du projet.
pip install -r requirements.txt
```

## Lancer l'API

```bash
uvicorn app.main:app --reload
```

Une fois le serveur lance :
- l'API est disponible sur `http://localhost:8001` ;
- la route `GET /` retourne un message de verification ;
- la route `POST /realtime` lance le workflow LangGraph ;
- la route `POST /batch` lance le workflow LangGraph pour plusieurs incidents ;
- la route `POST /event` simule un declenchement automatique par evenement ;
- la route `POST /streaming` renvoie les events LangGraph progressivement ;
- Swagger est disponible sur `http://localhost:8001/docs`.

## Lancer l'interface Desktop Tkinter

Le fichier `gui.py` fournit une interface graphique pour tester l'agent sans
modifier l'API FastAPI.

Commande :

```bash
python gui.py
```

L'interface permet de tester :
- `POST /realtime` ;
- `POST /batch` ;
- `POST /event` ;
- `POST /streaming`.

Par defaut, le GUI appelle :

```text
http://127.0.0.1:8001
```

L'URL peut etre modifiee directement dans l'interface.

Fonctionnalites principales :
- chargement automatique d'exemples ;
- affichage du status HTTP ;
- mesure du temps de reponse ;
- resultat JSON formate ;
- copie du resultat ;
- sauvegarde en `.json` ;
- historique des 20 derniers appels ;
- logs de connexion, erreurs et reponses ;
- verification automatique de l'API toutes les 5 secondes ;
- visualisation de `langgraph_workflow.png` si l'image existe.

## Test Streaming Massif

Le fichier `streaming_mass_test.py` simule un flux continu d'incidents vers
l'endpoint `POST /streaming`.

Objectif :
- envoyer automatiquement un incident toutes les 3 secondes ;
- simuler un flux MLOps / DevOps continu ;
- lire les events streaming renvoyes par LangGraph ;
- afficher le status HTTP, l'heure d'envoi et la reponse JSON formatee ;
- arreter proprement le test avec `Ctrl + C`.

### 1. Lancer l'API

Le script utilise par defaut :

```text
http://127.0.0.1:8001/streaming
```

Lancer donc l'API sur le port 8001 :

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 2. Lancer le script de test massif

Dans un autre terminal :

```bash
python streaming_mass_test.py
```

Le script envoie des payloads au format :

```json
{
  "text": "Le deploiement Kubernetes echoue."
}
```

Important :
Le endpoint `POST /streaming` accepte maintenant ce format simple avec le champ
`text`. Le script transforme chaque incident en body JSON de ce type avant de
l'envoyer a l'API.

Frequence d'envoi :

```text
1 incident toutes les 3 secondes
```

Exemples d'incidents envoyes :
- PostgreSQL indisponible ;
- erreur HTTP 500 ;
- deploiement Kubernetes en echec ;
- latence elevee du modele d'inference ;
- derive de donnees ;
- Redis indisponible ;
- pipeline CI/CD en erreur.

### 3. Arreter le test

Le script tourne en boucle infinie.

Pour l'arreter proprement :

```text
Ctrl + C
```

Le script intercepte l'arret clavier et affiche un message de fin propre.

## Benchmark des modes de deploiement et de test

Ce tableau compare les principales manieres de lancer, tester ou demontrer le
projet. Il ne mesure pas seulement la performance brute : il sert surtout de
benchmark pedagogique pour comprendre quel mode utiliser selon le besoin.

| Mode | Commande / outil | Usage principal | Avantages | Limites | Cas MLOps typique |
| --- | --- | --- | --- | --- | --- |
| Local Uvicorn | `uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload` | Developpement rapide de l'API | Simple, rapide, logs directs, reload automatique | Depend de l'environnement local | Tester vite un changement de node, schema ou endpoint |
| Swagger | `http://localhost:8001/docs` | Test manuel des endpoints | Interface automatique, aucun outil externe, tres lisible pour une demo | Pas ideal pour les tests repetes ou automatises | Demonstration pedagogique des contrats API |
| Postman | Application Postman | Test manuel avance | Collections, historique, headers, environnements | Necessite un outil externe | Validation fonctionnelle avant livraison |
| Real-Time | `POST /realtime` | Analyse immediate d'un seul incident | Reponse directe, simple a comprendre, ideal pour tester un cas precis | Traite un seul incident par appel | Analyser rapidement une alerte ou un incident utilisateur |
| Batch | `POST /batch` | Analyse de plusieurs incidents en une requete | Reduit le nombre d'appels API, pratique pour traiter une liste | Chaque incident reste traite sequentiellement dans ce TP | Analyser un lot d'alertes ou un export de tickets |
| GUI Tkinter | `python gui.py` | Demo graphique de l'agent | Interface claire, historique, logs, resultats formates | Depend de l'API deja lancee | Presenter l'agent a un utilisateur non technique |
| Streaming massif | `python streaming_mass_test.py` | Simulation d'un flux continu | Envoi automatique toutes les 3 secondes, test periodique, utile pour observer le comportement | Boucle simple, pas de parallelisme, pas de stockage long terme | Simuler des incidents de monitoring en continu |
| Docker Build | `docker build -t tp_langgraph_deployment .` | Construction d'une image deployable | Image reproductible, portable, versionnable | Ne lance pas plusieurs services tout seul | Preparer une image pour CI/CD ou registry |
| Docker Compose | `docker compose up --build` | Lancement containerise de l'API | Commande unique, charge `.env`, expose le port, proche du deploiement | Necessite Docker et un fichier `.env` valide | Lancer l'agent dans un environnement controle |
| Event-Driven | `POST /event` via webhook | Declenchement automatique | Reagit a GitHub ou a un systeme externe, proche production | Necessite un emetteur d'evenements | Analyser automatiquement un push, une alerte ou un signal monitoring |

### Lecture rapide du benchmark

Pour developper rapidement, utiliser le mode local avec Uvicorn.

Pour expliquer l'API, utiliser Swagger.

Pour analyser un seul incident precis, utiliser le mode Real-Time.

Pour analyser plusieurs incidents dans une seule requete, utiliser le mode Batch.

Pour faire une demonstration visuelle, utiliser le GUI Tkinter.

Pour simuler un flux continu d'incidents, utiliser le test streaming massif.

Pour preparer un deploiement reproductible, utiliser Docker puis Docker Compose.

Pour se rapprocher d'un fonctionnement MLOps de production, utiliser le mode
event-driven avec un webhook.

## Deploiement avec Docker

Le projet est pret a etre lance dans un container Docker.

### Container

Un container est un environnement d'execution isole. Il contient l'application
et tout ce dont elle a besoin pour demarrer de la meme facon sur plusieurs
machines.

Sans container, l'application depend beaucoup de la machine locale :
- version de Python installee ;
- dependances deja presentes ;
- variables d'environnement ;
- configuration systeme ;
- differences entre Windows, macOS et Linux.

Avec un container, on reduit ces differences. L'application tourne dans un
environnement plus previsible.

### Image Docker

Une image Docker est le modele utilise pour creer un container.

On peut voir la difference ainsi :
- image Docker : recette deja construite, immuable ;
- container : instance en cours d'execution de cette image.

Dans ce projet, l'image contient :
- Python 3.12 ;
- les dependances de `requirements.txt` ;
- le code du dossier `app/` ;
- la commande Uvicorn qui lance FastAPI.

Le fichier `.env` n'est pas copie dans l'image. C'est volontaire : une image
Docker ne doit pas contenir de secrets. Les variables sensibles sont fournies au
container au moment du lancement avec Docker Compose.

### Docker Build

Le Docker Build est l'etape qui fabrique l'image Docker a partir du
`Dockerfile`.

Commande :

```bash
docker build -t tp_langgraph_deployment .
```

Explication :
- `docker build` construit une image ;
- `-t tp_langgraph_deployment` donne un nom a l'image ;
- `.` indique que le Dockerfile et le projet sont dans le dossier courant.

### Docker Compose

Docker Compose permet de decrire et lancer les services du projet avec un seul
fichier : `docker-compose.yml`.

Dans ce TP, Docker Compose lance un service :
- `api`, l'application FastAPI.

Commande de lancement :

```bash
docker compose up --build
```

Explication :
- `docker compose up` demarre les services ;
- `--build` reconstruit l'image si necessaire.

Commande pour lancer en arriere-plan :

```bash
docker compose up --build -d
```

Commande pour voir les logs :

```bash
docker compose logs -f api
```

Commande pour arreter :

```bash
docker compose down
```

### Pourquoi Docker est utilise en MLOps

Docker est tres utilise en MLOps parce qu'un projet IA doit souvent passer par
plusieurs environnements :
- machine du developpeur ;
- environnement de test ;
- serveur de staging ;
- production ;
- plateforme cloud.

Docker aide a garder le meme environnement d'execution partout.

En MLOps, cela apporte plusieurs avantages :
- reproductibilite : le meme code tourne avec les memes dependances ;
- portabilite : l'application peut etre lancee sur differents serveurs ;
- isolation : les dependances du projet ne polluent pas la machine ;
- deploiement plus simple : on deploie une image plutot qu'une suite de fichiers ;
- rollback plus facile : on peut revenir a une image precedente ;
- integration CI/CD : une pipeline peut construire, tester et publier l'image.

Pour une application LangGraph ou LLM, Docker est particulierement utile car le
projet depend souvent de bibliotheques, variables d'environnement, services
externes et configurations reseau.

## Lancer le projet avec Docker

### 1. Preparer le fichier `.env`

Copier le modele :

```bash
cp .env.example .env
```

Sur Windows PowerShell :

```powershell
Copy-Item .env.example .env
```

Modifier ensuite `.env` :

```env
GROQ_API_KEY=your_real_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

### 2. Construire et lancer avec Docker Compose

```bash
docker compose up --build
```

Quand le serveur est pret, ouvrir :

```text
http://localhost:8001
```

La route d'accueil doit retourner :

```json
{
  "message": "API tp_langgraph_deployment active"
}
```

### 3. Tester avec Swagger

Swagger est disponible ici :

```text
http://localhost:8001/docs
```

Pour tester avec Swagger :
1. ouvrir `/docs` dans le navigateur ;
2. choisir un endpoint, par exemple `POST /realtime` ;
3. cliquer sur `Try it out` ;
4. coller un JSON de test ;
5. cliquer sur `Execute` ;
6. lire la reponse retournee par l'API.

Exemple pour `POST /realtime` :

```json
{
  "title": "Erreur 500 sur l'API",
  "description": "La creation de compte retourne une erreur serveur.",
  "severity": "critical",
  "source": "monitoring"
}
```

### 4. Tester avec Postman

Postman permet d'envoyer des requetes HTTP manuellement.

Pour tester `POST /realtime` :
1. ouvrir Postman ;
2. choisir la methode `POST` ;
3. saisir l'URL `http://localhost:8001/realtime` ;
4. aller dans l'onglet `Body` ;
5. choisir `raw` ;
6. choisir `JSON` ;
7. coller le JSON de test ;
8. cliquer sur `Send`.

Exemple de body JSON :

```json
{
  "title": "Erreur 500 sur l'API",
  "description": "La creation de compte retourne une erreur serveur.",
  "severity": "critical",
  "source": "monitoring"
}
```

Pour tester `POST /batch`, utiliser l'URL :

```text
http://localhost:8001/batch
```

Pour tester `POST /event`, utiliser l'URL :

```text
http://localhost:8001/event
```

Pour tester `POST /streaming`, utiliser l'URL :

```text
http://localhost:8001/streaming
```

Remarque :
Les endpoints qui appellent LangGraph appellent aussi Groq via le service IA.
Ils necessitent donc une cle `GROQ_API_KEY` valide dans `.env`.

## Endpoint temps reel

Le endpoint `POST /realtime` recoit un incident en JSON, le transforme en State
initial, puis appelle le workflow LangGraph avec `graph.invoke()`.

Exemple de requete :

```json
{
  "title": "Erreur 500 sur l'API",
  "description": "La creation de compte retourne une erreur serveur.",
  "severity": "critical",
  "source": "monitoring"
}
```

Exemple de reponse :

```json
{
  "analysis": "Resume : ..."
}
```

Le endpoint est defini dans `app/api/routes.py`. Il utilise `IncidentRequest`
pour valider la request et retourne une response JSON simple contenant
l'analyse produite par le graphe.

## Endpoint batch

Le endpoint `POST /batch` recoit plusieurs incidents dans une seule request.

Exemple de requete :

```json
{
  "items": [
    {
      "title": "Erreur 500 sur l'API",
      "description": "La creation de compte retourne une erreur serveur.",
      "severity": "critical",
      "source": "monitoring"
    },
    {
      "title": "Application lente",
      "description": "Les pages mettent plus de 10 secondes a charger.",
      "severity": "medium",
      "source": "support"
    }
  ]
}
```

Exemple de reponse :

```json
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
```

### Difference avec le mode Real-Time

`POST /realtime` traite un seul incident et retourne une seule analyse. C'est
utile quand un incident vient d'arriver et que le client attend une reponse
immediate.

`POST /batch` traite plusieurs incidents dans une seule request et retourne une
liste de resultats. C'est utile quand le client possede deja plusieurs incidents
a analyser.

### Pourquoi une boucle ?

Le workflow LangGraph actuel sait analyser un incident a la fois. Le batch
utilise donc une boucle Python pour prendre chaque incident de la liste,
construire un State initial, appeler le graphe, puis stocker le resultat.

### Pourquoi appeler `graph.invoke()` plusieurs fois ?

Chaque appel a `graph.invoke()` correspond a une execution independante du
workflow. En batch, chaque incident doit garder son propre State pour eviter de
melanger les donnees et les analyses.

## Endpoint event-driven GitHub

Le endpoint `POST /event` illustre un vrai mode event-driven base sur webhook.
Il peut recevoir un payload GitHub, par exemple apres un push, transformer cet
evenement technique en texte d'incident, puis declencher LangGraph.

Exemple de requete :

```json
{
  "ref": "refs/heads/main",
  "repository": {
    "name": "tp_langgraph_deployment"
  },
  "head_commit": {
    "message": "fix: update deployment workflow"
  }
}
```

Exemple de reponse :

```json
{
  "mode": "event-driven",
  "source": "github-webhook",
  "event_received": true,
  "input_event": "Webhook GitHub recu. Repository: tp_langgraph_deployment. Branche: refs/heads/main. Commit: fix: update deployment workflow.",
  "result": "Resume : ..."
}
```

Le endpoint accepte aussi un webhook generique avec un champ `text` :

```json
{
  "text": "Le pipeline CI a echoue sur la branche main."
}
```

### Webhook

Un webhook est un appel HTTP envoye automatiquement par un systeme externe vers
notre API. Par exemple, GitHub peut appeler `POST /event` quand un commit est
pousse sur une branche.

### Evenement

Un evenement est un message indiquant qu'une chose vient de se produire :
erreur 500, latence anormale, taux d'erreur eleve, derive de donnees ou baisse
de performance d'un modele.

### Monitoring

Le monitoring observe le systeme en continu. En MLOps, il peut surveiller les
APIs, les modeles, les predictions, les erreurs, les temps de reponse ou la
qualite des donnees.

### Declenchement automatique

Un declenchement automatique signifie qu'un traitement demarre sans action
humaine directe. Dans ce projet, un evenement recu sur `POST /event` declenche
automatiquement `graph.invoke()`.

### Principe MLOps

En MLOps, on cherche a rendre les systemes IA observables et exploitables en
production. Le mode event-driven aide a relier :
- l'observation du systeme ;
- la detection d'un probleme ;
- l'envoi d'une alerte ;
- l'analyse automatique ;
- une future action de remediation.

Dans ce TP, `POST /event` reste simple, mais il introduit cette idee centrale :
un workflow IA peut etre declenche par un signal de production.

## Endpoint streaming

Le endpoint `POST /streaming` utilise `graph.stream()` pour renvoyer les events
du graphe progressivement.

Exemple de requete :

```json
{
  "text": "Le deploiement Kubernetes echoue."
}
```

Ce format est volontairement simple pour les tests de streaming continu.
L'endpoint lit le champ `text`, le transforme en State LangGraph sous la forme :

```json
{
  "incident": "Le deploiement Kubernetes echoue."
}
```

Puis le graphe est execute avec `graph.stream()`.

Exemple de flux de reponse :

```json
{"event": "start", "message": "Demarrage du streaming LangGraph."}
{"event": "graph_event", "data": {"analyze_incident": {"analysis": "Resume : ..."}}}
{"event": "end", "message": "Streaming termine."}
```

### Streaming

Le streaming consiste a envoyer une reponse en plusieurs morceaux. Le client
peut commencer a recevoir des informations avant la fin complete du traitement.

### Event

Dans ce contexte, un event est un morceau d'information emis pendant
l'execution du graphe. Avec LangGraph, un event peut montrer qu'un node a
produit une mise a jour du State.

### Yield

`yield` est un mot-cle Python qui permet a une fonction de produire plusieurs
valeurs successives. Dans `POST /streaming`, chaque `yield` envoie une ligne
JSON au client.

### Difference entre `invoke()` et `stream()`

`graph.invoke()` attend la fin du workflow et retourne le State final.

`graph.stream()` renvoie des events au fur et a mesure de l'execution. Il permet
de suivre la progression du graphe et de transmettre des informations
intermediaires au client.

## Bibliotheques utilisees

### `fastapi`

FastAPI servira a construire l'API HTTP du projet. C'est le framework qui
permettra plus tard de declarer des routes, recevoir des requetes et retourner
des reponses structurees.

Le fichier `app/main.py` cree maintenant l'application FastAPI principale et
declare uniquement `GET /`.

FastAPI genere aussi automatiquement une documentation Swagger accessible via
`/docs`. Swagger permet de visualiser et tester les endpoints disponibles.

### `uvicorn`

Uvicorn est le serveur ASGI qui executera l'application FastAPI. FastAPI decrit
l'application, tandis qu'Uvicorn la lance et la rend accessible via un port
HTTP, par exemple `http://localhost:8001`.

### `langgraph`

LangGraph servira a construire des workflows sous forme de graphes. Dans ce
type d'architecture, les etapes d'un raisonnement ou d'un traitement peuvent
etre modelisees avec des noeuds et des transitions.

Avant de creer un workflow, le projet definit d'abord un `State` dans
`app/graph/state.py`.

Dans LangGraph, le State est la memoire partagee du graphe. Les nodes lisent le
State courant, puis retournent les champs qu'ils veulent ajouter ou modifier.
LangGraph fusionne ces mises a jour pour faire circuler les donnees d'une etape
a l'autre.

Ce choix rend le workflow plus lisible : chaque node peut se concentrer sur une
petite transformation, tandis que le State conserve le contexte global.

### `langchain`

LangChain fournit des abstractions utiles pour construire des applications avec
des modeles de langage : prompts, messages, composants reutilisables et
integrations avec differents fournisseurs.

### `langchain-groq`

LangChain-Groq permet d'utiliser les modeles disponibles via Groq depuis les
interfaces LangChain. Cette bibliotheque fera le lien entre le code applicatif
et le fournisseur de modele.

Le fichier `app/services/groq_service.py` contient maintenant un premier service
dedie a Groq. Il separe l'appel au modele du workflow LangGraph afin que le
graphe reste responsable de l'orchestration, tandis que le service reste
responsable du prompt et de la communication avec le LLM.

### `python-dotenv`

Python-dotenv permet de charger des variables d'environnement depuis un fichier
`.env`. C'est pratique en developpement local pour separer la configuration du
code source, notamment les cles API.

## Configuration

Le projet utilise un fichier `.env` local pour stocker la configuration sensible
ou facilement modifiable.

Pour preparer ce fichier, copier le modele fourni :

```bash
cp .env.example .env
```

Sur Windows PowerShell, la commande equivalente est :

```powershell
Copy-Item .env.example .env
```

Ensuite, modifier `.env` avec vos propres valeurs :

```env
GROQ_API_KEY=your_real_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

### Pourquoi ne jamais mettre la cle API dans le code ?

Une cle API est un secret. Si elle est ecrite directement dans le code, elle
risque d'etre envoyee dans Git, partagee par erreur ou exposee dans un depot
public.

Les consequences peuvent etre serieuses :
- quelqu'un peut utiliser votre compte Groq a votre place ;
- vous pouvez consommer votre quota ou generer des couts non prevus ;
- il faut revoquer la cle exposee et en recreer une nouvelle ;
- l'historique Git peut conserver le secret meme apres suppression du fichier.

La bonne pratique consiste donc a placer les secrets dans `.env`, a ignorer ce
fichier avec `.gitignore`, et a garder uniquement `.env.example` dans le depot.
Le fichier `.env.example` montre les variables attendues, mais ne contient
jamais de vraie cle.

### `pydantic`

Pydantic servira a definir et valider des schemas de donnees. Il est souvent
utilise avec FastAPI pour decrire les entrees et sorties de l'API de maniere
claire et robuste.

Dans ce projet, Pydantic permet de decrire la structure attendue des donnees
avant d'ecrire les endpoints ou les workflows. Par exemple, le fichier
`app/schemas/incident_schema.py` definit maintenant :
- `IncidentRequest`, pour representer un incident unique ;
- `BatchRequest`, pour representer une liste d'incidents.

Ces classes aident a separer clairement la forme des donnees de la logique qui
les utilisera plus tard.

### `pytest`

Pytest servira a ecrire et executer les tests automatises. Les tests aideront a
verifier progressivement que les endpoints, services et workflows fonctionnent
comme prevu.

## Role des dossiers

### `app/`

Dossier principal du code applicatif. Tout ce qui concerne l'application Python
sera place ici afin d'eviter de melanger le code source avec la documentation,
les tests ou les fichiers d'infrastructure.

### `app/api/`

Futur emplacement des routes HTTP, endpoints et controleurs API.

Le fichier `app/api/routes.py` contient maintenant le endpoint
`POST /realtime`, qui appelle le workflow LangGraph pour un incident, et le
endpoint `POST /batch`, qui appelle le meme workflow pour plusieurs incidents.
Il contient aussi `POST /event`, qui simule un declenchement automatique par
webhook GitHub ou webhook generique. Le endpoint `POST /streaming` montre
comment renvoyer progressivement les events produits par `graph.stream()`.

Plus tard, d'autres routes pourront etre ajoutees dans des routers dedies. Un
router permet de regrouper les endpoints par domaine, par exemple les incidents.

### `app/graph/`

Futur emplacement des graphes LangGraph.

Ce dossier pourra contenir :
- la definition des noeuds ;
- la definition des transitions ;
- la compilation du graphe ;
- les workflows conversationnels ou decisionnels.

Un workflow minimal existe dans `app/graph/workflow.py`. Il contient un seul
node et sert uniquement a comprendre la mecanique de LangGraph.

Le fichier `app/graph/state.py` definit uniquement `IncidentState`, c'est-a-dire
la structure des donnees qui circuleront plus tard entre les nodes.

### `app/schemas/`

Futur emplacement des schemas de donnees.

Ces schemas serviront plus tard a definir clairement les entrees, sorties et
objets manipules par l'application. Par exemple, on pourra y placer des modeles
Pydantic.

Le fichier `app/schemas/incident_schema.py` contient les premiers schemas
pedagogiques du projet :
- `IncidentRequest` decrit un incident individuel ;
- `BatchRequest` decrit un lot d'incidents.

### `app/services/`

Futur emplacement de la logique de service.

Un service regroupe generalement une action applicative reutilisable :
appeler un modele, interroger une base de donnees, orchestrer une operation,
ou isoler une dependance externe.

Le fichier `app/services/groq_service.py` contient la fonction
`analyze_with_groq()`, qui prepare un prompt detaille et appelle un modele Groq
via `ChatGroq`.

### `app/utils/`

Futur emplacement des fonctions utilitaires.

Ce dossier doit rester reserve aux petits outils transverses et reutilisables.
Il ne doit pas devenir un fourre-tout de logique metier.

### `tests/`

Dossier reserve aux tests automatises.

Les tests permettront de verifier que l'application continue de fonctionner
lorsque le code evolue. Ils seront ajoutes progressivement.

### `docs/`

Dossier reserve a la documentation complementaire.

On pourra y ajouter des notes de cours, schemas d'architecture, explications
de deploiement ou guides de TP.

## Role des fichiers

### `app/main.py`

Point d'entree principal de l'application FastAPI.

Ce fichier cree l'objet `app = FastAPI(...)` et declare uniquement la route
`GET /`, qui sert a verifier que l'API demarre correctement. Il branche aussi
le router defini dans `app/api/routes.py`.

### `app/config.py`

Point central pour la configuration.

Il charge le fichier `.env`, recupere `GROQ_API_KEY` et `GROQ_MODEL`, puis
verifie que ces variables obligatoires sont bien presentes avant que le reste
de l'application les utilise.

### `.env.example`

Modele de fichier d'environnement.

Il montre quelles variables devront exister sans contenir de secrets reels.

### `requirements.txt`

Liste des dependances Python du projet.

Les dependances actuelles preparent le projet pour FastAPI, LangGraph,
LangChain, Groq, la configuration par variables d'environnement et les tests.

### `README.md`

Documentation principale du projet.

Ce fichier explique le but du depot, son organisation, les dependances et la
responsabilite de chaque dossier.

### `Dockerfile`

Fichier qui decrit comment construire l'image Docker de l'application.

Il installe Python, les dependances du projet, copie le code et lance Uvicorn
sur le port 8001.

Il copie uniquement le dossier `app/` afin d'eviter d'inclure accidentellement
des fichiers locaux sensibles comme `.env` dans l'image Docker.

### `docker-compose.yml`

Fichier qui permet de lancer l'application avec Docker Compose.

Il definit le service `api`, charge les variables depuis `.env`, expose le port
8001 et construit l'image a partir du Dockerfile.

### `.gitignore`

Liste des fichiers a ignorer par Git.

Il evite de versionner les fichiers locaux, caches, environnements virtuels et
secrets.

## Etat actuel

- Structure initiale creee.
- Dependances Python declarees.
- Configuration Groq ajoutee avec verification des variables obligatoires.
- Schemas Pydantic d'incident ajoutes.
- State LangGraph `IncidentState` ajoute.
- Service Groq `analyze_with_groq()` ajoute.
- Endpoint `GET /` ajoute.
- Endpoint `POST /realtime` ajoute.
- Endpoint `POST /batch` ajoute.
- Endpoint `POST /event` ajoute.
- Endpoint `POST /streaming` ajoute.
- Workflow LangGraph minimal a un node ajoute.
- Dockerfile et Docker Compose ajoutes pour le deploiement.
- Swagger disponible via `/docs` lorsque l'API est lancee.
- Beaucoup de commentaires pour guider les prochaines etapes.
