import os
import re
import uuid
import time
import zipfile
import shutil
import threading
from typing import Dict, Any, Optional, List

try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"

# Serverless writable directory detection
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(".", os.W_OK):
    DOWNLOADS_DIR = "/tmp/downloads"
else:
    DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

try:
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
except Exception:
    DOWNLOADS_DIR = "/tmp"

class TaskState:
    def __init__(self, task_id: str, url: str):
        self.task_id = task_id
        self.url = url
        self.status = "queued"
        self.percent = 0.0
        self.speed = "0 KB/s"
        self.eta = "--:--"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.downloaded_str = "0 MB"
        self.total_str = "Unknown"
        self.filename = ""
        self.filepath = ""
        self.error_msg = ""
        self.created_at = time.time()
        self.title = ""
        self.is_playlist = False
        self.current_item = 0
        self.total_items = 0
        self.current_title = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "percent": round(self.percent, 1),
            "speed": self.speed,
            "eta": self.eta,
            "downloaded": self.downloaded_str,
            "total": self.total_str,
            "filename": self.filename,
            "title": self.title,
            "error": self.error_msg,
            "is_playlist": self.is_playlist,
            "current_item": self.current_item,
            "total_items": self.total_items,
            "current_title": self.current_title,
            "ready_for_download": self.status == "completed" and bool(self.filepath and os.path.exists(self.filepath))
        }

tasks: Dict[str, TaskState] = {}
tasks_lock = threading.Lock()

def get_task(task_id: str) -> Optional[TaskState]:
    with tasks_lock:
        return tasks.get(task_id)

def cleanup_old_files(max_age_seconds: int = 3600):
    now = time.time()
    try:
        for f in os.listdir(DOWNLOADS_DIR):
            file_path = os.path.join(DOWNLOADS_DIR, f)
            if os.path.isfile(file_path):
                if now - os.path.getmtime(file_path) > max_age_seconds:
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
            elif os.path.isdir(file_path):
                if now - os.path.getmtime(file_path) > max_age_seconds:
                    try:
                        shutil.rmtree(file_path, ignore_errors=True)
                    except Exception:
                        pass
    except Exception:
        pass

def format_bytes(b: int) -> str:
    if not b or b <= 0:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} PB"

def format_seconds(secs: Optional[int]) -> str:
    if secs is None or secs < 0:
        return "--:--"
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def is_playlist_url(url: str) -> bool:
    if "list=" in url and "watch?v=" not in url:
        return True
    if "/playlist?list=" in url:
        return True
    return False

def extract_playlist_info(url: str) -> Dict[str, Any]:
    import yt_dlp
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "ffmpeg_location": FFMPEG_PATH,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("Failed to retrieve playlist information.")

    entries = info.get("entries") or []
    items = []
    
    for idx, entry in enumerate(entries):
        if not entry:
            continue
        v_id = entry.get("id")
        v_title = entry.get("title") or f"Video {idx + 1}"
        v_duration = entry.get("duration") or 0
        v_url = entry.get("url") or f"https://www.youtube.com/watch?v={v_id}"
        thumbs = entry.get("thumbnails") or []
        t_url = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"

        items.append({
            "index": idx + 1,
            "id": v_id,
            "title": v_title,
            "duration": v_duration,
            "duration_str": format_seconds(v_duration),
            "url": v_url,
            "thumbnail": t_url
        })

    best_thumb = items[0]["thumbnail"] if items else ""

    return {
        "is_playlist": True,
        "id": info.get("id"),
        "title": info.get("title", "YouTube Playlist"),
        "uploader": info.get("uploader") or info.get("channel", "Unknown Channel"),
        "thumbnail": best_thumb,
        "total_count": len(items),
        "items": items,
        "webpage_url": info.get("webpage_url") or url
    }

