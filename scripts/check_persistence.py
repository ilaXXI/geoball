"""Vérifier la persistance via la gateway en redémarrant les deux services locaux."""

import argparse
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

KUBECTL = ["kubectl", "--context=minikube", "--namespace=default"]


def restart(deployment):
    subprocess.run(
        KUBECTL + ["rollout", "restart", f"deployment/{deployment}"],
        check=True,
        timeout=20,
    )
    subprocess.run(
        KUBECTL + ["rollout", "status", f"deployment/{deployment}", "--timeout=120s"],
        check=True,
        timeout=130,
    )


def wait_for_quiz(client):
    for _ in range(40):
        try:
            response = client.get("/quizzes/health")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Le quiz ne répond pas après le redémarrage")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:31380")
    args = parser.parse_args()

    with httpx.Client(base_url=args.url, timeout=10) as client:
        response = client.get("/countries")
        response.raise_for_status()
        capitals = {country["name"]: country["capital"] for country in response.json()}
        response = client.post("/quizzes", json={"number_of_questions": 2})
        response.raise_for_status()
        quiz = response.json()
        path = f"/quizzes/{quiz['id']}"
        first, second = quiz["questions"]
        response = client.post(
            f"{path}/answers",
            json={"question_id": first["id"], "choice": capitals[first["country"]]},
        )
        response.raise_for_status()
        assert response.json()["score"] == 1

        restart("geoball-quiz")
        wait_for_quiz(client)
        response = client.get(path)
        response.raise_for_status()
        state = response.json()
        assert state["score"] == 1 and not state["finished"]
        assert [q["id"] for q in state["questions"]] == [first["id"], second["id"]]
        assert state["questions"][0]["answered"]
        response = client.post(
            f"{path}/answers",
            json={"question_id": second["id"], "choice": capitals[second["country"]]},
        )
        response.raise_for_status()
        assert response.json() == {"correct": True, "score": 2, "finished": True}
        print("Partie retrouvée et terminée après redémarrage du quiz.")

        restart("geoball-postgres")
        wait_for_quiz(client)
        response = client.get(path)
        response.raise_for_status()
        assert response.json()["score"] == 2 and response.json()["finished"]
        print("Partie conservée après redémarrage de PostgreSQL.")

        response = client.post("/quizzes", json={"number_of_questions": 1})
        response.raise_for_status()
        race = response.json()
        question = race["questions"][0]
        body = {"question_id": question["id"], "choice": capitals[question["country"]]}
        url = f"/quizzes/{race['id']}/answers"
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(lambda _: client.post(url, json=body).status_code, range(8)))
        assert statuses.count(200) == 1 and statuses.count(409) == 7, statuses
        response = client.get(f"/quizzes/{race['id']}")
        response.raise_for_status()
        assert response.json()["score"] == 1
        print("Huit réponses concurrentes : une acceptée, sept refusées, score = 1.")


if __name__ == "__main__":
    main()
