# Internship Hunter Bot

Message your WhatsApp bot. It hunts internships across RemoteOK, Internshala, LinkedIn, and Wellfound — scores them against your resume — and replies with the best matches.

---

## Setup (one time)

### 1. Install Python packages
```bash
pip install -r requirements.txt
```

### 2. Install ngrok
- Download from https://ngrok.com/download
- Sign up free at https://ngrok.com
- Run: `ngrok authtoken <cr_3AHlrwb5URKLD9LrjLGePlbV9MT>`

### 3. Edit config.json
```json
{
  "resume": "M.Sc Integrated Data Science (2026)
Skills: Python, SQL, Machine Learning, Deep Learning, NLP, Reinforcement Learning, FastAPI, Streamlit
Projects: Cricket Clutch Score Metric, RL Traffic Control System, ML Food Recommendation Model
Experience: Data Analytics Intern – Financial Advisory
Looking for: AI/ML Internship | Sports Analytics | Agentic AI | Remote/Hybrid",
  "whatsapp": {
    "instance_id": "7103529991",
    "api_token":   "17a30aff10a5462292d012ee398f0b991856f5d62fd3421abe",
    "phone":       "919585289813"
  }
}
```

### 4. Run
```bash
python run.py
```

That's it. The script:
- Starts ngrok automatically
- Sets the Green API webhook automatically  
- Prints the dashboard URL
- Waits for your WhatsApp messages

---

## WhatsApp Commands

| Command | What it does |
|---|---|
| `find` | Scrapes all platforms right now and sends top matches |
| `new` | Shows jobs found today |
| `top` | Shows highest match scores ever |
| `status` | Stats: total found, applied, pending |
| `search python intern` | Keyword search |
| `applied 2` | Mark job #2 as applied |
| `save 3` | Save job #3 for later |
| `ignore 1` | Ignore job #1 |
| `help` | Show all commands |

---

## Dashboard

Open **http://localhost:8000** in your browser.

- See all jobs found with match scores
- Filter by: High Match / Medium / New / Applied / Saved
- Search by keyword
- Click Apply to open the original listing
- Mark Applied / Save / Ignore directly

---

## How Match Scoring Works

Uses `sentence-transformers` (all-MiniLM-L6-v2) — semantic AI similarity.
It understands meaning, not just keywords.

- **>85%** — High priority (shown first, bot alerts you)
- **65-85%** — Medium (stored, visible in dashboard)
- **<65%** — Low (stored silently)

**Tip:** The more detailed your resume text in config.json, the better the matching.
List every skill, technology, and domain you know.

---

## Troubleshooting

**"find" takes a long time**
→ First run downloads the AI model (~80MB). Normal. Subsequent runs are fast.

**Bot not replying**
→ Check ngrok is running: http://127.0.0.1:4040
→ Check Green API instance is Authorized at green-api.com
→ Make sure the webhook URL in Green API settings matches the ngrok URL

**Match scores all low**
→ Add more skills to your resume in config.json
→ Be specific: "pandas, scikit-learn, TensorFlow" beats "Python libraries"

**Internshala/LinkedIn not finding results**
→ These sites occasionally block scrapers. RemoteOK always works (free API).
→ Try again in 10-15 minutes.
