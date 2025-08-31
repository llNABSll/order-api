# Utilise une image officielle Python comme base
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt ./

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . .

# Exposer le port utilisé par l'API
EXPOSE 8000

# Commande de démarrage par défaut (surchargée par docker-compose)
CMD ["uvicorn", "dev.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
