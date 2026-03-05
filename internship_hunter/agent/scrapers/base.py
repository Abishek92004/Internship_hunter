from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Job:
    title:       str
    company:     str
    location:    str
    description: str
    url:         str
    platform:    str
    posted_date: Optional[str] = None
    deadline:    Optional[str] = None
    match_score: float = 0.0
    found_date:  str = field(default_factory=lambda: datetime.now().isoformat())
