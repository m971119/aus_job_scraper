import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.db")

import json
from sqlmodel import Session, select
from models import Job
from database import create_db, engine


def test_job_insert_and_retrieve():
    create_db()
    with Session(engine) as session:
        job = Job(
            seek_url="https://www.seek.com.au/job/12345",
            title="Software Engineer",
            company="Acme Corp",
            description="A great job",
            state="VIC",
            city="Melbourne",
            suburb="CBD",
            listed_dates=json.dumps(["2026-05-22"]),
            is_repost=False,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        found = session.exec(select(Job).where(Job.seek_url == job.seek_url)).first()
        assert found is not None
        assert found.title == "Software Engineer"
        assert json.loads(found.listed_dates) == ["2026-05-22"]
        assert found.is_repost is False
