#!/bin/sh
# docker compose for the production stack, always reading the repo-root .env.
#   ./deploy/prod.sh up -d --build
#   ./deploy/prod.sh logs -f api
#   ./deploy/prod.sh exec api python manage.py createsuperuser
ROOT=$(cd "$(dirname "$0")/.." && pwd)
exec docker compose --env-file "$ROOT/.env" -f "$ROOT/deploy/docker-compose.prod.yml" "$@"
