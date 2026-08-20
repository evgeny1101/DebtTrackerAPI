#!/bin/sh
# Reload nginx inside the container after certificate renewal.
# Run from the project root (where docker-compose.yml lives).
#
# Hook into your renewal tool:
#   certbot renew --deploy-hook "$(pwd)/reload-nginx.sh"
#   acme.sh --renew ... --reloadcmd "$(pwd)/reload-nginx.sh"
set -e

cd "$(dirname "$0")"

if ! docker compose ps --services --status running | grep -q '^nginx$'; then
    echo "nginx container not running (profile 'proxy' not active?) — nothing to reload" >&2
    exit 1
fi

docker compose exec -T nginx nginx -s reload
echo "nginx reloaded"