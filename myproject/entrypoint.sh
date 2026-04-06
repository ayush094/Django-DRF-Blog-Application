#!/bin/sh

set -e

echo "Starting entrypoint..."

# ---------------------------------------------------
# WAIT FOR POSTGRES
# ---------------------------------------------------
echo "Waiting for Postgres at db:5432 ..."
until nc -z db 5432; do
  sleep 2
done
echo "Postgres is READY!"

# ---------------------------------------------------
# WAIT FOR REDIS (OPTIONAL BUT SAFE)
# ---------------------------------------------------
if [ ! -z "$REDIS_HOST" ]; then
  echo "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT:-6379} ..."
  until nc -z ${REDIS_HOST} ${REDIS_PORT:-6379}; do
    sleep 2
  done
  echo "Redis is READY!"
fi

# ---------------------------------------------------
# ENSURE DJANGO CAN FIND PROJECT
# ---------------------------------------------------
export PYTHONPATH=/app

# ---------------------------------------------------
# APPLY MIGRATIONS (ONLY SAFE FOR WEB / CELERY)
# ---------------------------------------------------
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running Django migrations..."
  python manage.py migrate --noinput
  echo "Migrations completed!"
fi

echo "All dependencies are ready. Running command..."

# ---------------------------------------------------
# EXECUTE FINAL COMMAND
# ---------------------------------------------------
exec "$@"
