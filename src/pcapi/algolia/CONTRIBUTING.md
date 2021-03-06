# Package `algolia`

- [Algolia](https://www.algolia.com) ;
- [Documentation Algolia](https://www.algolia.com/doc/api-client/getting-started/install/python/?language=python) ;
- [Documentation Redis](https://redis.io/commands) ;
- objet = document à indexer.

## api

Fonctions pour discuter avec Algolia.

## rules_engine

Fonction qui détermine si l'offre est éligible à être indexée, dans le cas contraire, on demande à la supprimer de l'index.

## builder

Fonction qui formatte l'objet à indexer.

## orchestrator

Fonction qui indexe ou supprime un objet.

## Tester

Il faut ajouter `ALGOLIA_TRIGGER_INDEXATION='1'` si vous voulez indexer votre local.
Faire ce que vous voulez sur l'application. Cela va remplir Redis.
On peut vérifier que Redis est remplie en conséquence :

```bash
docker exec -it pc-redis sh
redis-cli
LRANGE offer_ids 0 100
```

Ensuite, on lance le batch pour indexer Algolia :

```bash
pc python
```

```python
from app import app
from pcapi.scripts.algolia_indexing.indexing import batch_indexing_offers_in_algolia_by_offer
with app.app_context():
    batch_indexing_offers_in_algolia_by_offer(client=app.redis_client)
```

Deux réponses possible :

- `2019-12-18 12:36:44 INFO    [ALGOLIA] Indexing X objectsID [SQ, ...]`
- `2019-12-18 12:36:44 INFO    [ALGOLIA] Deleting X objectsID [SQ, ...]`

Si vous voulez indexer directement de la base de données vers Algolia :

```bash
pc python
```

```python
from pcapi.scripts.algolia_indexing.indexing import batch_indexing_offers_in_algolia_from_database
batch_indexing_offers_in_algolia_from_database()
```
