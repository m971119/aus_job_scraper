import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.db")
os.environ.setdefault("OPENAI_API_KEY", "test-dummy-key")

import pytest
from sqlmodel import SQLModel
from database import engine


@pytest.fixture(autouse=True, scope="session")
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
