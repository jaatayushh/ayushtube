# AyushTube • Ultra High-Performance YouTube Media Downloader & Studio

A full-stack, ad-free web application to download YouTube videos and audio in all qualities up to **4K 60FPS** and **320kbps MP3** with real-time download progress tracking.

---

## ⚡ Features

- **Highest Resolutions**: True 4K Ultra HD (2160p), 2K (1440p), Full HD (1080p60), 720p HD, 480p, and 360p.
- **Audio Extraction**: Studio-grade MP3 (320 kbps & 192 kbps), original M4A (AAC), and Lossless WAV with embedded metadata.
- **FFmpeg v7.1 Multiplexing**: High-resolution video and audio streams are merged automatically with zero desynchronization.
- **Live Server-Sent Events (SSE)**: Real-time progress bar, speed (MB/s), downloaded / total size, and dynamic ETA counters.
- **Modern Cyber-Glass UI**: Dark mode with radiant ambient glows, frosted glass cards, and instant clipboard paste.
- **Shorts & Mobile Ready**: Supports standard videos, YouTube Shorts (`/shorts/`), and mobile URLs (`youtu.be`).
- **Download History**: Tracks your recent downloads directly inside your browser.

---

## 🚀 Quick Start

### 1. Launch with One Click
Double-click `run.bat` (or run `./run.ps1` in PowerShell).  
It will automatically launch the server and open the interface at **`http://127.0.0.1:8000`**.

### 2. Or Run via Command Line
```bash
python main.py
```
Open `http://127.0.0.1:8000` in your web browser.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Uvicorn, Python 3.13
- **Downloader Engine**: `yt-dlp` (Latest)
- **Audio/Video Processor**: `imageio-ffmpeg` (FFmpeg v7.1 binary)
- **Frontend**: Vanilla HTML5, CSS3 Glassmorphism, Modern JavaScript (ES6+), Server-Sent Events (SSE)
