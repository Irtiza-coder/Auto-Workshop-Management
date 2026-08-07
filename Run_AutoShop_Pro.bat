@echo off
cd /d "d:\Workshop\workshop_figma"
start "AutoShop_Server" /b "d:\Workshop\venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
timeout /t 4 /nobreak >nul
start /wait msedge --app=http://127.0.0.1:8000/
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
