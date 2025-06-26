from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery.result import AsyncResult
from redis import Redis
from pathlib import Path
import json
from app.utils import calculate_start_date

from app.tasks import run_analysis, app as celery_app

app = FastAPI()

# Disabilita CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Modelli ===
class AnalyzeRequest(BaseModel):
    author: str
    repository: str
    end_date: str

# === Endpoint per analisi ===
@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    task = run_analysis.apply_async(kwargs={
        "author": request.author,
        "repository": request.repository,
        "end_date": request.end_date
    })

    # Scrivi metadati iniziali in Redis per lo stato PENDING
    redis = Redis(host="localhost", port=6379, db=0)
    meta_key = f"celery-task-meta-{task.id}"
    meta_payload = {
        "status": "PENDING",
        "result": None,
        "traceback": None,
        "children": [],
        "meta": {
            "job_id": task.id,
            "author": request.author,
            "repository": request.repository,
            "end_date": request.end_date,
            "start_date": calculate_start_date(request.end_date),
        }
    }
    redis.set(meta_key, json.dumps(meta_payload))

    return {"job_id": task.id}

# === Endpoint per stato ===
@app.get("/status/{job_id}")
def get_status(job_id: str):
    res = AsyncResult(job_id, app=celery_app)
    response = {
        "job_id": job_id,
        "status": res.status,
    }

    if res.info and isinstance(res.info, dict):
        response.update({
            "author": res.info.get("author"),
            "repository": res.info.get("repository"),
            "start_date": res.info.get("start_date"),
            "end_date": res.info.get("end_date"),
        })

    # Se è in PENDING ma Redis ha i metadati, leggili direttamente
    if res.status == "PENDING":
        redis = Redis(host="localhost", port=6379, db=0)
        meta_key = f"celery-task-meta-{job_id}"
        raw = redis.get(meta_key)
        if raw:
            try:
                parsed = json.loads(raw)
                meta = parsed.get("meta", {})
                response.update({
                    "author": meta.get("author"),
                    "repository": meta.get("repository"),
                    "start_date": meta.get("start_date"),
                    "end_date": meta.get("end_date"),
                })
            except Exception:
                pass

    return response

# === Endpoint per risultato ===
@app.get("/result/{job_id}")
def get_result(job_id: str):
    res = AsyncResult(job_id, app=celery_app)

    if res.ready():
        return res.result

    # In caso Redis non abbia il risultato, prova con i file log
    log_path = Path("logs") / f"{job_id}.json"
    if log_path.exists():
        with open(log_path) as f:
            return json.load(f)

    raise HTTPException(status_code=404, detail=f"Risultato non trovato per job_id: {job_id}")