#!/usr/bin/env bash
# Creates .env with a random Grafana password and your Telegram settings.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -e .env ] && [ "${1:-}" != "--force" ]; then
  echo ".env already exists. Use --force to overwrite it (the old values are lost)." >&2
  exit 1
fi
echo "Telegram alerts: create a bot with @BotFather, send it a message and read the chat id from"
echo "https://api.telegram.org/bot<TOKEN>/getUpdates. Press Enter to skip and set it later in .env."
read -r -s -p "Telegram bot token: " token; echo
read -r -p "Telegram chat id: " chat
[ -n "$token" ] || token="not-configured"
[[ "$chat" =~ ^-?[0-9]+$ ]] || chat="0"
password="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)"
umask 077
cat >.env <<ENV
GRAFANA_ADMIN_PASSWORD=$password
TELEGRAM_BOT_TOKEN=$token
TELEGRAM_CHAT_ID=$chat
PROMETHEUS_RETENTION=30d
GRAFANA_PORT=3000
PROMETHEUS_PORT=9090
ALERTMANAGER_PORT=9093
ENV
echo ".env written. Grafana password: grep GRAFANA_ADMIN_PASSWORD .env"
