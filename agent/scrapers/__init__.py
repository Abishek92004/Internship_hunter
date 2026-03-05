from .remoteok    import fetch as fetch_remoteok
from .internshala import fetch as fetch_internshala
from .linkedin    import fetch as fetch_linkedin
from .wellfound   import fetch as fetch_wellfound

def fetch_all() -> list:
    jobs = []
    for fetcher in [fetch_remoteok, fetch_internshala, fetch_linkedin, fetch_wellfound]:
        try:
            jobs.extend(fetcher())
        except Exception as e:
            print(f"[Scrapers] Fetcher failed: {e}")
    return jobs
