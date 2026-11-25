import os
import random
from contextlib import asynccontextmanager
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import database
from app.database import Question, Quiz, get_session


class Country(BaseModel):
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    capital: str = Field(min_length=1)


def get_countries(request: Request) -> list[Country]:
    url = os.environ.get("CATALOG_URL", "http://127.0.0.1:8000").rstrip("/")
    # Conserver le contexte de trace entre les deux services.
    trace_headers = {
        name: request.headers[name]
        for name in (
            "x-request-id",
            "traceparent",
            "tracestate",
            "b3",
            "x-b3-traceid",
            "x-b3-spanid",
            "x-b3-parentspanid",
            "x-b3-sampled",
            "x-b3-flags",
        )
        if name in request.headers
    }
    try:
        response = httpx.get(f"{url}/countries", timeout=5, headers=trace_headers)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Le catalogue doit renvoyer une liste")
        countries = [Country.model_validate(item) for item in data]
    except (httpx.HTTPError, ValueError, TypeError) as error:
        raise HTTPException(status_code=503, detail="Catalogue indisponible") from error

    codes = {country.code for country in countries}
    capitals = {country.capital for country in countries}
    if len(codes) != len(countries) or len(capitals) < 4:
        raise HTTPException(status_code=503, detail="Catalogue insuffisant pour un QCM")
    return countries


class CreateQuiz(BaseModel):
    number_of_questions: int = Field(default=5, ge=1, le=10, strict=True)


class QuestionView(BaseModel):
    id: UUID
    country: str
    choices: list[str]
    answered: bool


class QuizView(BaseModel):
    id: UUID
    questions: list[QuestionView]
    score: int
    finished: bool


class Answer(BaseModel):
    question_id: UUID
    choice: str


class AnswerResult(BaseModel):
    correct: bool
    score: int
    finished: bool


def quiz_view(quiz: Quiz):
    return QuizView(
        id=quiz.id,
        questions=[
            QuestionView(
                id=question.id,
                country=question.country,
                choices=question.choices,
                answered=question.answer is not None,
            )
            for question in quiz.questions
        ],
        score=quiz.score,
        finished=quiz.finished,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = database.get_engine()
    # Première version du schéma ; create_all ne remplace pas des migrations.
    database.Base.metadata.create_all(engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="GeoBall — Quiz",
    docs_url="/quizzes/docs",
    openapi_url="/quizzes/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return JSONResponse(status_code=503, content={"detail": "Base de données indisponible"})


@app.get("/quizzes/health")
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/quizzes", response_model=QuizView, status_code=201)
def create_quiz(
    request: CreateQuiz,
    countries: list[Country] = Depends(get_countries),
    session: Session = Depends(get_session),
):
    if request.number_of_questions > len(countries):
        raise HTTPException(status_code=400, detail="Pas assez de pays dans le catalogue")

    capitals = sorted({country.capital for country in countries})
    questions = []
    for position, country in enumerate(random.sample(countries, request.number_of_questions)):
        choices = random.sample([capital for capital in capitals if capital != country.capital], 3)
        choices.append(country.capital)
        random.shuffle(choices)
        questions.append(
            Question(
                country=country.name,
                choices=choices,
                correct_answer=country.capital,
                position=position,
            )
        )

    quiz = Quiz(questions=questions)
    session.add(quiz)
    session.commit()
    return quiz_view(quiz)


@app.get("/quizzes/{quiz_id}", response_model=QuizView)
def get_quiz(quiz_id: UUID, session: Session = Depends(get_session)):
    quiz = session.get(Quiz, str(quiz_id))
    if quiz is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    return quiz_view(quiz)


@app.post("/quizzes/{quiz_id}/answers", response_model=AnswerResult)
def answer_question(quiz_id: UUID, answer: Answer, session: Session = Depends(get_session)):
    # Sérialiser les réponses d'une partie, même entre plusieurs processus.
    quiz = session.scalar(select(Quiz).where(Quiz.id == str(quiz_id)).with_for_update())
    if quiz is None:
        raise HTTPException(status_code=404, detail="Partie introuvable")
    question = next(
        (question for question in quiz.questions if question.id == str(answer.question_id)),
        None,
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question introuvable")
    if question.answer is not None:
        raise HTTPException(status_code=409, detail="Question déjà répondue")
    if answer.choice not in question.choices:
        raise HTTPException(status_code=400, detail="Choix invalide")
    updated = session.execute(
        update(Question)
        .where(Question.id == question.id, Question.answer.is_(None))
        .values(answer=answer.choice)
    )
    if updated.rowcount != 1:
        raise HTTPException(status_code=409, detail="Question déjà répondue")
    result = AnswerResult(
        correct=answer.choice == question.correct_answer,
        score=quiz.score,
        finished=quiz.finished,
    )
    session.commit()
    return result
