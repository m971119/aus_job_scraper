import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.db")

import pytest
from sqlmodel import SQLModel
from database import engine


@pytest.fixture(autouse=True, scope="session")
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
