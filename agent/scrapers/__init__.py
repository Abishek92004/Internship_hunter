from .remoteok    import fetch as fetch_remoteok
from .internshala import fetch as fetch_internshala
from .linkedin    import fetch as fetch_linkedin
from .wellfound   import fetch as fetch_wellfound
from .glassdoor   import fetch as fetch_glassdoor
from .instahyre   import fetch as fetch_instahyre
from .joincom     import fetch as fetch_joincom

ALL_FETCHERS = [
    fetch_remoteok,
    fetch_internshala,
    fetch_linkedin,
    fetch_wellfound,
    fetch_glassdoor,
    fetch_instahyre,
    fetch_joincom,
]

def fetch_all() -> list:
    jobs = []
    for fetcher in ALL_FETCHERS:
        try:
            jobs.extend(fetcher())
        except Exception as e:
            print(f"[Scrapers] Fetcher failed: {e}")
    return jobs
