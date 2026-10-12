#!/usr/bin/env sh
# Stop CodeScope. Your data is kept. Add -v to also delete the database:  ./stop.sh -v
cd "$(dirname "$0")"
docker compose down "$@"
