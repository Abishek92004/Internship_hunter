import httpx
from .base import Job

KEYWORDS = ["machine learning", "ml", "data science", "data analyst",
            "artificial intelligence", "ai", "python", "nlp", "deep learning"]

def fetch() -> list[Job]:
    print("[RemoteOK] Fetching...")
    try:
        r = httpx.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
            follow_redirects=True,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[RemoteOK] Error: {e}")
        return []

    jobs = []
    for item in data:
        if not isinstance(item, dict) or "position" not in item:
            continue

        title = item.get("position", "").lower()
        tags  = " ".join(item.get("tags", [])).lower()
        text  = f"{title} {tags}"

        # Only internship / entry-level / ML-related
        is_intern = any(k in text for k in ["intern", "junior", "entry"])
        is_ml     = any(k in text for k in KEYWORDS)
        if not (is_intern or is_ml):
            continue

        jobs.append(Job(
            title       = item.get("position", ""),
            company     = item.get("company", ""),
            location    = item.get("location", "Remote"),
            description = item.get("description", "") or f"{item.get('position','')} at {item.get('company','')}. Tags: {tags}",
            url         = item.get("url", f"https://remoteok.com/l/{item.get('id','')}"),
            platform    = "RemoteOK",
            posted_date = item.get("date", ""),
        ))

    print(f"[RemoteOK] Found {len(jobs)} relevant jobs")
    return jobs
