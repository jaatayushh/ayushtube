import os
import uuid
import asyncio
import json
import urllib.parse
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import downloader

app = FastAPI(
    title="AyushTube Downloader API",
    description="High Performance YouTube & Social Media Media Downloader",
    version="2.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class InfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    quality_id: str
    format_type: str = "video"
    title: str = ""

class PlaylistItem(BaseModel):
    id: str
    title: str
    url: str

class PlaylistDownloadRequest(BaseModel):
    playlist_title: str
    items: List[PlaylistItem]
    quality_id: str = "audio_mp3_320"
    format_type: str = "audio"

# Keep-Alive & Health Ping endpoints for UptimeRobot / Cron-Job
@app.get("/health")
@app.get("/ping")
@app.head("/health")
@app.head("/ping")
async def health_check():
    return JSONResponse(content={"status": "online", "app": "AyushTube", "active": True})

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>AyushTube backend running. Static UI initializing...</h1>")

@app.post("/api/info")
async def get_video_info(req: InfoRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")
    
    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(None, downloader.extract_video_info, url)
        return {"success": True, "data": info}
    except Exception as e:
        error_str = str(e)
        if "Private video" in error_str:
            detail = "This video is private and cannot be accessed."
        elif "Sign in to confirm your age" in error_str:
            detail = "This video is age-restricted and requires YouTube login."
        elif "Video unavailable" in error_str:
            detail = "Video is unavailable or has been removed."
        else:
            detail = f"Unable to fetch media: {error_str[:160]}"
        raise HTTPException(status_code=400, detail=detail)

@app.post("/api/download")
async def create_download(req: DownloadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Video URL is required.")

    task_id = str(uuid.uuid4())[:10]
    task = downloader.TaskState(task_id=task_id, url=url)
    
    with downloader.tasks_lock:
        downloader.tasks[task_id] = task

    downloader.start_download_thread(
        task_id=task_id,
        url=url,
        quality_id=req.quality_id,
        format_type=req.format_type,
        title=req.title
    )

    return {"success": True, "task_id": task_id}

@app.post("/api/playlist/download")
async def create_playlist_download(req: PlaylistDownloadRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="No playlist items selected.")

    task_id = str(uuid.uuid4())[:10]
    task = downloader.TaskState(task_id=task_id, url="")
    
    with downloader.tasks_lock:
        downloader.tasks[task_id] = task

    items_dicts = [item.dict() for item in req.items]
    
    import threading
    t = threading.Thread(
        target=downloader.start_playlist_download_thread,
        args=(task_id, items_dicts, req.quality_id, req.format_type, req.playlist_title),
        daemon=True
    )
    t.start()

    return {"success": True, "task_id": task_id}

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    task = downloader.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Download task not found.")
    return task.to_dict()

@app.get("/api/progress/{task_id}")
async def stream_progress(task_id: str):
    task = downloader.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Download task not found.")

    async def event_generator():
        while True:
            t = downloader.get_task(task_id)
            if not t:
                break
            data = t.to_dict()
            yield f"data: {json.dumps(data)}\n\n"
            
            if t.status in ["completed", "error"]:
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/file/{task_id}")
async def download_file(task_id: str):
    task = downloader.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Download task not found.")

    if task.status != "completed" or not task.filepath or not os.path.exists(task.filepath):
        raise HTTPException(status_code=400, detail="File is not ready or failed to generate.")

    filename = task.filename or f"media_{task_id}.mp4"
    safe_filename = urllib.parse.quote(filename.encode("utf-8"))

    return FileResponse(
        path=task.filepath,
        filename=filename,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"
        }
    )

if __name__ == "__main__":
    import uvicorn
    print("AyushTube Server starting at http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
