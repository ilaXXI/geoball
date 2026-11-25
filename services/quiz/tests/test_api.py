from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app import database
from app.main import Country, app, get_countries


COUNTRIES = [
    Country(code="FR", name="France", capital="Paris"),
    Country(code="JP", name="Japon", capital="Tokyo"),
    Country(code="KE", name="Kenya", capital="Nairobi"),
    Country(code="CA", name="Canada", capital="Ottawa"),
    Country(code="DE", name="Allemagne", capital="Berlin"),
]
CAPITALS = {country.name: country.capital for country in COUNTRIES}


@pytest.fixture
def engine(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'quiz.db'}", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(database, "get_engine", lambda: engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    app.dependency_overrides[get_countries] = lambda: COUNTRIES
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def create(client, count=3):
    response = client.post("/quizzes", json={"number_of_questions": count})
    assert response.status_code == 201
    return response.json()


def test_health_and_documentation(client):
    assert client.get("/quizzes/health").json() == {"status": "ok"}
    assert client.get("/quizzes/docs").status_code == 200
    assert client.get("/quizzes/openapi.json").status_code == 200


def test_questions_have_distinct_choices_and_no_answer_leak(client):
    quiz = create(client)
    assert quiz["score"] == 0
    assert quiz["finished"] is False
    assert len({question["country"] for question in quiz["questions"]}) == 3
    for question in quiz["questions"]:
        assert set(question) == {"id", "country", "choices", "answered"}
        assert len(set(question["choices"])) == 4
        assert CAPITALS[question["country"]] in question["choices"]
        assert question["answered"] is False
    assert client.get(f"/quizzes/{quiz['id']}").json() == quiz


def test_score_and_end_of_game(client):
    quiz = create(client, 2)
    for index, question in enumerate(quiz["questions"]):
        correct = CAPITALS[question["country"]]
        choice = correct if index == 0 else next(
            choice for choice in question["choices"] if choice != correct
        )
        response = client.post(
            f"/quizzes/{quiz['id']}/answers",
            json={"question_id": question["id"], "choice": choice},
        )
        assert response.status_code == 200
        assert response.json() == {
            "correct": index == 0,
            "score": 1,
            "finished": index == 1,
        }
    assert client.get(f"/quizzes/{quiz['id']}").json()["finished"] is True


def test_answer_cannot_be_counted_twice(client):
    quiz = create(client, 1)
    question = quiz["questions"][0]
    body = {"question_id": question["id"], "choice": CAPITALS[question["country"]]}
    url = f"/quizzes/{quiz['id']}/answers"
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: client.post(url, json=body).status_code, range(2)))
    assert sorted(statuses) == [200, 409]
    assert client.get(f"/quizzes/{quiz['id']}").json()["score"] == 1


def test_invalid_choice_does_not_consume_question(client):
    quiz = create(client, 1)
    question = quiz["questions"][0]
    response = client.post(
        f"/quizzes/{quiz['id']}/answers",
        json={"question_id": question["id"], "choice": "invalide"},
    )
    assert response.status_code == 400
    state = client.get(f"/quizzes/{quiz['id']}").json()
    assert state["questions"][0]["answered"] is False
    assert state["score"] == 0


def test_unknown_game_and_question(client):
    assert client.get(f"/quizzes/{uuid4()}").status_code == 404
    body = {"question_id": str(uuid4()), "choice": "Paris"}
    assert client.post(f"/quizzes/{uuid4()}/answers", json=body).status_code == 404
    quiz = create(client)
    assert client.post(f"/quizzes/{quiz['id']}/answers", json=body).status_code == 404


@pytest.mark.parametrize("count", [0, -1, 11, "3", True])
def test_invalid_question_count(client, count):
    assert client.post("/quizzes", json={"number_of_questions": count}).status_code == 422


def test_not_enough_countries(client):
    assert client.post("/quizzes", json={"number_of_questions": 6}).status_code == 400


@pytest.mark.parametrize("failure", ["timeout", "http", "json", "incomplete"])
def test_catalog_failure(client, engine, monkeypatch, failure):
    app.dependency_overrides.clear()

    def fake_get(url, timeout, headers):
        assert url.endswith("/countries")
        assert timeout == 5
        if failure == "timeout":
            raise httpx.ConnectTimeout("catalogue indisponible")
        request = httpx.Request("GET", url)
        if failure == "http":
            return httpx.Response(500, request=request)
        if failure == "json":
            return httpx.Response(200, text="pas du JSON", request=request)
        return httpx.Response(200, json=[{"code": "FR"}], request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    response = client.post("/quizzes", json={})
    assert response.status_code == 503
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(database.Quiz)) == 0


def test_catalog_call_and_configuration(monkeypatch):
    monkeypatch.setenv("CATALOG_URL", "http://catalog:8000/")

    def fake_get(url, timeout, headers):
        assert url == "http://catalog:8000/countries"
        assert headers == {"traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"}
        return httpx.Response(
            200,
            json=[country.model_dump() for country in COUNTRIES],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    request = Request({
        "type": "http",
        "headers": [
            (b"traceparent", b"00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"),
            (b"authorization", b"ne-pas-transmettre"),
        ],
    })
    assert get_countries(request) == COUNTRIES


@pytest.mark.parametrize("countries", [COUNTRIES[:3], [COUNTRIES[0]] * 4, []])
def test_catalog_cannot_provide_a_qcm(client, monkeypatch, countries):
    app.dependency_overrides.clear()
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, timeout, headers: httpx.Response(
            200,
            json=[country.model_dump() for country in countries],
            request=httpx.Request("GET", url),
        ),
    )
    assert client.post("/quizzes", json={}).status_code == 503


def test_game_survives_an_application_restart(engine):
    app.dependency_overrides[get_countries] = lambda: COUNTRIES
    try:
        with TestClient(app) as first:
            quiz = create(first, 2)
            question = quiz["questions"][0]
            response = first.post(
                f"/quizzes/{quiz['id']}/answers",
                json={
                    "question_id": question["id"],
                    "choice": CAPITALS[question["country"]],
                },
            )
            assert response.json()["score"] == 1
        # Fermer puis rouvrir l'application et ses connexions, sans effacer la base.
        with TestClient(app) as second:
            state = second.get(f"/quizzes/{quiz['id']}").json()
            assert state["score"] == 1
            assert state["finished"] is False
            assert [q["id"] for q in state["questions"]] == [
                q["id"] for q in quiz["questions"]
            ]
            assert state["questions"][0]["answered"] is True
            question = state["questions"][1]
            response = second.post(
                f"/quizzes/{quiz['id']}/answers",
                json={
                    "question_id": question["id"],
                    "choice": CAPITALS[question["country"]],
                },
            )
            assert response.json() == {"correct": True, "score": 2, "finished": True}
    finally:
        app.dependency_overrides.clear()


def test_database_unavailable_returns_503(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def unavailable():
        raise OperationalError("connexion", {}, Exception("indisponible"))

    app.dependency_overrides[database.get_session] = unavailable
    response = client.get("/quizzes/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "Base de données indisponible"}
