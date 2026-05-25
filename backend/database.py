from pathlib import Path
from sqlmodel import SQLModel, create_engine
import os

_DEFAULT_DB = Path(__file__).resolve().parent / "data" / "jobs.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB}")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db():
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL[len("sqlite:///"):]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
