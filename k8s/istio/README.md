# Istio

Adaptation du [TP servicemesh](https://github.com/charroux/servicemesh).
Version utilisée : Istio 1.32.0, compatible avec Kubernetes 1.37.
Le TP utilise une ancienne version d'Istio.

Installer `istioctl` depuis la [distribution officielle](https://github.com/istio/istio/releases/tag/1.32.0)
et rendre la commande accessible dans le terminal.

```powershell
istioctl x precheck --context=minikube
istioctl install --context=minikube --set profile=demo -y
kubectl --context=minikube label namespace default istio-injection=enabled --overwrite
kubectl --context=minikube --namespace=default apply -f k8s/
kubectl --context=minikube --namespace=default rollout restart deployment/geoball-catalog
kubectl --context=minikube --namespace=default rollout status deployment/geoball-catalog
kubectl --context=minikube --namespace=default apply -f k8s/istio/
```

L'injection s'applique aux nouveaux Pods : le redémarrage est nécessaire si le
catalogue tournait déjà. Son Pod doit contenir `geoball-catalog` et `istio-proxy`,
avec un état `2/2`.

La Gateway écoute les requêtes HTTP et le VirtualService les route vers le
catalogue. Accès local, en gardant le terminal ouvert :

```powershell
kubectl --context=minikube --namespace=istio-system port-forward deployment/istio-ingressgateway 31380:8080
```

Tester http://127.0.0.1:31380/countries et http://127.0.0.1:31380/docs.
La gateway accepte tous les noms d'hôte pour cet exercice local ; ce n'est pas
une configuration destinée à être exposée telle quelle sur Internet.

Le circuit breaker et les outils de supervision du TP ne sont pas encore installés.
