import httpx
from bs4 import BeautifulSoup
from .base import Job
import time

# Glassdoor public job-search pages (no login required for listings)
SEARCHES = [
    ("machine learning intern",  "India"),
    ("data science intern",      "India"),
    ("data analyst intern",      "India"),
    ("AI intern",                "India"),
    ("python developer intern",  "India"),
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
    print("[Glassdoor] Fetching...")
    jobs = []
    seen_urls: set[str] = set()

    for keyword, location in SEARCHES:
        try:
            url = (
                "https://www.glassdoor.co.in/Job/jobs.htm?"
                f"sc.keyword={keyword.replace(' ', '+')}"
                f"&locT=N&locId=115&jt=I"   # jt=I → Internship
                "&sortBy=date_desc"
            )
            r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")

            # Glassdoor uses li[data-test="jobListing"] or div.react-job-listing
            cards = (
                soup.select("li[data-test='jobListing']")
                or soup.select("div.react-job-listing")
                or soup.select("li.JobsList_jobListItem__wjTHv")
            )

            for card in cards:
                try:
                    title_el   = card.select_one(
                        "a[data-test='job-title'], "
                        "a.JobCard_jobTitle__GLyJ1, "
                        "a[class*='jobTitle']"
                    )
                    company_el = card.select_one(
                        "span.EmployerProfile_compactEmployerName__9MGcV, "
                        "div[data-test='employer-name'], "
                        "span[class*='EmployerProfile']"
                    )
                    loc_el     = card.select_one(
                        "div[data-test='emp-location'], "
                        "span.JobCard_location__DKIkN, "
                        "div[class*='location']"
                    )

                    if not title_el:
                        continue

                    title    = title_el.get_text(strip=True)
                    company  = company_el.get_text(strip=True) if company_el else "Unknown"
                    location = loc_el.get_text(strip=True)    if loc_el    else "India"

                    href    = title_el.get("href", "")
                    job_url = (
                        f"https://www.glassdoor.co.in{href}"
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
                            "Internship listing on Glassdoor."
                        ),
                        url         = job_url,
                        platform    = "Glassdoor",
                    ))
                except Exception:
                    continue

            time.sleep(1)

        except Exception as e:
            print(f"[Glassdoor] Error for '{keyword}': {e}")
            continue

    print(f"[Glassdoor] Found {len(jobs)} jobs")
    return jobs
