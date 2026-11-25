# PostgreSQL

Configuration dans `geoball-database` (ConfigMap), mot de passe dans
`geoball-postgres` (Secret). Aucun mot de passe dans les manifests ou l'image.
Depuis la racine du dépôt :

```powershell
python scripts/create_db_secret.py
kubectl --context=minikube --namespace=default apply -f k8s/postgres.yaml
kubectl --context=minikube --namespace=default rollout status deployment/geoball-postgres
kubectl --context=minikube --namespace=default apply -f k8s/
kubectl --context=minikube --namespace=default rollout status deployment/geoball-quiz
```

Le script génère le mot de passe en mémoire et transmet le Secret à Kubernetes
sans écrire de fichier. Il conserve le Secret s'il existe déjà.
Un Secret Kubernetes n'est pas un coffre-fort : les droits d'accès restent importants.

Le PVC `geoball-postgres-data` garde les données lors du remplacement du Pod.
Ne pas supprimer ce PVC ni le Secret pour simplement redémarrer l'application.
La persistance locale n'est ni une sauvegarde ni de la haute disponibilité.
Les anciennes parties de la version en mémoire ne sont pas importées.

## Vérification

Avec la gateway accessible sur le port 31380 :

```powershell
python scripts/check_persistence.py
```

Ce script redémarre le quiz puis PostgreSQL dans le contexte `minikube`.
Il vérifie la reprise d'une partie et le refus de réponses concurrentes en double.
Test réalisé avec la vraie base PostgreSQL : partie retrouvée après les deux
redémarrages et une seule réponse acceptée sur huit appels simultanés.
