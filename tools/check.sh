#!/usr/bin/env bash
# Static checks of the whole configuration, without starting the stack. Needs only Docker:
# promtool and amtool come from the same images the stack uses. Also run in CI.
set -euo pipefail
cd "$(dirname "$0")/.."

prom_image="$(grep -oE 'prom/prometheus:[^ ]+' docker-compose.yml | head -1)"
am_image="$(grep -oE 'prom/alertmanager:[^ ]+' docker-compose.yml | head -1)"
promtool() { docker run --rm -v "$PWD/prometheus:/etc/prometheus:ro" --entrypoint promtool "$prom_image" "$@"; }
amtool() {
  docker run --rm -v "$PWD/alertmanager:/etc/alertmanager:ro" --entrypoint amtool "$am_image" "$@"
}

echo "== Prometheus configuration and rules ($prom_image)"
promtool check config /etc/prometheus/prometheus.yml
echo "== Alert rule unit tests"
for file in prometheus/tests/*.test.yml; do
  promtool test rules "/etc/prometheus/tests/$(basename "$file")"
done

echo "== Alertmanager configuration ($am_image)"
amtool check-config /etc/alertmanager/alertmanager.yml
route() { amtool config routes test --config.file=/etc/alertmanager/alertmanager.yml "$@"; }
expect() {
  local want="$1"; shift
  local got; got="$(route "$@")"
  [ "$got" = "$want" ] || { echo "routing: $* went to '$got', expected '$want'" >&2; exit 1; }
}
expect null alertname=Watchdog severity=none
expect telegram alertname=HostDown severity=critical
expect telegram alertname=HostHighCpu severity=warning
expect telegram alertname=HostRebooted severity=info
echo "routing ok"

echo "== Dashboards and repository consistency"
python3 -m unittest discover -s tests -v
echo "All static checks passed."
