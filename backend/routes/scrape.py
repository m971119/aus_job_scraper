import json
from datetime import datetime, timezone
from fastapi import APIRouter
from sqlmodel import Session, select
from database import engine
from models import Job
from scraper import scrape_seek
from schemas import ScrapeRequest, ScrapeResponse

router = APIRouter()


@router.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(req: ScrapeRequest):
    scraped = await scrape_seek(req.keywords, req.location, req.max_pages)

    inserted = 0
    updated = 0

    with Session(engine) as session:
        for item in scraped:
            existing = session.exec(
                select(Job).where(Job.seek_url == item.seek_url)
            ).first()

            if existing:
                dates = json.loads(existing.listed_dates)
                if item.listed_date not in dates:
                    dates.append(item.listed_date)
                    existing.listed_dates = json.dumps(dates)
                    existing.is_repost = True
                    existing.updated_at = datetime.now(timezone.utc)
                    session.add(existing)
                    updated += 1
            else:
                job = Job(
                    seek_url=item.seek_url,
                    title=item.title,
                    company=item.company,
                    description=item.description,
                    state=item.state,
                    city=item.city,
                    suburb=item.suburb,
                    salary_range=item.salary_range,
                    listed_dates=json.dumps([item.listed_date]),
                    is_repost=False,
                )
                session.add(job)
                inserted += 1

        session.commit()

    return ScrapeResponse(scraped=len(scraped), inserted=inserted, updated_reposts=updated)
