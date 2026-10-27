

from fastapi import FastAPI
from pydantic import BaseModel
from uuid import uuid4

app = FastAPI(title="AI Video Generator API")

jobs = {}

class VideoRequest(BaseModel):
    prompt: str
    duration: int = 8
    style: str = "3D animation"

@app.get("/")
def home():
    return {"message": "AI Video Generator API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
def generate_video(request: VideoRequest):
    job_id = str(uuid4())
    jobs[job_id] = {
        "status": "needs_model_setup",
        "prompt": request.prompt,
        "message": "AI video model is not connected yet"
    }
    return {"job_id": job_id, **jobs[job_id]}

@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        return {"error": "Job not found"}
    return jobs[job_id]
