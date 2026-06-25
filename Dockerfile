# -----------------------------------------------------------------------------
# Dockerfile du projet tp_langgraph_deployment
# -----------------------------------------------------------------------------
# Un Dockerfile est une recette de construction.
#
# Il explique a Docker comment fabriquer une image Docker de l'application.
#
# Une image Docker est comme un paquet autonome qui contient :
# - le systeme de base minimal ;
# - Python ;
# - les dependances du projet ;
# - le code de l'application ;
# - la commande de demarrage.
#
# Cette image pourra ensuite etre lancee sous forme de container.


# -----------------------------------------------------------------------------
# 1. Image de base
# -----------------------------------------------------------------------------
# `FROM` indique l'image de depart.
#
# Ici, on utilise une image officielle Python basee sur Debian slim.
#
# Pourquoi `python:3.12-slim` ?
# - Python 3.12 est une version moderne de Python ;
# - `slim` est plus leger qu'une image complete ;
# - une image plus petite se telecharge et se deploie plus vite.
FROM python:3.12-slim


# -----------------------------------------------------------------------------
# 2. Variables d'environnement Python
# -----------------------------------------------------------------------------
# `PYTHONDONTWRITEBYTECODE=1`
# Evite que Python cree des fichiers `.pyc`.
# Dans un container, ces fichiers de cache sont rarement utiles.
#
# `PYTHONUNBUFFERED=1`
# Force Python a afficher les logs immediatement.
# C'est important en Docker, car on lit souvent les logs avec :
#
#     docker logs <container>
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# -----------------------------------------------------------------------------
# 3. Dossier de travail
# -----------------------------------------------------------------------------
# `WORKDIR /app` signifie :
# "A partir de maintenant, les commandes seront executees dans /app."
#
# Si le dossier n'existe pas, Docker le cree.
WORKDIR /app


# -----------------------------------------------------------------------------
# 4. Installation des dependances
# -----------------------------------------------------------------------------
# On copie d'abord uniquement `requirements.txt`.
#
# Pourquoi ne pas copier tout le projet directement ?
# Docker utilise un systeme de cache.
#
# Si `requirements.txt` ne change pas, Docker peut reutiliser la couche qui
# installe les dependances. Les builds suivants deviennent plus rapides.
COPY requirements.txt .

# `pip install --no-cache-dir -r requirements.txt`
# installe toutes les bibliotheques Python declarees dans requirements.txt.
#
# `--no-cache-dir` evite de garder le cache pip dans l'image finale.
# Cela reduit la taille de l'image.
RUN pip install --no-cache-dir -r requirements.txt


# -----------------------------------------------------------------------------
# 5. Copie du code applicatif
# -----------------------------------------------------------------------------
# On copie maintenant le code applicatif dans le container.
#
# On ne fait pas `COPY . .` afin d'eviter d'embarquer accidentellement des
# fichiers locaux sensibles dans l'image, par exemple `.env`.
#
# Le fichier `.env` doit etre fourni au container au moment de l'execution,
# via Docker Compose, et non copie dans l'image.
COPY app ./app


# -----------------------------------------------------------------------------
# 6. Port expose
# -----------------------------------------------------------------------------
# `EXPOSE 8000` documente le port utilise par l'application.
#
# Attention :
# Cette instruction n'ouvre pas le port toute seule.
# Elle indique simplement que l'application ecoute sur le port 8000.
#
# Le mapping reel se fait avec Docker Compose ou `docker run -p`.
EXPOSE 8000


# -----------------------------------------------------------------------------
# 7. Commande de demarrage
# -----------------------------------------------------------------------------
# `CMD` indique la commande executee quand le container demarre.
#
# Ici, on lance Uvicorn, le serveur ASGI utilise par FastAPI.
#
# `app.main:app` signifie :
# - fichier Python : app/main.py ;
# - variable FastAPI : app.
#
# `--host 0.0.0.0`
# Indispensable dans Docker : l'application doit ecouter sur toutes les
# interfaces reseau du container, sinon elle ne sera pas accessible depuis
# l'exterieur.
#
# `--port 8000`
# Le serveur ecoute sur le port 8000 dans le container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
