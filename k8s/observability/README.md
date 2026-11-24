# Supervision

Addons de démonstration fournis avec Istio 1.32.0, comme dans le TP servicemesh.
Istio doit déjà être installé. Depuis la racine du dépôt, dans PowerShell :

```powershell
foreach ($name in @("prometheus", "grafana", "kiali", "jaeger")) {
    kubectl --context=minikube apply -f "https://raw.githubusercontent.com/istio/istio/1.32.0/samples/addons/$name.yaml"
}
kubectl --context=minikube --namespace=istio-system wait --for=condition=Available deployment/prometheus deployment/grafana deployment/kiali deployment/jaeger --timeout=180s
kubectl --context=minikube --namespace=default apply -f k8s/observability/
```

- Prometheus collecte les métriques des proxies.
- Grafana affiche les tableaux de bord Istio.
- Kiali représente les services et leurs échanges.
- Jaeger affiche les traces des requêtes.

Le fournisseur `jaeger` est déclaré dans la configuration d'Istio 1.32.0.
Le fichier `tracing.yaml` active les traces pour toutes les requêtes du namespace
`default` : échantillonnage à 100 % uniquement pour ce TP local.

Ouvrir chaque outil dans un terminal séparé et garder les terminaux ouverts :

```powershell
kubectl --context=minikube --namespace=istio-system port-forward service/kiali 20001:20001
kubectl --context=minikube --namespace=istio-system port-forward service/grafana 3000:3000
kubectl --context=minikube --namespace=istio-system port-forward service/tracing 16686:80
```

Accès : http://127.0.0.1:20001/kiali/, http://127.0.0.1:3000 et
http://127.0.0.1:16686/jaeger/.
Générer du trafic via la gateway avec `python scripts/load_catalog.py`, puis
attendre la collecte des métriques. Dans Kiali, sélectionner le namespace `default`.
Dans Grafana, ouvrir les dashboards Istio. Dans Jaeger, chercher le service
`geoball-catalog.default`.

Ces installations sont destinées au TP : pas de stockage durable, interfaces
locales sans authentification de production. Ne pas les exposer sur Internet.

Vérifié après génération de trafic : métriques du catalogue dans Prometheus et
via la source Grafana, catalogue présent dans le graphe Kiali et traces récupérées
dans Jaeger. Les redirections utilisées pour ces vérifications ont été arrêtées.
