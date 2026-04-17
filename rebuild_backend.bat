@echo off
cd /d "%~dp0"
echo Rebuilding backend...
docker compose up -d --build backend
echo.
echo Backend rebuilt!
pause