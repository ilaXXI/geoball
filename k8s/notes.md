# Essais Kubernetes

Référence : [TP kubernetes-minikube](https://github.com/charroux/kubernetes-minikube).
Commandes lancées avec le contexte `minikube` et le namespace `default`.

## Réplication et remplacement d'un Pod

```powershell
kubectl --context=minikube --namespace=default scale deployment/geoball-catalog --replicas=2
kubectl --context=minikube --namespace=default get pods -l app=geoball-catalog
```

Deux Pods disponibles. Après suppression d'un des Pods avec `kubectl delete pod`,
Kubernetes en crée un autre pour retrouver les deux instances demandées.

## Mise à jour et retour arrière

```powershell
kubectl --context=minikube --namespace=default set image deployment/geoball-catalog geoball-catalog=gabriel0langlois/geoball-catalog@sha256:8759e600eba386355accb4427e48e615df90529369000f7ee5698c5fa85280a5
kubectl --context=minikube --namespace=default rollout status deployment/geoball-catalog
kubectl --context=minikube --namespace=default rollout undo deployment/geoball-catalog
kubectl --context=minikube --namespace=default rollout status deployment/geoball-catalog
```

Le passage du tag `0.1` à son empreinte exacte déclenche une nouvelle révision.
C'est la même image : aucune fonctionnalité n'a changé. Le retour arrière rétablit
la référence `:0.1`. Les deux déploiements se sont terminés correctement ;
l'absence de coupure HTTP pendant la transition n'a pas été mesurée.

## Retour à la configuration du dépôt

```powershell
kubectl --context=minikube --namespace=default apply -f k8s/
```

Le Deployment revient à une instance, comme dans `catalog-deployment.yaml`.
La réplication sur un seul nœud ne protège pas contre une panne de ce nœud.

Après ces essais, accès vérifié avec `minikube service geoball-catalog --url` :
`/health` répond `ok`, `/countries` renvoie sept pays et `/docs` répond en HTTP 200.
Le tunnel de vérification a été arrêté, pas le Deployment.
