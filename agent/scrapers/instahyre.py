import httpx
from bs4 import BeautifulSoup
from .base import Job
import time

# Instahyre – India-focused tech hiring platform
SEARCH_URLS = [
    "https://www.instahyre.com/search-jobs/?q=machine+learning+intern",
    "https://www.instahyre.com/search-jobs/?q=data+science+intern",
    "https://www.instahyre.com/search-jobs/?q=data+analyst+intern",
    "https://www.instahyre.com/search-jobs/?q=ai+intern",
    "https://www.instahyre.com/search-jobs/?q=python+intern",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.instahyre.com/",
}


def fetch() -> list[Job]:
    print("[Instahyre] Fetching...")
    jobs = []
    seen_urls: set[str] = set()

    for url in SEARCH_URLS:
        try:
            r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")

            # Instahyre job cards
            cards = (
                soup.select("div.job-card, div[class*='job-card']")
                or soup.select("div.opportunity-card, div[class*='OpportunityCard']")
                or soup.select("div.job-listing-card")
            )

            for card in cards:
                try:
                    title_el   = card.select_one(
                        "a.job-title, h2 a, h3 a, "
                        "a[class*='title'], span[class*='title']"
                    )
                    company_el = card.select_one(
                        "a.company-name, span.company-name, "
                        "div[class*='company'], a[class*='company']"
                    )
                    loc_el     = card.select_one(
                        "span.location, div.location, "
                        "span[class*='location']"
                    )

                    if not title_el:
                        continue

                    title    = title_el.get_text(strip=True)
                    company  = company_el.get_text(strip=True) if company_el else "Unknown"
                    location = loc_el.get_text(strip=True)    if loc_el    else "India"

                    href    = title_el.get("href", "")
                    job_url = (
                        f"https://www.instahyre.com{href}"
                        if href.startswith("/") else href
                    )
                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    jobs.append(Job(
                        title       = title,
                        company     = company,
                        location    = location,
                        description = (
                            f"{title} at {company}. "
                            f"Location: {location}. "
                            "Internship / fresher role on Instahyre."
                        ),
                        url         = job_url,
                        platform    = "Instahyre",
                    ))
                except Exception:
                    continue

            time.sleep(1)

        except Exception as e:
            print(f"[Instahyre] Error fetching {url}: {e}")
            continue

    print(f"[Instahyre] Found {len(jobs)} jobs")
    return jobs
