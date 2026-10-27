
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from huggingface_hub import InferenceClient

app = FastAPI(title="AI Video Generator API")

VIDEO_DIR = Path("/tmp/generated_videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

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
    if not os.environ.get("HF_TOKEN"):
        raise HTTPException(
            status_code=500,
            detail="HF_TOKEN is missing in Render settings"
        )

    job_id = str(uuid.uuid4())
    output_file = VIDEO_DIR / f"{job_id}.mp4"

    jobs[job_id] = {"status": "processing"}

    try:
        client = InferenceClient(
            provider="fal-ai",
            api_key=os.environ["HF_TOKEN"],
            timeout=600
        )

        prompt = f"{request.style}: {request.prompt}"

        video_bytes = client.text_to_video(
            prompt=prompt,
            model="Wan-AI/Wan2.2-TI2V-5B"
        )

        output_file.write_bytes(video_bytes)

        jobs[job_id] = {
            "status": "completed",
            "download_url": f"/video/{job_id}"
        }

        return {"job_id": job_id, **jobs[job_id]}

    except Exception as e:
        jobs[job_id] = {
            "status": "failed",
            "message": str(e)[:1000]
        }
        raise HTTPException(status_code=502, detail=str(e)[:1000])


@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **jobs[job_id]}


@app.get("/video/{job_id}")
def download_video(job_id: str):
    output_file = VIDEO_DIR / f"{job_id}.mp4"

    if not output_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Video not found. Generate it first."
        )

    return FileResponse(
        path=output_file,
        media_type="video/mp4",
        filename="generated_video.mp4"
    )
