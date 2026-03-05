import sqlite3
import contextvars
from contextlib import contextmanager
from .scrapers.base import Job

DB_PATH = "jobs.db"

_user_ctx = contextvars.ContextVar("chat_id", default="default")

def set_current_user(chat_id: str):
    _user_ctx.set(str(chat_id))

def get_user() -> str:
    return _user_ctx.get()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,
    company     TEXT,
    location    TEXT,
    description TEXT,
    url         TEXT UNIQUE,
    platform    TEXT,
    posted_date TEXT,
    found_date  TEXT,
    deadline    TEXT
);

CREATE TABLE IF NOT EXISTS users (
    chat_id TEXT PRIMARY KEY,
    resume TEXT
);

CREATE TABLE IF NOT EXISTS user_jobs (
    chat_id TEXT,
    job_id INTEGER,
    match_score REAL DEFAULT 0,
    priority TEXT DEFAULT 'low',
    status TEXT DEFAULT 'new',
    notified INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, job_id),
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);
"""

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    print(f"[DB] Initialized at {DB_PATH}")

def save_resume(resume_text: str):
    chat_id = get_user()
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO users (chat_id, resume) VALUES (?, ?)", (chat_id, resume_text))

def get_resume() -> str:
    chat_id = get_user()
    with get_conn() as conn:
        row = conn.execute("SELECT resume FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
        return row["resume"] if row else ""

def is_duplicate(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM jobs WHERE url = ?", (url,)).fetchone()
        return row is not None

def save_job(job: Job) -> bool:
    """Returns True if inserted into user_jobs (new for this user), False if duplicate."""
    chat_id = get_user()
    priority = "high" if job.match_score >= 85 else "medium" if job.match_score >= 65 else "low"
    
    with get_conn() as conn:
        # Insert into jobs pool if doesn't exist
        try:
            conn.execute("""
                INSERT OR IGNORE INTO jobs (title, company, location, description, url, platform,
                                  posted_date, found_date, deadline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job.title, job.company, job.location, job.description, job.url,
                  job.platform, getattr(job, "posted_date", ""), getattr(job, "found_date", ""), getattr(job, "deadline", "")))
        except sqlite3.Error as e:
            pass

        row = conn.execute("SELECT id FROM jobs WHERE url = ?", (job.url,)).fetchone()
        if not row:
            return False
        job_id = row["id"]

        dup = conn.execute("SELECT 1 FROM user_jobs WHERE chat_id = ? AND job_id = ?", (chat_id, job_id)).fetchone()
        if dup:
            return False

        conn.execute("""
            INSERT INTO user_jobs (chat_id, job_id, match_score, priority)
            VALUES (?, ?, ?, ?)
        """, (chat_id, job_id, job.match_score, priority))
        
    return True

def get_jobs(priority=None, status=None, platform=None,
             min_score=0, limit=50, new_only=False) -> list[dict]:
    chat_id = get_user()
    query  = """
        SELECT j.*, uj.match_score, uj.priority, uj.status, uj.notified 
        FROM jobs j
        JOIN user_jobs uj ON j.id = uj.job_id
        WHERE uj.chat_id = ? AND uj.match_score >= ?
    """
    params = [chat_id, min_score]
    if priority: query += " AND uj.priority = ?";  params.append(priority)
    if status:   query += " AND uj.status = ?";    params.append(status)
    if platform: query += " AND j.platform = ?";  params.append(platform)
    if new_only: query += " AND uj.status = 'new'"
    query += " ORDER BY uj.match_score DESC, j.found_date DESC LIMIT ?"
    params.append(limit)
    
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

def update_status(job_id: int, status: str):
    chat_id = get_user()
    with get_conn() as conn:
        conn.execute("UPDATE user_jobs SET status = ? WHERE chat_id = ? AND job_id = ?", (status, chat_id, job_id))

def mark_notified(job_ids: list[int]):
    chat_id = get_user()
    with get_conn() as conn:
        conn.executemany("UPDATE user_jobs SET notified = 1 WHERE chat_id = ? AND job_id = ?",
                         [(chat_id, jid) for jid in job_ids])

def get_stats() -> dict:
    chat_id = get_user()
    with get_conn() as conn:
        base = "SELECT COUNT(*) FROM jobs j JOIN user_jobs uj ON j.id = uj.job_id WHERE uj.chat_id = ?"
        total    = conn.execute(base, (chat_id,)).fetchone()[0]
        today    = conn.execute(base + " AND date(j.found_date) = date('now')", (chat_id,)).fetchone()[0]
        high     = conn.execute(base + " AND uj.priority = 'high'", (chat_id,)).fetchone()[0]
        applied  = conn.execute(base + " AND uj.status = 'applied'", (chat_id,)).fetchone()[0]
        new      = conn.execute(base + " AND uj.status = 'new'", (chat_id,)).fetchone()[0]
    return {"total": total, "today": today, "high_priority": high,
            "applied": applied, "new": new}

def search_jobs(keyword: str, limit: int = 10) -> list[dict]:
    chat_id = get_user()
    kw = f"%{keyword.lower()}%"
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT j.*, uj.match_score, uj.priority, uj.status, uj.notified
            FROM jobs j JOIN user_jobs uj ON j.id = uj.job_id
            WHERE uj.chat_id = ? AND (lower(j.title) LIKE ? OR lower(j.company) LIKE ? OR lower(j.description) LIKE ?)
            ORDER BY uj.match_score DESC LIMIT ?
        """, (chat_id, kw, kw, kw, limit)).fetchall()
    return [dict(r) for r in rows]

def get_unnotified_high() -> list[dict]:
    chat_id = get_user()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT j.*, uj.match_score, uj.priority, uj.status, uj.notified
            FROM jobs j JOIN user_jobs uj ON j.id = uj.job_id
            WHERE uj.chat_id = ? AND uj.priority = 'high' AND uj.notified = 0
            ORDER BY uj.match_score DESC LIMIT 10
        """, (chat_id,)).fetchall()
    return [dict(r) for r in rows]
