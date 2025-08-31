# Order API

> API de gestion de commandes (FastAPI, PostgreSQL, RabbitMQ, Docker, BDD Behave)

---

## Installer les dépendances Python

```sh
pip install -r requirements.txt
```

---

## Lancer les conteneurs (Docker Compose)

```sh
# Démarre l'API, la base de données et RabbitMQ

docker compose up -d
```

---

## Lancer l'API en local (hors Docker)

```sh
# Démarre le serveur FastAPI en mode développement

uvicorn dev.src.main:app --reload --port 8000
```

---

## Lancer les tests BDD (Behave)

```sh
# Exécute tous les tests Behave et génère les rapports JUnit

behave dev/tests/features --junit --junit-directory reports
```

---

## Accès rapides

- API docs : http://localhost:8000/docs
- RabbitMQ UI : http://localhost:15672 (guest/guest)
- PostgreSQL : localhost:5432 (user/pass selon .env)

---

## Astuces

- Pour arrêter les conteneurs :
  ```sh
  docker compose down
  ```
- Pour voir les logs :
  ```sh
  docker compose logs -f
  ```