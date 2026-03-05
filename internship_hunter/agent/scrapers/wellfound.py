import httpx
from bs4 import BeautifulSoup
from .base import Job

URLS = [
    "https://wellfound.com/jobs?role=Data+Scientist&jobType=internship",
    "https://wellfound.com/jobs?role=Machine+Learning+Engineer&jobType=internship",
    "https://wellfound.com/jobs?role=Data+Analyst&jobType=internship",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def fetch() -> list[Job]:
    print("[Wellfound] Fetching...")
    jobs = []
    seen_urls = set()

    for url in URLS:
        try:
            r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")

            # Wellfound renders job cards with these selectors
            cards = soup.select("div[class*='JobListing'], div[data-test='StartupResult'], .styles_component__")
            for card in cards:
                try:
                    title_el   = card.select_one("a[class*='jobTitle'], h2 a, .title a")
                    company_el = card.select_one("a[class*='company'], h3, .name")
                    loc_el     = card.select_one("span[class*='location'], .styles_location__")
                    link_el    = card.select_one("a[href*='/jobs/']")

                    if not title_el:
                        continue

                    title    = title_el.get_text(strip=True)
                    company  = company_el.get_text(strip=True) if company_el else "Unknown"
                    location = loc_el.get_text(strip=True)    if loc_el    else "Remote"
                    href     = link_el.get("href", "")        if link_el   else ""
                    job_url  = f"https://wellfound.com{href}" if href.startswith("/") else href

                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    jobs.append(Job(
                        title       = title,
                        company     = company,
                        location    = location,
                        description = f"{title} at {company}. Location: {location}. Startup internship.",
                        url         = job_url,
                        platform    = "Wellfound",
                    ))
                except Exception:
                    continue

        except Exception as e:
            print(f"[Wellfound] Error: {e}")
            continue

    print(f"[Wellfound] Found {len(jobs)} jobs")
    return jobs
