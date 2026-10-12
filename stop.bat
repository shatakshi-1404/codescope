@echo off
cd /d "%~dp0"
docker compose down
echo CodeScope stopped. Your data is kept. To also delete the database run: docker compose down -v
pause
