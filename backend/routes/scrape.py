import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from models import Job
from schemas import ScrapeRequest, ScrapeStatus
from scraper import scrape_seek

router = APIRouter()

_state: dict = {
    "status": "idle",
    "current_page": 0,
    "total_pages": 0,
    "inserted": 0,
    "updated_reposts": 0,
    "skipped_hidden": 0,
    "error": None,
    "cancel_requested": False,
}


def _reset_state() -> None:
    _state.update({
        "status": "running",
        "current_page": 0,
        "total_pages": 0,
        "inserted": 0,
        "updated_reposts": 0,
        "skipped_hidden": 0,
        "error": None,
        "cancel_requested": False,
    })


def _on_progress(current: int, total: int) -> None:
    _state["current_page"] = current
    _state["total_pages"] = total


def _is_cancelled() -> bool:
    return _state["cancel_requested"]


async def _run_scrape(req: ScrapeRequest) -> None:
    from database import engine
    try:
        jobs = await scrape_seek(
            req.keywords,
            req.location,
            on_progress=_on_progress,
            is_cancelled=_is_cancelled,
        )

        if _state["cancel_requested"]:
            _state["status"] = "cancelled"
            return

        with Session(engine) as session:
            for scraped in jobs:
                existing = session.exec(
                    select(Job).where(Job.seek_url == scraped.seek_url)
                ).first()

                if existing:
                    if existing.is_hidden:
                        _state["skipped_hidden"] += 1
                        continue
                    dates = json.loads(existing.listed_dates or "[]")
                    if scraped.listed_date not in dates:
                        dates.append(scraped.listed_date)
                        existing.listed_dates = json.dumps(dates)
                        existing.latest_listing_date = max(dates)
                        existing.is_repost = True
                        _state["updated_reposts"] += 1
                else:
                    dates = [scraped.listed_date]
                    job = Job(
                        seek_url=scraped.seek_url,
                        title=scraped.title,
                        company=scraped.company,
                        description=scraped.description,
                        state=scraped.state,
                        city=scraped.city,
                        suburb=scraped.suburb,
                        salary_range=scraped.salary_range,
                        listed_dates=json.dumps(dates),
                        latest_listing_date=scraped.listed_date,
                    )
                    session.add(job)
                    _state["inserted"] += 1
            session.commit()

        _state["status"] = "done"

    except Exception as exc:
        _state["status"] = "error"
        _state["error"] = str(exc)


@router.post("/scrape", status_code=202)
async def trigger_scrape(req: ScrapeRequest) -> dict:
    if _state["status"] == "running":
        return JSONResponse(status_code=409, content={"detail": "Scrape already running"})
    _reset_state()
    asyncio.create_task(_run_scrape(req))
    return {"status": "started"}


@router.get("/scrape/status", response_model=ScrapeStatus)
def get_scrape_status() -> ScrapeStatus:
    return ScrapeStatus(
        status=_state["status"],
        current_page=_state["current_page"],
        total_pages=_state["total_pages"],
        inserted=_state["inserted"],
        updated_reposts=_state["updated_reposts"],
        skipped_hidden=_state["skipped_hidden"],
        error=_state["error"],
    )


@router.post("/scrape/cancel")
def cancel_scrape() -> dict:
    _state["cancel_requested"] = True
    return {"status": "cancel_requested"}
