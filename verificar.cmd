@echo off
setlocal
cd /d "%~dp0"
echo ===== CONTAINERS =====
docker compose ps -a
echo.
echo ===== ULTIMOS LOGS WEB =====
docker compose logs web --tail=80
pause
