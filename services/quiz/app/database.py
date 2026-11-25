import os
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    questions: Mapped[list["Question"]] = relationship(
        cascade="all, delete-orphan", order_by="Question.position"
    )

    @property
    def score(self):
        return sum(question.answer == question.correct_answer for question in self.questions)

    @property
    def finished(self):
        return all(question.answer is not None for question in self.questions)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id"), index=True)
    position: Mapped[int]
    country: Mapped[str]
    choices: Mapped[list[str]] = mapped_column(JSON)
    correct_answer: Mapped[str]
    answer: Mapped[str | None]


@lru_cache
def get_engine():
    url = URL.create(
        "postgresql+psycopg",
        username=os.environ.get("POSTGRES_USER", "geoball"),
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "geoball"),
    )
    return create_engine(
        url, pool_pre_ping=True, hide_parameters=True, connect_args={"connect_timeout": 5}
    )


def get_session():
    with Session(get_engine()) as session:
        yield session
