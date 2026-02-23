@echo off
:: Ensure we are working in the directory where this script is located
cd /d "%~dp0"

echo Pulling latest release...
docker compose pull

echo.
echo Latest release pulled!
pause