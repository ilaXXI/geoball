# geoball

Projet de quiz géographique en Python / FastAPI pour les cours de Cloud Integration
et de DevOps.

Deux services : un catalogue de sept pays et un [quiz sur les capitales](services/quiz/README.md).

## Lancement local (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r services/catalog/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services/catalog --reload
```

Documentation de l'API : http://127.0.0.1:8000/docs

## Docker

Depuis la racine du dépôt :

```powershell
docker build -t geoball-catalog:0.1 services/catalog
docker run --rm -p 8001:8000 geoball-catalog:0.1
```

Documentation : http://127.0.0.1:8001/docs

L'image est aussi disponible sur [Docker Hub](https://hub.docker.com/r/gabriel0langlois/geoball-catalog) :

```powershell
docker run --rm -p 8001:8000 gabriel0langlois/geoball-catalog:0.1
```

## Kubernetes (Minikube)

```powershell
minikube start --driver=docker
kubectl --context=minikube --namespace=default apply -f k8s/
kubectl --context=minikube --namespace=default rollout status deployment/geoball-catalog
kubectl --context=minikube --namespace=default rollout status deployment/geoball-quiz
minikube service geoball-catalog --url
```

Ajouter `/docs` à l'URL affichée. Garder le terminal ouvert si Minikube utilise un tunnel.

## Service mesh

Installation et accès via la gateway : [Istio](k8s/istio/README.md).
Le catalogue est accessible sur `/countries` et le quiz sur `/quizzes`.
Documentation du quiz via la gateway : http://127.0.0.1:31380/quizzes/docs.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest services/catalog/tests --import-mode=importlib -o pythonpath=services/catalog
.\.venv\Scripts\python.exe -m pytest services/quiz/tests --import-mode=importlib -o pythonpath=services/quiz
```
