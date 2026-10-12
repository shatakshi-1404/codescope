@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker is not installed. Install Docker Desktop from https://www.docker.com/products/docker-desktop
  pause
  exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop is not running. Start it, wait until it says "running", then run this again.
  pause
  exit /b 1
)

echo Building and starting CodeScope. The first run takes a few minutes...
docker compose up --build -d --wait
if errorlevel 1 (
  echo.
  echo Start-up failed. Last log lines:
  docker compose logs --tail=60
  echo.
  echo If you see "port is already allocated", edit .env and change APP_PORT, then run this again.
  pause
  exit /b 1
)

echo.
echo CodeScope is running at http://localhost:8080
start "" http://localhost:8080
endlocal
