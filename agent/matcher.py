from sentence_transformers import SentenceTransformer, util
import torch

_model  = None
_resume = None
_resume_emb = None

def load_model():
    global _model
    if _model is None:
        print("[Matcher] Loading sentence-transformers model (first time only)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")  # fast + accurate, 80MB
        print("[Matcher] Model loaded")
    return _model

def set_resume(resume_text: str):
    global _resume, _resume_emb
    _resume = resume_text
    model   = load_model()
    _resume_emb = model.encode(resume_text, convert_to_tensor=True)
    print(f"[Matcher] Resume embedded ({len(resume_text)} chars)")

def score(job_text: str) -> float:
    """Returns 0-100 similarity score between job text and resume."""
    if _resume_emb is None:
        return 0.0
    model   = load_model()
    job_emb = model.encode(job_text, convert_to_tensor=True)
    sim     = float(util.cos_sim(_resume_emb, job_emb)[0][0])
    return round(sim * 100, 1)

def score_jobs(jobs: list) -> list:
    """Score a list of Job objects. Mutates match_score in place."""
    if not jobs:
        return jobs
    model = load_model()
    texts = [f"{j.title} {j.company} {j.description}" for j in jobs]
    embs  = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)
    for job, emb in zip(jobs, embs):
        if _resume_emb is not None:
            sim = float(util.cos_sim(_resume_emb, emb.unsqueeze(0))[0][0])
            job.match_score = round(sim * 100, 1)
    return jobs
