#!/usr/bin/env sh
# Deploy CodeScope on a Linux server with Docker.
#
#   ./deploy.sh                      HTTP on port 8080 (put your own TLS proxy in front, or use only on a private network)
#   ./deploy.sh codescope.example.com   HTTPS with an automatic certificate (DNS must already point here; ports 80/443 open)
#
# It creates a PRODUCTION .env with fresh random secrets (only if one does not exist yet),
# then builds and starts everything. Re-running it later is safe: it keeps your existing .env and data.
set -eu
cd "$(dirname "$0")"

command -v docker >/dev/null 2>&1 || { echo "Docker is not installed. Get it at https://docs.docker.com/get-docker/"; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker is installed but not running (or you need sudo)."; exit 1; }

rand_hex() {
  if command -v openssl >/dev/null 2>&1; then openssl rand -hex "$1"
  else python3 -c "import secrets; print(secrets.token_hex($1))"; fi
}

DOMAIN_ARG="${1:-}"

if [ -f .env ] && grep -q '^APP_ENV=production' .env; then
  echo "Keeping your existing production .env"
  if [ -n "$DOMAIN_ARG" ]; then
    sed -i.bak "s|^DOMAIN=.*|DOMAIN=${DOMAIN_ARG}|" .env && rm -f .env.bak
    sed -i.bak "s|^APP_BIND=.*|APP_BIND=127.0.0.1|" .env && rm -f .env.bak
  fi
else
  if [ -f .env ]; then cp .env ".env.backup.$(date +%s)"; echo "Backed up the old .env"; fi
  if [ -n "$DOMAIN_ARG" ]; then BIND="127.0.0.1"; else BIND="0.0.0.0"; fi
  cat > .env <<EOF
APP_ENV=production
POSTGRES_USER=codescope
POSTGRES_PASSWORD=$(rand_hex 16)
POSTGRES_DB=codescope
JWT_SECRET=$(rand_hex 32)
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7
APP_BIND=${BIND}
APP_PORT=8080
CORS_ORIGINS=
DOMAIN=${DOMAIN_ARG}
EOF
  chmod 600 .env
  echo "Created a production .env with random secrets (keep it private and back it up)"
fi

DOMAIN_NOW="$(sed -n 's/^DOMAIN=//p' .env | head -1)"
if [ -n "$DOMAIN_NOW" ]; then PROFILE="--profile https"; else PROFILE=""; fi

# shellcheck disable=SC2086
docker compose $PROFILE up --build -d --wait || { echo; echo "Deployment failed. Last log lines:"; docker compose logs --tail=80; exit 1; }

echo
if [ -n "$DOMAIN_NOW" ]; then
  echo "CodeScope is live at https://${DOMAIN_NOW}"
else
  echo "CodeScope is running on port 8080 of this server (HTTP only)."
  echo "Add HTTPS before real use:  ./deploy.sh your.domain.com"
fi
echo "Backups:  docker compose exec -T postgres pg_dump -U codescope codescope | gzip > backup-\$(date +%F).sql.gz"
