
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from magic_hour import Client

app = FastAPI(title="AI Video Generator API")

VIDEO_DIR = Path("/tmp/generated_videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

jobs = {}


class VideoRequest(BaseModel):
    prompt: str
    duration: int = 5
    style: str = "3D animation"


@app.get("/")
def home():
    return {"message": "AI Video Generator API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate_video(request: VideoRequest):
    api_key = os.environ.get("MAGIC_HOUR_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="MAGIC_HOUR_API_KEY is missing"
        )

    if not request.prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Prompt cannot be empty"
        )

    job_id = str(uuid.uuid4())
    job_dir = VIDEO_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    jobs[job_id] = {"status": "processing"}

    try:
        client = Client(token=api_key)

        result = client.v1.text_to_video.generate(
            name=f"Video {job_id[:8]}",
            end_seconds=5,
            aspect_ratio="16:9",
            style={
                "prompt": f"{request.style}: {request.prompt}"
            },
            model="ltx-2.5",
            resolution="480p",
            wait_for_completion=True,
            download_outputs=True,
            download_directory=str(job_dir)
        )

        if result.status != "complete":
            error = getattr(result, "error", None)
            message = getattr(error, "message", "Generation failed")
            jobs[job_id] = {
                "status": "failed",
                "message": str(message)
            }
            raise HTTPException(status_code=502, detail=str(message))

        files = list(job_dir.rglob("*.mp4"))

        if not files:
            raise RuntimeError(
                "Generation completed but no MP4 was downloaded"
            )

        video_path = files[0]

        jobs[job_id] = {
            "status": "completed",
            "download_url": f"/video/{job_id}",
            "credits_charged": getattr(
                result, "credits_charged", None
            )
        }

        return {"job_id": job_id, **jobs[job_id]}

    except HTTPException:
        raise
    except Exception as exc:
        jobs[job_id] = {
            "status": "failed",
            "message": str(exc)[:500]
        }
        raise HTTPException(
            status_code=502,
            detail=str(exc)[:500]
        )


@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"job_id": job_id, **jobs[job_id]}


@app.get("/video/{job_id}")
def download_video(job_id: str):
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        raise HTTPException(
            status_code=404,
            detail="Completed video not found"
        )

    files = list((VIDEO_DIR / job_id).rglob("*.mp4"))

    if not files:
        raise HTTPException(
            status_code=404,
            detail="Video file is no longer available"
        )

    return FileResponse(
        path=files[0],
        media_type="video/mp4",
        filename="generated_video.mp4"
    )
