import logging
import re
from datetime import date, timedelta
from urllib.parse import urlencode
from playwright.async_api import async_playwright
from schemas import ScrapedJob

SEEK_BASE = "https://www.seek.com.au"
logger = logging.getLogger(__name__)


def build_seek_url(keywords: str, location: str, page: int = 1) -> str:
    params = {"keywords": keywords, "where": location, "sortmode": "ListedDate", "daterange": 31, "page": page}
    return f"{SEEK_BASE}/jobs?{urlencode(params)}"


def parse_listing_date(text: str) -> str:
    """Convert Seek relative date text (e.g. '3d ago', '12d ago•Expiring') to ISO date."""
    clean = text.split("•")[0].strip()
    m = re.match(r"(\d+)d ago", clean)
    if m:
        return (date.today() - timedelta(days=int(m.group(1)))).isoformat()
    return date.today().isoformat()


def parse_location(location_text: str) -> dict:
    """Extract state, city, suburb from a raw Seek location string."""
    au_states = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}
    state = next((s for s in au_states if s in location_text.upper()), None)
    parts = [p.strip() for p in location_text.split() if p.strip()]
    filtered = [p for p in parts if p.upper() not in au_states and not re.match(r"^\d{4}$", p)]
    suburb = filtered[0] if len(filtered) >= 2 else None
    city = filtered[1] if len(filtered) >= 2 else (filtered[0] if filtered else None)
    return {"state": state, "city": city, "suburb": suburb}


async def scrape_seek(
    keywords: str,
    location: str,
    on_progress=None,   # callable(current_page: int, total_pages: int)
    is_cancelled=None,  # callable() -> bool
) -> list[ScrapedJob]:
    """Scrape Seek pages until an empty page is found."""
    results: list[ScrapedJob] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(20000)

        page_num = 1

        while True:
            if is_cancelled and is_cancelled():
                break

            url = build_seek_url(keywords, location, page_num)
            logger.info("Scraping page %d: %s", page_num, url)
            await page.goto(url, wait_until="domcontentloaded")

            if on_progress:
                on_progress(page_num, len(results))

            job_cards = await page.query_selector_all("article[data-testid='job-card']")
            if not job_cards:
                logger.info("No job cards on page %d — done", page_num)
                break

            for card in job_cards:
                try:
                    title_el = await card.query_selector("a[data-testid='job-card-title']")
                    title = await title_el.inner_text() if title_el else None
                    href = await title_el.get_attribute("href") if title_el else None
                    clean_path = href.split("?")[0] if href else None
                    seek_url = f"{SEEK_BASE}{clean_path}" if clean_path and clean_path.startswith("/") else clean_path

                    company_el = await card.query_selector("a[data-automation='jobCompany']")
                    company = await company_el.inner_text() if company_el else None

                    loc_els = await card.query_selector_all("[data-automation='jobLocation']")
                    location_text = " ".join([await e.inner_text() for e in loc_els])
                    loc = parse_location(location_text)

                    salary_el = await card.query_selector("[data-automation='jobSalary']")
                    salary_range = await salary_el.inner_text() if salary_el else None

                    date_el = await card.query_selector("[data-automation='jobListingDate']")
                    date_text = (await date_el.inner_text()).strip() if date_el else ""
                    listed_date = parse_listing_date(date_text)

                    if title and seek_url:
                        results.append(ScrapedJob(
                            seek_url=seek_url,
                            title=title.strip(),
                            company=company.strip() if company else None,
                            state=loc["state"],
                            city=loc["city"],
                            suburb=loc["suburb"],
                            salary_range=salary_range.strip() if salary_range else None,
                            listed_date=listed_date,
                        ))
                except Exception:
                    continue

            page_num += 1

        for job in results:
            try:
                await page.goto(job.seek_url, wait_until="domcontentloaded")
                desc_el = await page.query_selector("[data-automation='jobAdDetails']")
                if desc_el:
                    job.description = (await desc_el.inner_text()).strip()
            except Exception:
                pass

        await browser.close()
    return results
