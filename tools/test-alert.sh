#!/usr/bin/env bash
# Sends a test alert through Alertmanager so you can see it arrive on Telegram.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec alertmanager amtool alert add alertname=TestAlert severity=warning host=manual \
  --annotation=summary="Test alert from dc-monitoring-stack" \
  --annotation=description="If you can read this on Telegram, notifications work." \
  --alertmanager.url=http://localhost:9093
echo "Sent. It reaches Telegram after the group wait (about 30 seconds)."