def extract_video_info(url: str) -> Dict[str, Any]:
    import yt_dlp
    if is_playlist_url(url):
        return extract_playlist_info(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "ffmpeg_location": FFMPEG_PATH,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("Failed to retrieve video information.")

    if info.get("_type") == "playlist" and "entries" in info:
        return extract_playlist_info(url)

    formats = info.get("formats", [])
    video_resolutions = {}
    
    for f in formats:
        height = f.get("height")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        
        if height and vcodec != "none":
            fps = f.get("fps") or 30
            filesize = f.get("filesize") or f.get("filesize_approx") or 0
            
            if height not in video_resolutions or (filesize > video_resolutions[height].get("filesize", 0)):
                video_resolutions[height] = {
                    "height": height,
                    "fps": fps,
                    "ext": f.get("ext", "mp4"),
                    "filesize": filesize,
                    "format_id": f.get("format_id"),
                    "tbr": f.get("tbr") or 0
                }

    standard_heights = [
        (2160, "4K Ultra HD", "2160p"),
        (1440, "2K Quad HD", "1440p"),
        (1080, "Full HD", "1080p"),
        (720, "HD", "720p"),
        (480, "Standard Definition", "480p"),
        (360, "Low Definition", "360p"),
        (240, "Mobile", "240p")
    ]
    
    available_video_options = []
    for height_val, label, res_tag in standard_heights:
        matched_height = None
        for h in sorted(video_resolutions.keys(), reverse=True):
            if h >= height_val * 0.95 and h <= height_val * 1.05:
                matched_height = h
                break
        
        if matched_height:
            v_info = video_resolutions[matched_height]
            fps = v_info["fps"]
            fps_str = f" {fps}fps" if fps and fps > 30 else ""
            size_est = format_bytes(v_info["filesize"]) if v_info["filesize"] else "Auto"
            
            available_video_options.append({
                "type": "video",
                "quality_id": f"video_{height_val}",
                "resolution": res_tag,
                "label": f"{label} ({res_tag}{fps_str})",
                "height": height_val,
                "fps": fps,
                "format": "mp4",
                "size_estimate": size_est,
                "recommended": height_val == 1080 or (height_val == 720 and not any(o["height"] == 1080 for o in available_video_options))
            })

    if not available_video_options and video_resolutions:
        max_h = max(video_resolutions.keys())
        available_video_options.append({
            "type": "video",
            "quality_id": f"video_{max_h}",
            "resolution": f"{max_h}p",
            "label": f"Best Quality ({max_h}p)",
            "height": max_h,
            "fps": 30,
            "format": "mp4",
            "size_estimate": "Auto",
            "recommended": True
        })

    if not available_video_options:
        available_video_options.append({
            "type": "video",
            "quality_id": "video_best",
            "resolution": "HD",
            "label": "Original Video Stream",
            "height": 720,
            "fps": 30,
            "format": "mp4",
            "size_estimate": "Original",
            "recommended": True
        })

    available_audio_options = [
        {
            "type": "audio",
            "quality_id": "audio_mp3_320",
            "format": "mp3",
            "quality": "320 kbps",
            "label": "MP3 High Fidelity (320 kbps)",
            "description": "Studio Quality MP3 with album artwork",
            "recommended": True
        },
        {
            "type": "audio",
            "quality_id": "audio_mp3_192",
            "format": "mp3",
            "quality": "192 kbps",
            "label": "MP3 Standard (192 kbps)",
            "description": "Balanced size and quality",
            "recommended": False
        },
        {
            "type": "audio",
            "quality_id": "audio_m4a",
            "format": "m4a",
            "quality": "AAC Original",
            "label": "M4A Original Audio",
            "description": "Native AAC audio stream without re-encoding",
            "recommended": False
        },
        {
            "type": "audio",
            "quality_id": "audio_wav",
            "format": "wav",
            "quality": "Lossless WAV",
            "label": "WAV Lossless Audio",
            "description": "Uncompressed audio stream",
            "recommended": False
        }
    ]

    thumbnails = info.get("thumbnails", [])
    best_thumb = info.get("thumbnail")
    if thumbnails:
        best_thumb = sorted(thumbnails, key=lambda t: (t.get("width") or 0) * (t.get("height") or 0), reverse=True)[0].get("url") or best_thumb

    duration = info.get("duration") or 0
    duration_str = format_seconds(duration)

    return {
        "is_playlist": False,
        "id": info.get("id"),
        "title": info.get("title", "Unknown Title"),
        "uploader": info.get("uploader") or info.get("channel", "Unknown Creator"),
        "uploader_url": info.get("uploader_url") or info.get("channel_url", ""),
        "thumbnail": best_thumb,
        "duration": duration,
        "duration_str": duration_str,
        "view_count": f"{info.get('view_count', 0):,}" if info.get("view_count") else "N/A",
        "upload_date": info.get("upload_date") or "",
        "webpage_url": info.get("webpage_url") or url,
        "description": (info.get("description") or "")[:280] + ("..." if len(info.get("description") or "") > 280 else ""),
        "video_options": available_video_options,
        "audio_options": available_audio_options
    }

def start_download_thread(task_id: str, url: str, quality_id: str, format_type: str, title: str):
    import yt_dlp
    task = get_task(task_id)
    if not task:
        return

    cleanup_old_files()

    def progress_hook(d):
        t = get_task(task_id)
        if not t:
            return

        if d["status"] == "downloading":
            t.status = "downloading"
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            
            if total > 0:
                t.percent = (downloaded / total) * 100.0
                t.total_bytes = total
                t.total_str = format_bytes(total)
            else:
                raw_p = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    t.percent = float(raw_p)
                except Exception:
                    pass

            t.downloaded_bytes = downloaded
            t.downloaded_str = format_bytes(downloaded)

            speed = d.get("speed")
            if speed:
                t.speed = f"{format_bytes(int(speed))}/s"
            else:
                t.speed = d.get("_speed_str", "Calculating...")

            eta = d.get("eta")
            if eta is not None:
                t.eta = format_seconds(eta)
            else:
                t.eta = d.get("_eta_str", "--:--")

        elif d["status"] == "finished":
            t.status = "converting"
            t.percent = 99.0
            t.speed = "Finishing..."
            t.eta = "Moments"

    out_tmpl = os.path.join(DOWNLOADS_DIR, f"{task_id}_%(title).150s.%(ext)s")

    ydl_opts: Dict[str, Any] = {
        "outtmpl": out_tmpl,
        "ffmpeg_location": FFMPEG_PATH,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
        "writethumbnail": False,
        "overwrites": True
    }

    try:
        task.status = "downloading"
        task.title = title

        if format_type == "audio":
            if quality_id == "audio_m4a":
                ydl_opts.update({
                    "format": "bestaudio[ext=m4a]/bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "m4a",
                    }]
                })
            elif quality_id == "audio_wav":
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                    }]
                })
            else:
                bitrate = "320" if "320" in quality_id else "192"
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": bitrate,
                        },
                        {
                            "key": "FFmpegMetadata",
                            "add_metadata": True,
                        }
                    ]
                })
        else:
            if quality_id == "video_best":
                ydl_opts.update({
                    "format": "bestvideo+bestaudio/best",
                    "merge_output_format": "mp4"
                })
            else:
                match = re.search(r"video_(\d+)", quality_id)
                target_h = int(match.group(1)) if match else 1080
                ydl_opts.update({
                    "format": f"bestvideo[height<={target_h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={target_h}] circuit",
                    "format": f"bestvideo[height<={target_h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={target_h}]+bestaudio/best[height<={target_h}]/best",
                    "merge_output_format": "mp4"
                })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            matched_file = None
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(task_id):
                    matched_file = os.path.join(DOWNLOADS_DIR, f)
                    break

            if matched_file and os.path.exists(matched_file):
                task.filepath = matched_file
                base_name = os.path.basename(matched_file)
                clean_name = base_name[len(task_id) + 1:]
                task.filename = clean_name
                task.status = "completed"
                task.percent = 100.0
                task.speed = "Done"
                task.eta = "00:00"
            else:
                raise FileNotFoundError("Output file was not generated properly.")

    except Exception as e:
        task.status = "error"
        task.error_msg = str(e)

