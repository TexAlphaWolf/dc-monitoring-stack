"""End-to-end check of a running stack (used in CI, also handy after `docker compose up`).

    python tools/check_stack.py [--webhook http://127.0.0.1:8080] [--skip grafana,cadvisor,windows]

Checks, in order: every scrape job is up, every rule loads and evaluates, Prometheus sees
Alertmanager, Grafana has the datasource and all dashboards, a query goes through Grafana, and
alerts really travel Prometheus -> Alertmanager -> receiver. The last step needs the CI webhook
receiver (docker-compose.ci.yml). Standard library only.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

EXPECTED_DASHBOARDS = {"dc-overview", "dc-linux", "dc-windows", "dc-containers", "dc-endpoints"}
JOBS = {"prometheus", "alertmanager", "node", "cadvisor", "blackbox", "probe-http", "probe-tcp",
        "windows"}  # fmt: skip


def get(url: str, auth: str | None = None):
    request = urllib.request.Request(url)
    if auth:
        request.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read()
    return json.loads(body) if body[:1] in (b"[", b"{") else body.decode()


def post(url: str, payload, auth: str | None = None):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    request.add_header("Content-Type", "application/json")
    if auth:
        request.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read()
    return json.loads(body) if body[:1] in (b"[", b"{") else body.decode()


def wait_for(description: str, check, timeout: float = 180, pause: float = 5):
    deadline = time.monotonic() + timeout
    last: object = None
    while True:
        try:
            result = check()
            if result:
                print(f"ok    {description}")
                return result
            last = "condition not met yet"
        except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
            last = error
        if time.monotonic() > deadline:
            print(f"FAIL  {description}: {last}")
            sys.exit(1)
        time.sleep(pause)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
    parser.add_argument("--alertmanager", default="http://127.0.0.1:9093")
    parser.add_argument("--grafana", default="http://127.0.0.1:3000")
    parser.add_argument("--webhook", default="", help="CI webhook receiver, enables the alert test")
    parser.add_argument("--skip", default="", help="comma separated: grafana,cadvisor,windows")
    args = parser.parse_args()
    skip = {s for s in args.skip.split(",") if s}
    prom = args.prometheus

    wait_for("Prometheus is ready", lambda: "Ready" in get(f"{prom}/-/ready"))

    def jobs_up():
        targets = get(f"{prom}/api/v1/targets")["data"]["activeTargets"]
        state: dict[str, list[str]] = {}
        for target in targets:
            state.setdefault(target["labels"]["job"], []).append(target["health"])
        wanted = JOBS - skip
        missing = [j for j in wanted if j not in state or set(state[j]) != {"up"}]
        if missing:
            raise ValueError(f"not up yet: {sorted(missing)}")
        return True

    wait_for("every scrape job is up", jobs_up)

    def rules_ok():
        groups = get(f"{prom}/api/v1/rules")["data"]["groups"]
        rules = [r for g in groups for r in g["rules"]]
        bad = [r["name"] for r in rules if r["health"] != "ok"]
        if bad or len(rules) < 40:
            raise ValueError(f"{len(rules)} rules, unhealthy: {bad}")
        return True

    wait_for("all alert and recording rules load and evaluate", rules_ok)

    wait_for(
        "Prometheus is connected to Alertmanager",
        lambda: len(get(f"{prom}/api/v1/alertmanagers")["data"]["activeAlertmanagers"]) == 1,
    )

    def probes_succeed():
        query = urllib.parse.quote('count(probe_success{job="probe-http"} == 1)')
        result = get(f"{prom}/api/v1/query?query={query}")["data"]["result"]
        return result and float(result[0]["value"][1]) >= 3

    wait_for("the three monitoring endpoints answer to the HTTP probe", probes_succeed)

    if "grafana" not in skip:
        auth = f"admin:{os.environ['GRAFANA_ADMIN_PASSWORD']}"
        graf = args.grafana
        wait_for("Grafana is healthy", lambda: get(f"{graf}/api/health")["database"] == "ok")
        wait_for(
            "the Prometheus datasource is provisioned and healthy",
            lambda: get(f"{graf}/api/datasources/uid/prometheus/health", auth)["status"] == "OK",
        )

        def dashboards():
            found = {d["uid"] for d in get(f"{graf}/api/search?type=dash-db", auth)}
            if not EXPECTED_DASHBOARDS <= found:
                raise ValueError(f"missing: {sorted(EXPECTED_DASHBOARDS - found)}")
            return True

        wait_for("all five dashboards are provisioned", dashboards)

        def query_through_grafana():
            reply = post(
                f"{graf}/api/ds/query",
                {"from": "now-5m", "to": "now", "queries": [{
                    "refId": "A", "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "expr": "count(up)", "instant": True}]},
                auth,
            )  # fmt: skip
            return "error" not in reply["results"]["A"]

        wait_for("a query runs through Grafana", query_through_grafana)

    if args.webhook:
        hook = args.webhook
        wait_for(
            "the Watchdog alert travels Prometheus -> Alertmanager -> receiver",
            lambda: "Watchdog" in get(f"{hook}/names"),
            timeout=240,
        )
        post(f"{args.alertmanager}/api/v2/alerts", [{
            "labels": {"alertname": "CITestAlert", "severity": "warning"},
            "annotations": {"summary": "end-to-end test"}}])  # fmt: skip
        wait_for(
            "an alert posted to Alertmanager reaches the receiver",
            lambda: "CITestAlert" in get(f"{hook}/names"),
            timeout=120,
        )

    print("The stack works end to end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
