import re
from datetime import date
from urllib.parse import urlencode
from playwright.async_api import async_playwright
from schemas import ScrapedJob

SEEK_BASE = "https://www.seek.com.au"


def build_seek_url(keywords: str, location: str, page: int = 1) -> str:
    params = {"keywords": keywords, "where": location, "page": page}
    return f"{SEEK_BASE}/jobs?{urlencode(params)}"


def parse_location(location_text: str) -> dict:
    """Extract state, city, suburb from a raw Seek location string."""
    au_states = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}
    state = next((s for s in au_states if s in location_text.upper()), None)
    parts = [p.strip() for p in location_text.split() if p.strip()]
    filtered = [p for p in parts if p.upper() not in au_states and not re.match(r"^\d{4}$", p)]
    suburb = filtered[0] if len(filtered) >= 2 else None
    city = filtered[1] if len(filtered) >= 2 else (filtered[0] if filtered else None)
    return {"state": state, "city": city, "suburb": suburb}


async def scrape_seek(keywords: str, location: str, max_pages: int = 3) -> list[ScrapedJob]:
    """Scrape Seek job listings anonymously. Returns list of ScrapedJob."""
    results: list[ScrapedJob] = []
    today = date.today().isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(20000)

        for page_num in range(1, max_pages + 1):
            url = build_seek_url(keywords, location, page_num)
            await page.goto(url, wait_until="domcontentloaded")

            job_cards = await page.query_selector_all("article[data-testid='job-card']")
            if not job_cards:
                break

            for card in job_cards:
                try:
                    title_el = await card.query_selector("a[data-testid='job-title']")
                    title = await title_el.inner_text() if title_el else None
                    href = await title_el.get_attribute("href") if title_el else None
                    seek_url = f"{SEEK_BASE}{href}" if href and href.startswith("/") else href

                    company_el = await card.query_selector("[data-testid='job-card-company-name']")
                    company = await company_el.inner_text() if company_el else None

                    location_el = await card.query_selector("[data-testid='job-card-location']")
                    location_text = await location_el.inner_text() if location_el else ""
                    loc = parse_location(location_text)

                    salary_el = await card.query_selector("[data-testid='job-card-pay']")
                    salary_range = await salary_el.inner_text() if salary_el else None

                    if title and seek_url:
                        results.append(ScrapedJob(
                            seek_url=seek_url,
                            title=title.strip(),
                            company=company.strip() if company else None,
                            state=loc["state"],
                            city=loc["city"],
                            suburb=loc["suburb"],
                            salary_range=salary_range.strip() if salary_range else None,
                            listed_date=today,
                        ))
                except Exception:
                    continue

        # Fetch descriptions by visiting each job page
        for job in results:
            try:
                await page.goto(job.seek_url, wait_until="domcontentloaded")
                desc_el = await page.query_selector("[data-testid='job-detail-overview']")
                if not desc_el:
                    desc_el = await page.query_selector(".job-detail-overview")
                if desc_el:
                    job.description = (await desc_el.inner_text()).strip()
            except Exception:
                pass

        await browser.close()
    return results
