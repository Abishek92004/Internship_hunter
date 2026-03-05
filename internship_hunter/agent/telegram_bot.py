"""
telegram_bot.py — Long-polling Telegram bot.
Runs in a background thread. No ngrok. No webhook.
Telegram servers hold the connection; we poll every 30s.
"""
import requests, json, os, time, threading
from . import bot as cmd_bot
from . import notifier

def _token():
    try:
        return json.load(open("config.json"))["telegram"]["bot_token"]
    except:
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

def _set_chat_id(chat_id: str):
    # Backward compatibility for the config setting (optional)
    pass

def _call(method: str, params: dict = None):
    token = _token()
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/{method}",
            params=params or {},
            timeout=35,
        )
        return r.json()
    except Exception as e:
        print(f"[TelegramBot] API error ({method}): {e}")
        return {}

def poll():
    print("[TelegramBot] Starting long-poll loop...")
    offset = 0

    while True:
        try:
            data = _call("getUpdates", {
                "offset":  offset,
                "timeout": 30,          # long-poll: waits up to 30s for a message
                "allowed_updates": ["message"],
            })

            updates = data.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1

                # Extract message text
                msg  = update.get("message", {})
                text = msg.get("text", "").strip()
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if not text or not chat_id:
                    continue

                print(f"[TelegramBot] Message from {chat_id}: '{text}'")

                # Process command and reply
                from . import database as db
                db.set_current_user(chat_id)
                db.init_db()
                
                reply = cmd_bot.handle(text, chat_id)
                notifier.send(reply, chat_id)

        except Exception as e:
            print(f"[TelegramBot] Poll error: {e}. Retrying in 5s...")
            time.sleep(5)

def start_in_thread():
    """Start polling in a daemon thread alongside FastAPI."""
    t = threading.Thread(target=poll, daemon=True)
    t.start()
    return t