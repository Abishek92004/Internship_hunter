import httpx
from bs4 import BeautifulSoup
from .base import Job
import time

# Join.com – global startup job board
SEARCH_URLS = [
    "https://join.com/jobs?q=machine+learning+intern",
    "https://join.com/jobs?q=data+science+intern",
    "https://join.com/jobs?q=data+analyst+intern",
    "https://join.com/jobs?q=ai+intern",
    "https://join.com/jobs?q=python+intern",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch() -> list[Job]:
    print("[Join.com] Fetching...")
    jobs = []
    seen_urls: set[str] = set()

    for url in SEARCH_URLS:
        try:
            r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")

            # Join.com job cards
            cards = (
                soup.select("article[data-testid='job-card']")
                or soup.select("div[class*='JobCard'], li[class*='job-item']")
                or soup.select("a[class*='job-card']")
            )

            for card in cards:
                try:
                    title_el   = card.select_one(
                        "h2[class*='title'], h3[class*='title'], "
                        "span[class*='title'], [data-testid='job-title']"
                    )
                    company_el = card.select_one(
                        "span[class*='company'], p[class*='company'], "
                        "[data-testid='company-name']"
                    )
                    loc_el     = card.select_one(
                        "span[class*='location'], p[class*='location'], "
                        "[data-testid='job-location']"
                    )
                    link_el    = card if card.name == "a" else card.select_one("a[href*='/jobs/']")

                    if not title_el:
                        continue

                    title    = title_el.get_text(strip=True)
                    company  = company_el.get_text(strip=True) if company_el else "Unknown"
                    location = loc_el.get_text(strip=True)    if loc_el    else "Remote"

                    href = ""
                    if link_el:
                        href = link_el.get("href", "") if link_el.name == "a" else ""
                    job_url = (
                        f"https://join.com{href}"
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
                            "Internship listing on Join.com."
                        ),
                        url         = job_url,
                        platform    = "Join.com",
                    ))
                except Exception:
                    continue

            time.sleep(1)

        except Exception as e:
            print(f"[Join.com] Error fetching {url}: {e}")
            continue

    print(f"[Join.com] Found {len(jobs)} jobs")
    return jobs
