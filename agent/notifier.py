# notifier.py — Telegram Bot API
import requests, json, os

def _creds():
    try:
        cfg = json.load(open("config.json"))
        tg  = cfg.get("telegram", {})
    except:
        tg  = {}
    return (
        os.getenv("TELEGRAM_BOT_TOKEN") or tg.get("bot_token", ""),
        os.getenv("TELEGRAM_CHAT_ID")   or tg.get("chat_id",   ""),
    )

def send(message: str, chat_id: str = None) -> bool:
    token, default_chat_id = _creds()
    target_chat_id = chat_id or default_chat_id
    if not token or not target_chat_id:
        print("[Notifier] Telegram not configured (bot_token or chat_id missing)")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":    target_chat_id,
                "text":       message,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        ok = r.ok
        if not ok:
            print(f"[Notifier] Telegram error: {r.text}")
        return ok
    except Exception as e:
        print(f"[Notifier] Error: {e}")
        return False