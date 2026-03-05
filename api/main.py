"""
api/main.py — FastAPI server v2 (with full debug logging)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import json, os

from agent import database as db
from agent import bot
from agent import notifier

app = FastAPI(title="Internship Hunter")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def set_db_user(request: Request, call_next):
    # Use user id from query parameter if provided
    u = request.query_params.get("u")
    if u:
        db.set_current_user(u)
    else:
        # Fallback to the environment var or try finding an active user
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if chat_id:
            db.set_current_user(chat_id)
        else:
            try:
                from agent.database import get_conn
                with get_conn() as conn:
                    row = conn.execute("SELECT chat_id FROM users ORDER BY rowid DESC LIMIT 1").fetchone()
                    if row:
                        db.set_current_user(row["chat_id"])
                    else:
                        db.set_current_user("default")
            except:
                db.set_current_user("default")
    return await call_next(request)

DASHBOARD = os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")

@app.get("/")
def dashboard():
    return FileResponse(DASHBOARD)

# ── Webhook ───────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    # Log RAW body — so you can see exactly what Green API sends
    try:
        raw = await request.body()
        body = json.loads(raw)
    except Exception as e:
        print(f"[Webhook] Could not parse body: {e}")
        return {"status": "bad_json"}

    # Log everything so we can debug
    print(f"\n[Webhook] ===== INCOMING =====")
    print(f"[Webhook] typeWebhook: {body.get('typeWebhook', 'MISSING')}")
    print(f"[Webhook] Full body: {json.dumps(body, ensure_ascii=False)[:500]}")

    # Only handle incoming messages
    msg_type = body.get("typeWebhook", "")
    if msg_type not in ("incomingMessageReceived", "incomingMessage"):
        print(f"[Webhook] Ignoring type: {msg_type}")
        return {"status": "ignored", "type": msg_type}

    # Extract text — try all known Green API payload shapes
    text = ""
    try:
        msg_data = body.get("messageData", {})

        # Shape 1: textMessageData (most common)
        if "textMessageData" in msg_data:
            text = msg_data["textMessageData"].get("textMessage", "")

        # Shape 2: extendedTextMessageData
        elif "extendedTextMessageData" in msg_data:
            text = msg_data["extendedTextMessageData"].get("text", "")

        # Shape 3: flat text field
        elif "textMessage" in body:
            text = body["textMessage"]

        # Shape 4: senderData contains message
        elif "body" in body:
            text = body["body"]

        text = text.strip()
    except Exception as e:
        print(f"[Webhook] Error extracting text: {e}")

    print(f"[Webhook] Extracted text: '{text}'")

    if not text:
        print("[Webhook] No text found in payload")
        return {"status": "no_text"}

    # Run command
    print(f"[Webhook] Processing command: '{text}'")
    reply = bot.handle(text)
    print(f"[Webhook] Reply length: {len(reply)} chars")

    # Send WhatsApp reply
    sent = notifier.send(reply)
    print(f"[Webhook] WhatsApp sent: {sent}")

    return {"status": "ok", "command": text, "reply_sent": sent}

# ── Manual test endpoint — call from browser to test bot ──────
@app.get("/test/{command}")
def test_command(command: str):
    """
    Test bot without WhatsApp. 
    Visit: http://localhost:8000/test/find
    """
    reply = bot.handle(command)
    notifier.send(reply)
    return {"command": command, "reply": reply}

# ── Webhook health check ──────────────────────────────────────
@app.get("/webhook")
def webhook_alive():
    """Green API pings this to verify webhook is reachable."""
    return {"status": "ok", "message": "Internship Hunter webhook is alive"}

# ── API endpoints ─────────────────────────────────────────────
@app.get("/api/jobs")
def api_jobs(priority: str = None, status: str = None,
             platform: str = None, min_score: float = 0, limit: int = 100):
    return db.get_jobs(priority=priority, status=status,
                       platform=platform, min_score=min_score, limit=limit)

@app.get("/api/stats")
def api_stats():
    return db.get_stats()

@app.post("/api/jobs/{job_id}/status")
async def update_job_status(job_id: int, request: Request):
    body = await request.json()
    status = body.get("status")
    if status in ("new", "saved", "applied", "ignored"):
        db.update_status(job_id, status)
        return {"ok": True}
    return JSONResponse({"error": "invalid status"}, status_code=400)

@app.get("/api/config")
def get_config():
    try:
        cfg = json.load(open("config.json"))
        cfg.pop("whatsapp", None)
        return cfg
    except:
        return {}

# ── Webhook setup helper ──────────────────────────────────────
@app.post("/api/set-webhook")
async def set_webhook(request: Request):
    """Call this to manually register webhook with Green API."""
    body = await request.json()
    webhook_url = body.get("url", "")
    if not webhook_url:
        return JSONResponse({"error": "url required"}, status_code=400)

    cfg = json.load(open("config.json"))
    wa  = cfg.get("whatsapp", {})
    instance = wa.get("instance_id", "")
    token    = wa.get("api_token", "")

    import requests as req
    url     = f"https://api.green-api.com/waInstance{instance}/setSettings/{token}"
    payload = {
        "webhookUrl":                    webhook_url + "/webhook",
        "incomingWebhook":               "yes",
        "outgoingWebhook":               "no",
        "outgoingMessageWebhook":        "no",
        "stateWebhook":                  "no",
        "markIncomingMessagesReaded":    "yes",
        "delaySendMessagesMilliseconds": 500,
    }
    r = req.post(url, json=payload, timeout=10)
    return {"ok": r.ok, "response": r.text, "webhook_url": webhook_url + "/webhook"}

@app.get("/api/webhook-status")
def webhook_status():
    """Check what webhook URL is currently set in Green API."""
    cfg = json.load(open("config.json"))
    wa  = cfg.get("whatsapp", {})
    instance = wa.get("instance_id", "")
    token    = wa.get("api_token", "")
    import requests as req
    try:
        r = req.get(
            f"https://api.green-api.com/waInstance{instance}/getSettings/{token}",
            timeout=10
        )
        data = r.json()
        return {
            "current_webhook": data.get("webhookUrl", "NOT SET"),
            "incoming_webhook": data.get("incomingWebhook", ""),
        }
    except Exception as e:
        return {"error": str(e)}