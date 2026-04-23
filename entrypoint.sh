#!/bin/bash
set -e

echo "Initializing/Upgrading database..."
uv run python -m backend.init_db

echo "Starting services via supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
