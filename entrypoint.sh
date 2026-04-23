#!/bin/bash
set -e

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting services via supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
