Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "          AyushTube Video & Audio Studio" -ForegroundColor Magenta
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting backend server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"
python main.py
