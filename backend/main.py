from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db
from routes import jobs, scrape, tags, sponsors
from routes.resume import router as resume_router, seed_resume
from routes.ai import router as ai_router
from routes.ai_filter import router as ai_filter_router
import os
import logging

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    seed_resume()
    yield


app = FastAPI(title="Aus Job Scraper", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(sponsors.router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(ai_filter_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
