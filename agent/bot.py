"""
bot.py — Groq-powered agentic bot (free, fast, Llama 3)
Get free API key: https://console.groq.com
"""

import json, os, re
from groq import Groq
from . import database as db
from . import matcher
from .scrapers import fetch_all

_groq_client = None

def _get_client():
    global _groq_client
    if _groq_client is None:
        key = os.environ.get("GROQ_API_KEY", "")
        if not key:
            try:
                key = json.load(open("config.json")).get("groq_api_key", "")
            except:
                pass
        _groq_client = Groq(api_key=key)
    return _groq_client

_last_jobs: list[dict] = []

def _load_config() -> dict:
    try:
        return json.load(open("config.json"))
    except:
        return {}

def _resume() -> str:
    return _load_config().get("resume", "")

SYSTEM_PROMPT = """You are an intelligent internship hunting assistant for a student.
You help find the best Data Science / ML / AI internships.

Your job:
- Understand what the student wants (even if phrased informally)
- Pick the most relevant jobs from the data given
- Explain clearly WHY each job is a good match
- YOU MUST include the direct link (URL) for each internship you recommend. Format it neatly (e.g., "Apply Here: [URL]")
- Flag anything suspicious (vague descriptions, no company info)
- Be concise — Telegram has limited space
- Use simple formatting: bold with *text*"""

def _ask_groq(user_message: str, jobs_context: str, intent: str = "") -> str:
    resume = _resume()
    prompt = f"""Student resume:
{resume[:600]}

{f"Intent: {intent}" if intent else ""}

Available internships (top matches by AI similarity):
{jobs_context}

Student message: "{user_message}"

Write a helpful Telegram reply. Be specific about why each job fits their profile. Keep it concise."""

    try:
        resp = _get_client().chat.completions.create(
            model    = "llama-3.1-8b-instant",   # free, fast
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            max_tokens  = 1024,
            temperature = 0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Groq] API error: {e}")
        return f"AI error: {e}\n\nRaw results:\n\n{jobs_context[:800]}"

def _jobs_to_context(jobs: list[dict], limit: int = 5) -> str:
    if not jobs:
        return "No jobs found."
    lines = []
    for i, j in enumerate(jobs[:limit], 1):
        lines.append(
            f"{i}. {j['title']} at {j['company']}\n"
            f"   Platform: {j['platform']} | Location: {j['location']}\n"
            f"   Match score: {j['match_score']}%\n"
            f"   URL: {j['url']}\n"
            f"   Description: {j.get('description','')[:200]}"
        )
    return "\n\n".join(lines)

def _detect_intent(msg: str) -> str:
    m = msg.lower()
    if any(w in m for w in ["find","search","hunt","fetch","get","show","look"]): return "search"
    if any(w in m for w in ["new","today","latest","recent","fresh"]):            return "new"
    if any(w in m for w in ["top","best","highest","good","strongest"]):          return "top"
    if any(w in m for w in ["status","stats","summary","how many","count"]):      return "status"
    if re.match(r"applied\s+\d+", m): return "applied"
    if re.match(r"save\s+\d+", m):    return "save"
    if re.match(r"ignore\s+\d+", m):  return "ignore"
    if any(w in m for w in ["help","hi","hello","hey","start"]): return "help"
    return "search"

