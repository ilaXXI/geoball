from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class Country(BaseModel):
    code: str
    name: str
    capital: str
    continent: str


# Premier jeu de données, volontairement limité pour démarrer.
COUNTRIES = [
    Country(code="FR", name="France", capital="Paris", continent="Europe"),
    Country(code="DE", name="Allemagne", capital="Berlin", continent="Europe"),
    Country(code="KE", name="Kenya", capital="Nairobi", continent="Afrique"),
    Country(code="JP", name="Japon", capital="Tokyo", continent="Asie"),
    Country(code="BR", name="Brésil", capital="Brasília", continent="Amérique du Sud"),
    Country(code="CA", name="Canada", capital="Ottawa", continent="Amérique du Nord"),
    Country(code="AU", name="Australie", capital="Canberra", continent="Océanie"),
]

app = FastAPI(title="GeoBall — Catalogue")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/countries", response_model=list[Country])
def list_countries():
    return COUNTRIES


@app.get("/countries/{code}", response_model=Country)
def get_country(code: str):
    for country in COUNTRIES:
        if country.code == code.upper():
            return country
    raise HTTPException(status_code=404, detail="Pays introuvable")
