@echo off
:: Ensure we are working in the directory where this script is located
cd /d "%~dp0"

echo Starting up services...
docker compose up -d

echo Cleaning up old unused images...
docker image prune -f

echo.
echo Services started!
pause