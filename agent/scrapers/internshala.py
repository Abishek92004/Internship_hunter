import httpx
from bs4 import BeautifulSoup
from .base import Job

SEARCH_URLS = [
    "https://internshala.com/internships/machine-learning-internship",
    "https://internshala.com/internships/data-science-internship",
    "https://internshala.com/internships/artificial-intelligence-internship",
    "https://internshala.com/internships/python-internship",
    "https://internshala.com/internships/data-analyst-internship",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch() -> list[Job]:
    print("[Internshala] Fetching...")
    jobs = []
    seen_urls = set()

    for url in SEARCH_URLS:
        try:
            r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            cards = soup.select(".internship_meta") or soup.select(".individual_internship")
            for card in cards:
                try:
                    # Title
                    title_el = card.select_one(".profile a, .job-internship-name a, h3 a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)

                    # Company
                    company_el = card.select_one(".company_name a, .company-name")
                    company = company_el.get_text(strip=True) if company_el else "Unknown"

                    # Location
                    loc_el = card.select_one(".location_link, .locations span")
                    location = loc_el.get_text(strip=True) if loc_el else "India"

                    # Stipend
                    stipend_el = card.select_one(".stipend, .stipend_container")
                    stipend = stipend_el.get_text(strip=True) if stipend_el else ""

                    # URL
                    href = title_el.get("href", "")
                    job_url = f"https://internshala.com{href}" if href.startswith("/") else href
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Duration
                    dur_el = card.select_one(".other_detail_item span, .ic-16-calendar + div")
                    duration = dur_el.get_text(strip=True) if dur_el else ""

                    desc = f"{title} at {company}. Location: {location}. Stipend: {stipend}. Duration: {duration}."

                    jobs.append(Job(
                        title       = title,
                        company     = company,
                        location    = location,
                        description = desc,
                        url         = job_url,
                        platform    = "Internshala",
                    ))
                except Exception:
                    continue

        except Exception as e:
            print(f"[Internshala] Error fetching {url}: {e}")
            continue

    print(f"[Internshala] Found {len(jobs)} jobs")
    return jobs
