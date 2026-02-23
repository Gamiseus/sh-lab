@echo off
:: Ensure we are working in the directory where this script is located
cd /d "%~dp0"

echo Shutting down services...
docker compose down

echo.
echo Services stopped.
pause