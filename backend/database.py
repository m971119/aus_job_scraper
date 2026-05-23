from pathlib import Path
from sqlmodel import SQLModel, create_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/jobs.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db():
    # Ensure the data directory exists for SQLite file-based URLs
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL[len("sqlite:///"):]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
