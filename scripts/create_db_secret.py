"""Créer le Secret PostgreSQL local sans enregistrer le mot de passe sur disque."""

import json
import secrets
import subprocess


def main():
    kubectl = ["kubectl", "--context=minikube", "--namespace=default"]
    existing = subprocess.run(
        kubectl + ["get", "secret", "geoball-postgres", "--ignore-not-found", "-o", "name"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if existing.stdout.strip():
        print("Le Secret geoball-postgres existe déjà : mot de passe conservé.")
        return

    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "geoball-postgres"},
        "type": "Opaque",
        "stringData": {"POSTGRES_PASSWORD": secrets.token_urlsafe(32)},
    }
    subprocess.run(
        kubectl + ["create", "-f", "-"],
        input=json.dumps(secret),
        text=True,
        check=True,
        timeout=20,
    )


if __name__ == "__main__":
    main()
