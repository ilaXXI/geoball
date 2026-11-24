import os
import random
from dataclasses import dataclass, field
from threading import Lock
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


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
            "x-request-id", "traceparent", "tracestate", "b3",
            "x-b3-traceid", "x-b3-spanid", "x-b3-parentspanid",
            "x-b3-sampled", "x-b3-flags",
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


@dataclass
class Question:
    country: str
    choices: list[str]
    correct_answer: str
    id: UUID = field(default_factory=uuid4)
    answer: str | None = None


@dataclass
class Quiz:
    questions: list[Question]
    id: UUID = field(default_factory=uuid4)

    @property
    def score(self):
        return sum(question.answer == question.correct_answer for question in self.questions)

    @property
    def finished(self):
        return all(question.answer is not None for question in self.questions)

    def view(self):
        return QuizView(
            id=self.id,
            questions=[
                QuestionView(
                    id=question.id,
                    country=question.country,
                    choices=question.choices,
                    answered=question.answer is not None,
                )
                for question in self.questions
            ],
            score=self.score,
            finished=self.finished,
        )


# Stockage temporaire : un seul processus et une seule réplique du service.
quizzes: dict[UUID, Quiz] = {}
quiz_lock = Lock()
app = FastAPI(
    title="GeoBall — Quiz",
    docs_url="/quizzes/docs",
    openapi_url="/quizzes/openapi.json",
    redoc_url=None,
)


@app.get("/quizzes/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/quizzes", response_model=QuizView, status_code=201)
def create_quiz(request: CreateQuiz, countries: list[Country] = Depends(get_countries)):
    if request.number_of_questions > len(countries):
        raise HTTPException(status_code=400, detail="Pas assez de pays dans le catalogue")

    capitals = sorted({country.capital for country in countries})
    questions = []
    for country in random.sample(countries, request.number_of_questions):
        choices = random.sample(
            [capital for capital in capitals if capital != country.capital], 3
        )
        choices.append(country.capital)
        random.shuffle(choices)
        questions.append(Question(country.name, choices, country.capital))

    quiz = Quiz(questions)
    with quiz_lock:
        quizzes[quiz.id] = quiz
        return quiz.view()


@app.get("/quizzes/{quiz_id}", response_model=QuizView)
def get_quiz(quiz_id: UUID):
    with quiz_lock:
        quiz = quizzes.get(quiz_id)
        if quiz is None:
            raise HTTPException(status_code=404, detail="Partie introuvable")
        return quiz.view()


@app.post("/quizzes/{quiz_id}/answers", response_model=AnswerResult)
def answer_question(quiz_id: UUID, answer: Answer):
    with quiz_lock:
        quiz = quizzes.get(quiz_id)
        if quiz is None:
            raise HTTPException(status_code=404, detail="Partie introuvable")
        question = next(
            (question for question in quiz.questions if question.id == answer.question_id),
            None,
        )
        if question is None:
            raise HTTPException(status_code=404, detail="Question introuvable")
        if question.answer is not None:
            raise HTTPException(status_code=409, detail="Question déjà répondue")
        if answer.choice not in question.choices:
            raise HTTPException(status_code=400, detail="Choix invalide")
        question.answer = answer.choice
        return AnswerResult(
            correct=question.answer == question.correct_answer,
            score=quiz.score,
            finished=quiz.finished,
        )
