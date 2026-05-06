@echo off
Stop-Process -Name python -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1; cd "i:\AIGameDev\时光印记"; python app.py
pause
