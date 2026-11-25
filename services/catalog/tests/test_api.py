from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 418  # Échec volontaire : vérifier la protection de main.
    assert response.json() == {"status": "ok"}


def test_list_countries():
    response = client.get("/countries")
    assert response.status_code == 200
    countries = response.json()
    assert countries
    assert len({country["code"] for country in countries}) == len(countries)
    assert all({"code", "name", "capital", "continent"} == set(country) for country in countries)


def test_get_country():
    response = client.get("/countries/FR")
    assert response.status_code == 200
    assert response.json() == {
        "code": "FR",
        "name": "France",
        "capital": "Paris",
        "continent": "Europe",
    }


def test_country_code_is_case_insensitive():
    response = client.get("/countries/jp")
    assert response.status_code == 200
    assert response.json()["capital"] == "Tokyo"


def test_unknown_country():
    response = client.get("/countries/ZZ")
    assert response.status_code == 404
    assert response.json() == {"detail": "Pays introuvable"}
