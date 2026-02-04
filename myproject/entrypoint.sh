#!/bin/sh
set -e

echo "Starting entrypoint..."

# ---------- WAIT FOR POSTGRES ----------
if [ "$POSTGRES_HOST" != "" ]; then
  echo "Waiting for Postgres at $POSTGRES_HOST:$POSTGRES_PORT ..."

  until PGPASSWORD="$POSTGRES_PASSWORD" \
    psql -h "$POSTGRES_HOST" \
         -U "$POSTGRES_USER" \
         -d "$POSTGRES_DB" \
         -c '\q' >/dev/null 2>&1; do
    echo "Postgres is not ready yet. Retrying..."
    sleep 2
  done

  echo "Postgres is READY!"
fi

# ---------- WAIT FOR REDIS ----------
if [ "$REDIS_HOST" != "" ]; then
  echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT ..."

  until nc -z "$REDIS_HOST" "$REDIS_PORT"; do
    echo "Redis unavailable... retrying..."
    sleep 1
  done

  echo "Redis is READY!"
fi

echo "All dependencies are ready. Running command..."
exec "$@"
