"""Generate docs/alerts.md from the rule files (run: python tools/build_docs.py). Needs PyYAML."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TITLES = {
    "meta.yml": "Monitoring the monitoring",
    "linux.yml": "Linux hosts",
    "windows.yml": "Windows hosts",
    "containers.yml": "Containers",
    "probes.yml": "Endpoints",
}


def render() -> str:
    lines = [
        "# Alerts",
        "",
        "Generated from `prometheus/rules/*.yml` by `tools/build_docs.py`: do not edit by hand.",
        "Every alert has a unit test in `prometheus/tests/`. Severities: **critical** repeats",
        "every hour, **warning** every 4 hours, **info** once a day, **none** is the heartbeat",
        "and is never sent to a person.",
        "",
    ]
    for name, title in TITLES.items():
        data = yaml.safe_load((ROOT / "prometheus" / "rules" / name).read_text("utf-8"))
        alerts = [r for g in data["groups"] for r in g["rules"] if "alert" in r]
        lines += [f"## {title}", "", "| Alert | Severity | Fires when | For |", "|---|---|---|---|"]
        for rule in alerts:
            expr = " ".join(rule["expr"].split()).replace("|", "\\|")
            what = re.sub(r"\{\{.*?\}\}", "…", rule["annotations"]["description"])
            lines.append(
                f"| `{rule['alert']}` | {rule['labels']['severity']} | {what} "
                f"<br><sub>`{expr}`</sub> | {rule.get('for', '0m')} |"
            )
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "alerts.md").write_text(render(), encoding="utf-8")
    print("wrote docs/alerts.md")
