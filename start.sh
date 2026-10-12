#!/usr/bin/env sh
# Start CodeScope (Linux / macOS). First run builds the images (a few minutes).
set -eu
cd "$(dirname "$0")"

command -v docker >/dev/null 2>&1 || { echo "Docker is not installed. Get it at https://docs.docker.com/get-docker/"; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker is installed but not running. Start it and try again."; exit 1; }

docker compose up --build -d --wait || { echo; echo "Start-up failed. Last log lines:"; docker compose logs --tail=60; exit 1; }

PORT="${APP_PORT:-8080}"
echo
echo "CodeScope is running:  http://localhost:${PORT}"
echo "Stop it with:          ./stop.sh"