def _handle_status_action(msg: str):
    global _last_jobs
    m = msg.lower().strip()

    for action in ("applied", "save", "ignore"):
        match = re.match(rf"{action}\s+(\d+)", m)
        if match:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(_last_jobs):
                job    = _last_jobs[idx]
                status = "applied" if action == "applied" else ("saved" if action == "save" else "ignored")
                db.update_status(job["id"], status)
                return f"Marked *{job['title']}* at *{job['company']}* as {status.upper()}."
            return f"No job #{idx+1}. Send 'top' or 'find' first."

    if m in ("status", "stats", "summary"):
        s = db.get_stats()
        return (
            f"*Internship Hunter Stats*\n\n"
            f"Total found:   {s['total']}\n"
            f"Found today:   {s['today']}\n"
            f"High priority: {s['high_priority']}\n"
            f"New (unseen):  {s['new']}\n"
            f"Applied:       {s['applied']}\n\n"
            f"📊 *Dashboard:* https://internshiphunter-production.up.railway.app?u={db.get_user()}\n\n"
            f"Send *find* to hunt now."
        )

    if m in ("help", "hi", "hello", "hey", "start"):
        return (
            "*Internship Hunter (Groq AI)*\n\n"
            "Commands:\n"
            "find           - hunt all platforms now\n"
            "new            - jobs found today\n"
            "top            - your best matches\n"
            "status         - stats\n"
            "clear          - wipe full job history for a fresh start\n"
            "search nlp     - keyword search\n"
            "change resume  - update your saved resume\n"
            "applied 2      - mark #2 as applied\n"
            "save 3         - save #3 for later\n"
            "ignore 1       - ignore #1\n\n"
            "Or just talk naturally:\n"
            "_'find remote python roles for freshers'_"
        )
    return None

def handle(message: str, chat_id: str = "default") -> str:
    global _last_jobs
    msg_lower = message.lower().strip()

    if msg_lower in ("change resume", "update resume"):
        return "To update your resume, send a new message starting with the word *resume:*\n\nExample:\n`resume: I am an experienced Data Scientist with Python...`"

    if msg_lower in ("reset", "clear", "clear history"):
        db.clear_user_jobs()
        _last_jobs = []
        return "🗑️ *All previous jobs cleared!*\n\nYour dashboard is now completely empty. Send *find* to hunt for brand new jobs based on your current resume."

    if msg_lower.startswith("resume:"):
        db.save_resume(message[7:].strip())
        return "📄 *Resume Updated!* I have refreshed your profile.\n\n_Tip: Send *clear* if you want to wipe old jobs from your dashboard before running a new search._\n\nSend *find* to hunt for internships based on this new resume."

    current_resume = db.get_resume()
    
    # Auto-save original resume ONLY if one isn't saved yet
    if not current_resume and len(message) > 100:
        db.save_resume(message)
        return "📄 *Resume Saved!* I have updated your profile.\nSend *find* to hunt for internships based on this resume."

    intent = _detect_intent(message)
    print(f"[Bot] Intent: {intent} | Message: '{message}' | User: {chat_id}")

    quick = _handle_status_action(message)
    if quick:
        return quick

    if intent in ("search", "new", "top"):
        if intent == "search":
            print("[Bot] Scraping all platforms...")
            resume = db.get_resume() or _resume()
            if not resume:
                return "❌ *I need your resume first!*\n\nPlease reply with your resume text (just paste it here). I will save it and use it to find internships for you."
            matcher.set_resume(resume)
            raw_jobs  = fetch_all()
            if not raw_jobs:
                return "Could not fetch jobs right now. Try again in a few minutes."
            scored    = matcher.score_jobs(raw_jobs)
            new_count = sum(1 for j in scored if db.save_job(j))
            top_jobs  = db.get_jobs(min_score=0, limit=8)
        elif intent == "new":
            top_jobs  = db.get_jobs(new_only=True, limit=8)
            new_count = len(top_jobs)
        else:
            top_jobs  = db.get_jobs(min_score=0, limit=8)  # show all above threshold
            new_count = len(top_jobs)

        _last_jobs = top_jobs

        if not top_jobs:
            return "No matching internships found yet.\nSend *find* to scrape all platforms now."

        context = _jobs_to_context(top_jobs)
        print(f"[Bot] Sending {len(top_jobs)} jobs to Groq AI...")

        reply = _ask_groq(
            f"{message} (found {new_count} new jobs)" if intent == "search" else message,
            context, intent
        )
        reply += "\n\n_Reply 'applied N' / 'save N' / 'ignore N' to track a job._"
        dash_url = f"https://internshiphunter-production.up.railway.app?u={db.get_user()}"
        reply += f"\n📊 *Dashboard:* [Open Control Panel]({dash_url})"
        return reply

    return "Send *help* to see all commands."