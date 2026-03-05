import httpx
from bs4 import BeautifulSoup
from .base import Job
import time

SEARCHES = [
    ("machine learning intern", "India"),
    ("data science intern",     "India"),
    ("data analyst intern",     "India"),
    ("AI intern",               "India"),
    ("python intern",           "India"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def fetch() -> list[Job]:
    print("[LinkedIn] Fetching...")
    jobs = []
    seen_ids = set()

    for keyword, location in SEARCHES:
        try:
            url = (
                "https://www.linkedin.com/jobs/search/?"
                f"keywords={keyword.replace(' ', '%20')}"
                f"&location={location.replace(' ', '%20')}"
                "&f_E=1"          # Entry level
                "&f_JT=I"         # Internship
                "&sortBy=DD"      # Most recent
            )
            r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")

            cards = soup.select("div.base-card, li.result-card")
            for card in cards:
                try:
                    # Job ID dedup
                    job_id = card.get("data-entity-urn", "") or card.get("data-id", "")
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    title_el   = card.select_one("h3.base-search-card__title, h3.result-card__title")
                    company_el = card.select_one("h4.base-search-card__subtitle a, h4.result-card__subtitle a")
                    loc_el     = card.select_one("span.job-search-card__location, span.result-card__location")
                    link_el    = card.select_one("a.base-card__full-link, a.result-card__full-card-link")
                    time_el    = card.select_one("time")

                    if not title_el or not link_el:
                        continue

                    title    = title_el.get_text(strip=True)
                    company  = company_el.get_text(strip=True) if company_el else "Unknown"
                    location = loc_el.get_text(strip=True)    if loc_el    else "India"
                    job_url  = link_el.get("href", "").split("?")[0]
                    posted   = time_el.get("datetime", "")    if time_el   else ""

                    jobs.append(Job(
                        title       = title,
                        company     = company,
                        location    = location,
                        description = f"{title} at {company}. Location: {location}. Entry level internship.",
                        url         = job_url,
                        platform    = "LinkedIn",
                        posted_date = posted,
                    ))
                except Exception:
                    continue

            time.sleep(1)  # polite delay between searches

        except Exception as e:
            print(f"[LinkedIn] Error for '{keyword}': {e}")
            continue

    print(f"[LinkedIn] Found {len(jobs)} jobs")
    return jobs
