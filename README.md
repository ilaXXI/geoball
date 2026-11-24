# geoball

Projet de quiz géographique en Python / FastAPI pour les cours de Cloud Integration
et de DevOps.

Pour l'instant : une API de catalogue avec sept pays et leurs capitales.

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

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest services/catalog/tests --import-mode=importlib -o pythonpath=services/catalog
```
