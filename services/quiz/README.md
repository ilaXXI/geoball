# Quiz

QCM sur les capitales. Le service appelle le catalogue en REST à la création
d'une partie ; les bonnes réponses et le calcul du score restent côté serveur.

En local, il faut le catalogue sur le port 8000 et une base PostgreSQL.
Fournir `POSTGRES_PASSWORD` dans l'environnement avant de lancer le service.
Par défaut : hôte `127.0.0.1`, port `5432`, base et utilisateur `geoball`.
Ces valeurs sont configurables via `POSTGRES_HOST`, `POSTGRES_PORT`,
`POSTGRES_DB` et `POSTGRES_USER`.

Depuis la racine du dépôt :

```powershell
.\.venv\Scripts\python.exe -m pip install -r services/quiz/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services/quiz --port 8002 --reload
```

Documentation : http://127.0.0.1:8002/quizzes/docs.
`CATALOG_URL` permet de changer l'adresse du catalogue.

- `POST /quizzes` avec `{"number_of_questions": 3}` : créer une partie.
- `GET /quizzes/{id}` : retrouver les questions et le score.
- `POST /quizzes/{id}/answers` avec `question_id` et `choice` : répondre.

Une question ne peut être comptée qu'une fois. Un choix invalide renvoie 400,
une réponse répétée 409, une partie inconnue 404 et un catalogue indisponible 503.

Les parties et leurs questions sont conservées dans PostgreSQL avec SQLAlchemy.
Les réponses sont enregistrées dans une transaction ; le score est recalculé.
Les tables sont créées au premier démarrage. Ce mécanisme n'effectue pas les
migrations d'un schéma existant. Pas de comptes utilisateurs pour cette version.

## Image et tests

Image publiée : [gabriel0langlois/geoball-quiz:0.2](https://hub.docker.com/r/gabriel0langlois/geoball-quiz).

```powershell
docker build -t gabriel0langlois/geoball-quiz:0.2 services/quiz
.\.venv\Scripts\python.exe -m pytest services/quiz/tests --import-mode=importlib -o pythonpath=services/quiz
```

Les tests utilisent une base SQLite temporaire et indépendante pour chaque test.
Si Windows bloque une bibliothèque native, les lancer dans le conteneur :

```powershell
$source = (Resolve-Path services/quiz).Path
docker run --rm --mount "type=bind,source=$source,target=/src,readonly" gabriel0langlois/geoball-quiz:0.2 sh -c 'pip install --no-cache-dir -r /src/requirements-dev.txt && python -m pytest /src/tests --import-mode=importlib -o pythonpath=/app -p no:cacheprovider'
```

Lancer les tests du catalogue et du quiz séparément : les deux services ont
chacun leur propre package Python `app`.

Parcours vérifié dans Minikube via la gateway : création, réponses, score final
et refus d'une réponse répétée. Une même trace Jaeger contient les deux services ;
le quiz transmet les en-têtes de trace lors de son appel au catalogue.

Déploiement et vérification après redémarrage : [PostgreSQL](../../k8s/database.md).
