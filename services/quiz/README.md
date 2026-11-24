# Quiz

QCM sur les capitales. Le service appelle le catalogue en REST à la création
d'une partie ; les bonnes réponses et le calcul du score restent côté serveur.

Avec le catalogue lancé sur le port 8000, depuis la racine du dépôt :

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

Les parties sont en mémoire : perdues au redémarrage. Garder un seul processus
et une seule réplique tant qu'il n'y a pas de stockage partagé. Pas de comptes
utilisateurs pour cette première version.

## Image et tests

Image publiée : [gabriel0langlois/geoball-quiz:0.1](https://hub.docker.com/r/gabriel0langlois/geoball-quiz).

```powershell
docker build -t gabriel0langlois/geoball-quiz:0.1 services/quiz
.\.venv\Scripts\python.exe -m pytest services/quiz/tests --import-mode=importlib -o pythonpath=services/quiz
```

Lancer les tests du catalogue et du quiz séparément : les deux services ont
chacun leur propre package Python `app`.

Parcours vérifié dans Minikube via la gateway : création, réponses, score final
et refus d'une réponse répétée. Une même trace Jaeger contient les deux services ;
le quiz transmet les en-têtes de trace lors de son appel au catalogue.
