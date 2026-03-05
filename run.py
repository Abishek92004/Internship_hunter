"""
run.py — Start the Internship Hunter (Telegram version)
Usage: python run.py

No ngrok needed. Bot polls Telegram directly.
"""
import sys, os, json
import uvicorn

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "resume": "",
    "preferences": {
        "roles":     ["data science", "machine learning", "AI", "data analyst", "python"],
        "min_match": 70,
    },
    "telegram": {
        "bot_token": "",
        "chat_id":   "",
    },
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        json.dump(DEFAULT_CONFIG, open(CONFIG_FILE, "w"), indent=2)
        print(f"\nCreated config.json")
        print("Fill in your resume text and Telegram bot_token, then run again.\n")
        sys.exit(0)
    return json.load(open(CONFIG_FILE))

def validate(cfg):
    errors = []
    
    # Prioritize environment variables over config file for deployment safety
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("telegram", {}).get("bot_token")
    if not bot_token:
        errors.append("  - TELEGRAM_BOT_TOKEN is missing (set in env vars or config.json)")
    
    # We no longer strictly require resume here, as users can provide their own resumes directly via telegram.
    
    if errors:
        print("\nFix these configuration issues:\n" + "\n".join(errors))
        sys.exit(1)

def print_banner(bot_username="your_bot"):
    print("\n" + "=" * 55)
    print("  INTERNSHIP HUNTER BOT IS RUNNING")
    print("=" * 55)
    print(f"\n  Dashboard : http://localhost:8000")
    print(f"\n  Open Telegram and message your bot:")
    print(f"    help   - see all commands")
    print(f"    find   - hunt internships now")
    print(f"    status - stats")
    print(f"\n  First message auto-saves your chat ID.")
    print(f"\n  Test without Telegram:")
    print(f"    http://localhost:8000/test/find")
    print("=" * 55 + "\n")

def main():
    cfg = load_config()
    validate(cfg)

    # Set up environent overrides
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        os.environ["TELEGRAM_BOT_TOKEN"] = cfg.get("telegram", {}).get("bot_token", "")
    if not os.environ.get("TELEGRAM_CHAT_ID"):
        os.environ["TELEGRAM_CHAT_ID"]   = cfg.get("telegram", {}).get("chat_id", "")

    # Groq API key
    groq_key = cfg.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        print("WARNING: groq_api_key not set in config.json — AI replies will not work")
    else:
        os.environ["GROQ_API_KEY"] = groq_key
        print("[Groq] API key loaded")

    # Init DB and load resume embedding
    from agent.database     import init_db
    from agent.matcher      import set_resume
    from agent.telegram_bot import start_in_thread

    init_db()
    set_resume(cfg.get("resume", ""))

    # Start Telegram polling in background thread
    start_in_thread()
    print("[Telegram] Bot polling started")

    print_banner()

    # Start FastAPI dashboard
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()