"""Run every dashboard query against a live Prometheus.

    python tools/check_dashboards.py [--prometheus URL] [--require node,cadvisor,probes,windows]
                                     [--wait SECONDS]

A query that Prometheus rejects always fails. With --require, a query on metrics of a listed
group (node, windows, cadvisor, probes) must also return data, so a dashboard that silently
shows "No data" is caught. --wait keeps retrying while queries are still empty, because rates and
recording rules need a few minutes of samples on a freshly started stack. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DASHBOARDS = Path(__file__).resolve().parent.parent / "grafana" / "dashboards"
GROUPS = {
    "node": ("node_", "node:"),
    "windows": ("windows_", "windows:"),
    "cadvisor": ("container_",),
    "probes": ("probe_",),
}
# Metrics that legitimately have no series on many machines.
OPTIONAL = (
    "hwmon",
    "ALERTS",
    "ssl_earliest_cert_expiry",
    "http_status_code",
    "container_spec_memory_limit_bytes",  # only containers with a memory limit have it
)
SUBSTITUTIONS = {
    "$__rate_interval": "2m",
    "$__range": "1h",
    "$__interval": "1m",
    "$instance": ".*",
    "$name": ".*",
}
LABEL_VALUES = re.compile(r"^label_values\((?P<metric>.+),\s*(?P<label>\w+)\)$")


def api(base: str, path: str, **params) -> dict:
    url = f"{base}/api/v1/{path}?{urllib.parse.urlencode(params, doseq=True)}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def expand(expr: str) -> str:
    for key, value in SUBSTITUTIONS.items():
        expr = expr.replace(key, value)
    return expr


def queries(path: Path):
    board = json.loads(path.read_text(encoding="utf-8"))
    for variable in board.get("templating", {}).get("list", []):
        yield f"variable {variable['name']}", variable["definition"], True
    for panel in board["panels"]:
        for target in panel.get("targets", []):
            yield panel["title"], target["expr"], False


def run_once(base: str, prefixes: tuple[str, ...]) -> tuple[list[str], list[str], int]:
    """Check every query once; returns (rejected, empty, total) with printable messages."""
    rejected: list[str] = []
    empty: list[str] = []
    total = 0
    for path in sorted(DASHBOARDS.glob("*.json")):
        for title, expr, is_variable in queries(path):
            total += 1
            try:
                if is_variable:
                    match = LABEL_VALUES.match(expr)
                    if match is None:
                        raise ValueError(f"unsupported variable query: {expr}")
                    reply = api(
                        base, f"label/{match['label']}/values", **{"match[]": match["metric"]}
                    )
                    result = reply["data"]
                else:
                    reply = api(base, "query", query=expand(expr))
                    result = reply["data"]["result"]
            except Exception as error:  # noqa: BLE001 - report every failing query
                rejected.append(f"FAIL {path.name} / {title}: {error}\n     {expr}")
                continue
            needs_data = (
                prefixes
                and any(prefix in expr for prefix in prefixes)
                and not any(word in expr for word in OPTIONAL)
            )
            if needs_data and not result:
                empty.append(f"EMPTY {path.name} / {title}\n     {expr}")
    return rejected, empty, total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
    parser.add_argument(
        "--require", default="", help="comma separated: node,windows,cadvisor,probes"
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="seconds to keep retrying while required queries are still empty",
    )
    args = parser.parse_args()
    required = {g for g in args.require.split(",") if g}
    unknown = required - GROUPS.keys()
    if unknown:
        parser.error(f"unknown group(s): {', '.join(sorted(unknown))}")
    prefixes = tuple(p for g in required for p in GROUPS[g])

    deadline = time.monotonic() + args.wait
    while True:
        rejected, empty, total = run_once(args.prometheus, prefixes)
        # A rejected query never fixes itself; empty ones may once samples have accumulated.
        if rejected or not empty or time.monotonic() >= deadline:
            break
        print(f"{len(empty)} queries still empty, retrying in 15 s", flush=True)
        time.sleep(15)

    for message in (*rejected, *empty):
        print(message)
    failures = len(rejected) + len(empty)
    print(f"FAILED: {failures} of {total} queries" if failures else f"OK: {total} queries")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
