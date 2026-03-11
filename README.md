# UNIGOM — Backend Biométrique

API FastAPI du Système Institutionnel de Présence Biométrique de l'Université de Goma.

## Stack

| Composant        | Technologie          |
|------------------|----------------------|
| Framework        | FastAPI 0.115        |
| Base de données  | PostgreSQL 16        |
| ORM              | SQLAlchemy 2.0       |
| Authentification | JWT (python-jose)    |
| Hachage          | bcrypt (passlib)     |
| Scheduler        | APScheduler 3.10     |
| Fuseau horaire   | Africa/Kinshasa UTC+2|
| Terminal         | Hikvision ISAPI (polling) + EHome/ISUP push |

## Démarrage rapide (développement)

```bash
# 1. Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# 4. Démarrer PostgreSQL (Docker)
docker run -d --name unigom_pg \
  -e POSTGRES_DB=unigom_bio \
  -e POSTGRES_USER=unigom \
  -e POSTGRES_PASSWORD=unigom_secret_pass \
  -p 5432:5432 postgres:16-alpine

# 5. Initialiser la base de données
python init_db.py

# 6. Lancer l'API (mode DEBUG)
DEBUG=true uvicorn app.main:app --reload --port 8000
```

Swagger UI (mode DEBUG) : http://localhost:8000/api/docs

## Production (Docker Compose)

```bash
cp .env.example .env
# Éditer .env — surtout JWT_SECRET_KEY et DB_PASSWORD

docker compose up -d --build
docker compose exec api python init_db.py
```

## Règles métier

## Intégration terminaux

Le backend supporte deux modes d'interrogation du terminal Hikvision :

1. **Polling ISAPI** : la fonction /api/v1/attendance/sync (et le scheduler)
   récupèrent périodiquement les événements via l'endpoint `/ISAPI/AccessControl/AcsEvent`.
2. **EHome/ISUP push** : les terminaux peuvent être configurés en `ISUP5.0` pour
   ouvrir une connexion TCP persistante sur le port configuré (par défaut
   7660).  Les événements d'empreinte sont alors **poussés** vers le backend
   en temps réel et insérés immédiatement dans la base de données.

Le système reste entièrement compatible avec le polling : tous les événements
poussés mettent également à jour le curseur de synchronisation pour que le
mode manuel / cron fonctionne en second plan.


| Heure d'arrivée | Statut   |
|-----------------|----------|
| ≤ 08:00         | PRESENT  |
| 08:01 – 08:19   | LATE     |
| ≥ 08:20         | REFUSED  |
| (aucune entrée) | ABSENT   |

- **08:21** : le scheduler marque automatiquement ABSENT tout employé sans enregistrement.
- **Départ** : ignoré si < 16:00, validé si ≥ 16:00.
- Un seul enregistrement par employé par jour.

## Sécurité

- Mots de passe hachés avec bcrypt (12 rounds).
- JWT signé HS256, expiration 24 h.
- Verrouillage de compte après 5 tentatives échouées (15 min).
- Rate-limiting Nginx : 30 req/s général, 5 req/min pour /auth/token.
- CORS restreint aux origines configurées.

## Migrations (Alembic)

```bash
# Créer une migration
alembic revision --autogenerate -m "description"

# Appliquer
alembic upgrade head

# Rollback
alembic downgrade -1
```