def start_playlist_download_thread(task_id: str, items: List[Dict[str, Any]], quality_id: str, format_type: str, playlist_title: str):
    import yt_dlp
    task = get_task(task_id)
    if not task:
        return

    cleanup_old_files()

    task.is_playlist = True
    task.total_items = len(items)
    task.title = playlist_title
    task.status = "downloading"

    playlist_temp_dir = os.path.join(DOWNLOADS_DIR, f"playlist_{task_id}")
    os.makedirs(playlist_temp_dir, exist_ok=True)
    downloaded_files = []

    try:
        for idx, item in enumerate(items):
            task.current_item = idx + 1
            task.current_title = item.get("title", f"Video {idx+1}")
            item_url = item.get("url")
            
            base_percent = (idx / len(items)) * 100.0
            task.percent = base_percent
            task.total_str = f"{len(items)} items"
            task.downloaded_str = f"Item {idx + 1} of {len(items)}"

            def item_progress_hook(d):
                t = get_task(task_id)
                if not t:
                    return
                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes") or 0
                    item_p = (downloaded / total) if total > 0 else 0
                    t.percent = base_percent + (item_p * (100.0 / len(items)))
                    speed = d.get("speed")
                    t.speed = f"{format_bytes(int(speed))}/s" if speed else "Downloading..."
                    t.eta = format_seconds(d.get("eta"))

            out_tmpl = os.path.join(playlist_temp_dir, f"{idx+1:02d}_%(title).100s.%(ext)s")
            ydl_opts: Dict[str, Any] = {
                "outtmpl": out_tmpl,
                "ffmpeg_location": FFMPEG_PATH,
                "progress_hooks": [item_progress_hook],
                "quiet": True,
                "no_warnings": True,
                "windowsfilenames": True,
                "overwrites": True
            }

            if format_type == "audio":
                bitrate = "320" if "320" in quality_id else "192"
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": bitrate,
                        },
                        {
                            "key": "FFmpegMetadata",
                            "add_metadata": True,
                        }
                    ]
                })
            else:
                match = re.search(r"video_(\d+)", quality_id)
                target_h = int(match.group(1)) if match else 720
                ydl_opts.update({
                    "format": f"bestvideo[height<={target_h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={target_h}]+bestaudio/best[height<={target_h}]/best",
                    "merge_output_format": "mp4"
                })

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(item_url, download=True)
            except Exception as item_err:
                print(f"Skipping failed item {item_url}: {item_err}")
                continue

        for root, _, files in os.walk(playlist_temp_dir):
            for f in files:
                downloaded_files.append(os.path.join(root, f))

        if not downloaded_files:
            raise RuntimeError("No files were successfully downloaded from the playlist.")

        task.status = "compressing"
        task.speed = "Packaging ZIP..."
        task.eta = "Moments"
        task.percent = 98.0

        clean_p_title = re.sub(r'[\\/*?:"<>|]', "", playlist_title)[:50].strip() or "Playlist"
        zip_filename = f"{clean_p_title}.zip"
        zip_filepath = os.path.join(DOWNLOADS_DIR, f"{task_id}_{zip_filename}")

        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_p in downloaded_files:
                arcname = os.path.basename(file_p)
                zipf.write(file_p, arcname)

        shutil.rmtree(playlist_temp_dir, ignore_errors=True)

        task.filepath = zip_filepath
        task.filename = zip_filename
        task.status = "completed"
        task.percent = 100.0
        task.speed = "Done"
        task.eta = "00:00"

    except Exception as e:
        task.status = "error"
        task.error_msg = str(e)
        shutil.rmtree(playlist_temp_dir, ignore_errors=True)
