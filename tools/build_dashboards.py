"""Generate the Grafana dashboards in grafana/dashboards/ (run: python tools/build_dashboards.py).

Every PromQL expression is also checked against a live Prometheus by tools/check_dashboards.py.
"""

from __future__ import annotations

import json
from pathlib import Path

DS = {"type": "prometheus", "uid": "prometheus"}
OUT = Path(__file__).resolve().parent.parent / "grafana" / "dashboards"

LINKS = [
    {"title": "Overview", "type": "link", "url": "/d/dc-overview", "icon": "dashboard"},
    {"title": "Linux hosts", "type": "link", "url": "/d/dc-linux", "icon": "dashboard"},
    {"title": "Windows hosts", "type": "link", "url": "/d/dc-windows", "icon": "dashboard"},
    {"title": "Containers", "type": "link", "url": "/d/dc-containers", "icon": "dashboard"},
    {"title": "Endpoints", "type": "link", "url": "/d/dc-endpoints", "icon": "dashboard"},
]


class Board:
    def __init__(self, uid: str, title: str, tags: list[str], variables: list[dict] | None = None):
        self.uid, self.title, self.tags = uid, title, tags
        self.variables = variables or []
        self.panels: list[dict] = []
        self._id = 0

    def _base(self, kind, title, x, y, w, h, targets, unit, extra_defaults=None, **extra):
        self._id += 1
        defaults = {"unit": unit}
        defaults.update(extra_defaults or {})
        panel = {
            "id": self._id,
            "type": kind,
            "title": title,
            "datasource": DS,
            "gridPos": {"x": x, "y": y, "w": w, "h": h},
            "targets": [
                {"datasource": DS, "refId": chr(65 + i), **t} for i, t in enumerate(targets)
            ],
            "fieldConfig": {"defaults": defaults, "overrides": []},
            "options": {},
        }
        panel.update(extra)
        self.panels.append(panel)
        return panel

    def stat(self, title, x, y, w, h, expr, unit="short", thresholds=None, color="blue", text=None):
        defaults = {"color": {"mode": "fixed", "fixedColor": color}}
        if thresholds:
            defaults = {
                "color": {"mode": "thresholds"},
                "thresholds": {"mode": "absolute", "steps": thresholds},
            }
        if text:
            defaults["mappings"] = [
                {"type": "special", "options": {"match": "null", "result": {"text": text}}}
            ]
        return self._base(
            "stat", title, x, y, w, h, [{"expr": expr, "instant": True}], unit, defaults,
            options={"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                     "colorMode": "value", "graphMode": "none", "textMode": "value"},
        )  # fmt: skip

    def series(
        self,
        title,
        x,
        y,
        w,
        h,
        exprs,
        unit="short",
        stack=False,
        minimum=None,
        maximum=None,
        legend_calcs=None,
    ):
        targets = [{"expr": e, "legendFormat": legend, "range": True} for e, legend in exprs]
        defaults = {
            "custom": {
                "drawStyle": "line",
                "lineWidth": 1,
                "fillOpacity": 25 if stack else 8,
                "showPoints": "never",
                "spanNulls": False,
                "stacking": {"mode": "normal" if stack else "none"},
            }
        }
        if minimum is not None:
            defaults["min"] = minimum
        if maximum is not None:
            defaults["max"] = maximum
        return self._base(
            "timeseries", title, x, y, w, h, targets, unit, defaults,
            options={"legend": {"displayMode": "table" if legend_calcs else "list",
                                "placement": "bottom", "calcs": legend_calcs or []},
                     "tooltip": {"mode": "multi", "sort": "desc"}},
        )  # fmt: skip

    def bars(
        self,
        title,
        x,
        y,
        w,
        h,
        expr,
        legend,
        unit="percentunit",
        maximum=1,
        thresholds=None,
        no_value=None,
    ):
        steps = thresholds or [
            {"color": "green", "value": None},
            {"color": "orange", "value": 0.8},
            {"color": "red", "value": 0.92},
        ]
        return self._base(
            "bargauge", title, x, y, w, h,
            [{"expr": expr, "legendFormat": legend, "instant": True}], unit,
            {"min": 0, "max": maximum, "color": {"mode": "thresholds"},
             "thresholds": {"mode": "absolute", "steps": steps},
             **({"noValue": no_value} if no_value else {})},
            options={"displayMode": "gradient", "orientation": "horizontal",
                     "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}},
        )  # fmt: skip

    def table(
        self, title, x, y, w, h, queries, hide=(), rename=None, overrides=None, no_value=None
    ):
        """`queries` is a list of (expr, refId-suffix) merged by the shared labels."""
        targets = [{"expr": e, "instant": True, "format": "table"} for e in queries]
        transforms = [{"id": "merge", "options": {}}]
        transforms.append({"id": "organize", "options": {
            "excludeByName": {name: True for name in ("Time", "__name__", *hide)},
            "renameByName": rename or {}}})  # fmt: skip
        panel = self._base(
            "table", title, x, y, w, h, targets, "short", None,
            transformations=transforms,
            options={"showHeader": True, "cellHeight": "sm"},
        )  # fmt: skip
        panel["fieldConfig"] = {
            "defaults": {"noValue": no_value} if no_value else {},
            "overrides": overrides or [],
        }
        return panel

    def build(self) -> dict:
        return {
            "uid": self.uid, "title": self.title, "tags": ["monitoring", *self.tags],
            "timezone": "browser", "schemaVersion": 39, "version": 1, "refresh": "30s",
            "time": {"from": "now-6h", "to": "now"}, "editable": True, "graphTooltip": 1,
            "links": [link for link in LINKS if link["url"] != f"/d/{self.uid}"],
            "templating": {"list": self.variables}, "panels": self.panels,
        }  # fmt: skip

    def write(self, name: str) -> None:
        path = OUT / name
        path.write_text(json.dumps(self.build(), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")


def variable(name, query, label, include_all=True):
    return {
        "name": name, "label": label, "type": "query", "datasource": DS,
        "query": query, "definition": query,
        "refresh": 2, "sort": 1, "multi": True, "includeAll": include_all,
        "allValue": ".*", "current": {"selected": True, "text": "All", "value": "$__all"},
    }  # fmt: skip


OK_RED = [{"color": "red", "value": None}, {"color": "green", "value": 1}]
GREEN_ORANGE_RED = [{"color": "green", "value": None}, {"color": "orange", "value": 0.8},
                    {"color": "red", "value": 0.92}]  # fmt: skip
ZERO_GREEN = [{"color": "green", "value": None}, {"color": "red", "value": 1}]
ZERO_ORANGE = [{"color": "green", "value": None}, {"color": "orange", "value": 1}]


def overview() -> Board:
    b = Board("dc-overview", "Overview", ["overview"])
    b.stat(
        "Hosts up",
        0,
        0,
        4,
        4,
        'sum(up{job=~"node|windows"} == 1) or vector(0)',
        thresholds=[{"color": "red", "value": None}, {"color": "green", "value": 1}],
    )
    b.stat(
        "Hosts down",
        4,
        0,
        4,
        4,
        'count(up{job=~"node|windows"} == 0) or vector(0)',
        thresholds=ZERO_GREEN,
    )
    b.stat(
        "Alerts firing",
        8,
        0,
        4,
        4,
        'count(ALERTS{alertstate="firing", alertname!="Watchdog"}) or vector(0)',
        thresholds=ZERO_ORANGE,
    )
    b.stat("Containers", 12, 0, 4, 4, 'count(container_last_seen{name!=""}) or vector(0)')
    b.stat("Endpoints up", 16, 0, 4, 4,
           '(sum(probe_success) / count(probe_success)) or vector(0)', unit="percentunit",
           thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 0.99},
                       {"color": "green", "value": 1}])  # fmt: skip
    b.stat("Targets down", 20, 0, 4, 4, "count(up == 0) or vector(0)", thresholds=ZERO_ORANGE)
    b.table(
        "Firing alerts",
        0,
        4,
        24,
        7,
        ['ALERTS{alertstate="firing", alertname!="Watchdog"}'],
        no_value="No alerts firing",
        hide=("alertstate", "Value", "site", "job"),
        rename={
            "alertname": "Alert",
            "severity": "Severity",
            "host": "Host",
            "instance": "Instance",
        },
    )
    b.series(
        "CPU busy",
        0,
        11,
        12,
        8,
        [("node:cpu_busy:ratio", "{{host}}"), ("windows:cpu_busy:ratio", "{{host}}")],
        unit="percentunit",
        minimum=0,
        maximum=1,
    )
    b.series("Memory available", 12, 11, 12, 8,
             [("node:memory_available:ratio", "{{host}}"),
              ("windows:memory_available:ratio", "{{host}}")],
             unit="percentunit", minimum=0, maximum=1)  # fmt: skip
    b.bars(
        "Fullest filesystems (Linux)",
        0,
        19,
        12,
        8,
        "topk(8, 1 - node:filesystem_avail:ratio)",
        "{{host}} {{mountpoint}}",
    )
    b.bars(
        "Fullest drives (Windows)",
        12,
        19,
        12,
        8,
        "topk(8, 1 - windows:disk_free:ratio)",
        "{{host}} {{volume}}",
    )
    b.table(
        "Scrape targets",
        0,
        27,
        24,
        8,
        ["up"],
        hide=("site", "Value #A"),
        rename={"Value": "Up", "job": "Job", "instance": "Instance", "host": "Host"},
    )
    return b


def linux() -> Board:
    inst = variable("instance", "label_values(node_uname_info, instance)", "Host")
    b = Board("dc-linux", "Linux hosts", ["linux", "node_exporter"], [inst])
    f = 'instance=~"$instance"'
    b.stat("Uptime", 0, 0, 4, 4, f"min(time() - node_boot_time_seconds{{{f}}})", unit="s")
    b.stat("CPU cores", 4, 0, 4, 4, f'count(node_cpu_seconds_total{{{f}, mode="idle"}})')
    b.stat(
        "CPU busy",
        8,
        0,
        4,
        4,
        f"avg(node:cpu_busy:ratio{{{f}}})",
        unit="percentunit",
        thresholds=GREEN_ORANGE_RED,
    )
    b.stat(
        "Memory used",
        12,
        0,
        4,
        4,
        f"1 - avg(node:memory_available:ratio{{{f}}})",
        unit="percentunit",
        thresholds=GREEN_ORANGE_RED,
    )
    b.stat("Load (15m) per core", 16, 0, 4, 4,
           f'avg(node_load15{{{f}}}) / count(node_cpu_seconds_total{{{f}, mode="idle"}})',
           thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1},
                       {"color": "red", "value": 2}])  # fmt: skip
    b.stat(
        "Open alerts",
        20,
        0,
        4,
        4,
        f'count(ALERTS{{alertstate="firing", {f}}}) or vector(0)',
        thresholds=ZERO_ORANGE,
    )
    b.series("CPU by mode", 0, 4, 12, 8,
             [(f'sum by (mode) (rate(node_cpu_seconds_total{{{f}, mode!="idle"}}[$__rate_interval]))'
               f' / scalar(count(node_cpu_seconds_total{{{f}, mode="idle"}}))', "{{mode}}")],
             unit="percentunit", stack=True, minimum=0, maximum=1)  # fmt: skip
    b.series("Memory", 12, 4, 12, 8,
             [(f'node_memory_MemTotal_bytes{{{f}}} - node_memory_MemAvailable_bytes{{{f}}}',
               "used {{host}}"),
              (f'node_memory_MemAvailable_bytes{{{f}}} - node_memory_MemFree_bytes{{{f}}}',
               "cache {{host}}"),
              (f'node_memory_MemFree_bytes{{{f}}}', "free {{host}}")],
             unit="bytes", stack=True, minimum=0)  # fmt: skip
    b.series(
        "Load average",
        0,
        12,
        8,
        8,
        [
            (f"node_load1{{{f}}}", "1m {{host}}"),
            (f"node_load5{{{f}}}", "5m {{host}}"),
            (f"node_load15{{{f}}}", "15m {{host}}"),
        ],
        minimum=0,
    )
    b.series(
        "Swap used",
        8,
        12,
        8,
        8,
        [(f"node_memory_SwapTotal_bytes{{{f}}} - node_memory_SwapFree_bytes{{{f}}}", "{{host}}")],
        unit="bytes",
        minimum=0,
    )
    b.series(
        "Temperatures",
        16,
        12,
        8,
        8,
        [(f"node_hwmon_temp_celsius{{{f}}}", "{{host}} {{chip}} {{sensor}}")],
        unit="celsius",
    )
    b.bars(
        "Filesystem usage",
        0,
        20,
        12,
        8,
        f"1 - node:filesystem_avail:ratio{{{f}}}",
        "{{host}} {{mountpoint}}",
    )
    b.series("Disk throughput", 12, 20, 12, 8,
             [(f'sum by (host, device) (rate(node_disk_read_bytes_total{{{f}, device!~"loop.*|ram.*|dm-.*"}}'
               f'[$__rate_interval]))', "read {{host}} {{device}}"),
              (f'sum by (host, device) (rate(node_disk_written_bytes_total{{{f}, device!~"loop.*|ram.*|dm-.*"}}'
               f'[$__rate_interval]))', "write {{host}} {{device}}")], unit="Bps")  # fmt: skip
    b.series("Network traffic", 0, 28, 12, 8,
             [(f'sum by (host, device) (rate(node_network_receive_bytes_total{{{f}, device!~"lo|veth.*|docker.*|br-.*"}}'
               f'[$__rate_interval]))', "in {{host}} {{device}}"),
              (f'sum by (host, device) (rate(node_network_transmit_bytes_total{{{f}, device!~"lo|veth.*|docker.*|br-.*"}}'
               f'[$__rate_interval]))', "out {{host}} {{device}}")], unit="Bps")  # fmt: skip
    b.series("Network errors and drops", 12, 28, 12, 8,
             [(f'sum by (host, device) (rate(node_network_receive_errs_total{{{f}, device!~"lo|veth.*|docker.*|br-.*"}}'
               f'[$__rate_interval]) + rate(node_network_transmit_errs_total{{{f}, device!~"lo|veth.*|docker.*|br-.*"}}'
               f'[$__rate_interval]))', "errors {{host}} {{device}}"),
              (f'sum by (host, device) (rate(node_network_receive_drop_total{{{f}, device!~"lo|veth.*|docker.*|br-.*"}}'
               f'[$__rate_interval]))', "rx drops {{host}} {{device}}")], unit="pps", minimum=0)  # fmt: skip
    return b


def windows() -> Board:
    inst = variable(
        "instance", "label_values(windows_memory_physical_total_bytes, instance)", "Host"
    )
    b = Board("dc-windows", "Windows hosts", ["windows", "windows_exporter"], [inst])
    f = 'instance=~"$instance"'
    b.stat(
        "CPU busy",
        0,
        0,
        6,
        4,
        f"avg(windows:cpu_busy:ratio{{{f}}})",
        unit="percentunit",
        thresholds=GREEN_ORANGE_RED,
    )
    b.stat(
        "Memory used",
        6,
        0,
        6,
        4,
        f"1 - avg(windows:memory_available:ratio{{{f}}})",
        unit="percentunit",
        thresholds=GREEN_ORANGE_RED,
    )
    b.stat(
        "Physical memory",
        12,
        0,
        6,
        4,
        f"sum(windows_memory_physical_total_bytes{{{f}}})",
        unit="bytes",
    )
    b.stat(
        "Logical processors",
        18,
        0,
        6,
        4,
        f"count(count by (instance, core) (windows_cpu_time_total{{{f}}}))",
    )
    b.series(
        "CPU busy",
        0,
        4,
        12,
        8,
        [(f"windows:cpu_busy:ratio{{{f}}}", "{{host}}")],
        unit="percentunit",
        minimum=0,
        maximum=1,
    )
    b.series("Memory", 12, 4, 12, 8,
             [(f'windows_memory_physical_total_bytes{{{f}}} - windows_memory_available_bytes{{{f}}}',
               "used {{host}}"),
              (f'windows_memory_available_bytes{{{f}}}', "available {{host}}")],
             unit="bytes", stack=True, minimum=0)  # fmt: skip
    b.bars(
        "Drive usage", 0, 12, 12, 8, f"1 - windows:disk_free:ratio{{{f}}}", "{{host}} {{volume}}"
    )
    b.series("Free space per drive", 12, 12, 12, 8,
             [(f'windows_logical_disk_free_bytes{{{f}, volume!~"HarddiskVolume.*"}}',
               "{{host}} {{volume}}")], unit="bytes", minimum=0)  # fmt: skip
    b.series("Disk throughput", 0, 20, 12, 8,
             [(f'sum by (host, volume) (rate(windows_logical_disk_read_bytes_total{{{f}, volume!~"HarddiskVolume.*"}}'
               f'[$__rate_interval]))', "read {{host}} {{volume}}"),
              (f'sum by (host, volume) (rate(windows_logical_disk_write_bytes_total{{{f}, volume!~"HarddiskVolume.*"}}'
               f'[$__rate_interval]))', "write {{host}} {{volume}}")], unit="Bps")  # fmt: skip
    b.series("Network traffic", 12, 20, 12, 8,
             [(f'sum by (host) (rate(windows_net_bytes_received_total{{{f}}}[$__rate_interval]))',
               "in {{host}}"),
              (f'sum by (host) (rate(windows_net_bytes_sent_total{{{f}}}[$__rate_interval]))',
               "out {{host}}")], unit="Bps")  # fmt: skip
    return b


def containers() -> Board:
    name = variable("name", 'label_values(container_last_seen{name!=""}, name)', "Container")
    b = Board("dc-containers", "Containers", ["docker", "cadvisor"], [name])
    f = 'name=~"$name", name!=""'
    b.stat("Containers", 0, 0, 6, 4, f"count(container_last_seen{{{f}}})")
    b.stat(
        "CPU (all selected)",
        6,
        0,
        6,
        4,
        f"sum(rate(container_cpu_usage_seconds_total{{{f}}}[$__rate_interval]))",
        unit="short",
        color="blue",
    )  # cores
    b.stat(
        "Memory (all selected)",
        12,
        0,
        6,
        4,
        f"sum(container_memory_working_set_bytes{{{f}}})",
        unit="bytes",
        color="blue",
    )
    b.stat("Restarts in range", 18, 0, 6, 4,
           f'sum(changes(container_start_time_seconds{{{f}}}[$__range])) or vector(0)',
           thresholds=ZERO_ORANGE)  # fmt: skip
    b.series(
        "CPU (cores)",
        0,
        4,
        12,
        8,
        [
            (
                f"sum by (name) (rate(container_cpu_usage_seconds_total{{{f}}}[$__rate_interval]))",
                "{{name}}",
            )
        ],
        unit="short",
        minimum=0,
        legend_calcs=["mean", "max"],
    )
    b.series(
        "Memory (working set)",
        12,
        4,
        12,
        8,
        [(f"sum by (name) (container_memory_working_set_bytes{{{f}}})", "{{name}}")],
        unit="bytes",
        minimum=0,
        legend_calcs=["mean", "max"],
    )
    b.bars("Memory against limit", 0, 12, 12, 8,
           f'container_memory_working_set_bytes{{{f}}} / (container_spec_memory_limit_bytes{{{f}}} > 0)',
           "{{name}}", no_value="No container has a memory limit")  # fmt: skip
    b.series("Network in / out", 12, 12, 12, 8,
             [(f'sum by (name) (rate(container_network_receive_bytes_total{{{f}}}[$__rate_interval]))',
               "in {{name}}"),
              (f'sum by (name) (rate(container_network_transmit_bytes_total{{{f}}}[$__rate_interval]))',
               "out {{name}}")], unit="Bps", minimum=0)  # fmt: skip
    b.table("Container state", 0, 20, 24, 8,
            [f'time() - container_start_time_seconds{{{f}}}'],
            hide=("id", "image", "instance", "job", "site", "cpu"),
            rename={"name": "Container", "Value": "Running for"},
            overrides=[{"matcher": {"id": "byName", "options": "Running for"},
                        "properties": [{"id": "unit", "value": "s"}]}])  # fmt: skip
    return b


def endpoints() -> Board:
    b = Board("dc-endpoints", "Endpoints", ["blackbox", "probes"])
    b.stat(
        "Probes up",
        0,
        0,
        6,
        4,
        "sum(probe_success) or vector(0)",
        thresholds=[{"color": "red", "value": None}, {"color": "green", "value": 1}],
    )
    b.stat(
        "Probes failing",
        6,
        0,
        6,
        4,
        "count(probe_success == 0) or vector(0)",
        thresholds=ZERO_GREEN,
    )
    b.stat("Slowest answer", 12, 0, 6, 4, 'max(probe_duration_seconds{job="probe-http"})', unit="s")
    b.stat("Next certificate expiry", 18, 0, 6, 4,
           'min(probe_ssl_earliest_cert_expiry - time()) > 0', unit="s", text="no TLS probes",
           thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 7 * 86400},
                       {"color": "green", "value": 30 * 86400}])  # fmt: skip
    b.table(
        "Probe status",
        0,
        4,
        24,
        9,
        [
            "probe_success",
            "probe_duration_seconds",
            "probe_http_status_code",
            "probe_ssl_earliest_cert_expiry - time()",
        ],
        hide=("site", "job"),
        rename={"instance": "Target", "service": "Service"},
    )
    b.series(
        "Probe duration",
        0,
        13,
        12,
        8,
        [("probe_duration_seconds", "{{instance}}")],
        unit="s",
        minimum=0,
        legend_calcs=["mean", "max"],
    )
    b.series("Availability", 12, 13, 12, 8,
             [('avg_over_time(probe_success[5m])', "{{instance}}")], unit="percentunit",
             minimum=0, maximum=1)  # fmt: skip
    b.bars("Availability over the selected range", 0, 21, 12, 8,
           'avg_over_time(probe_success[$__range])', "{{instance}}",
           thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 0.95},
                       {"color": "green", "value": 0.999}])  # fmt: skip
    b.bars("Days until certificate expiry", 12, 21, 12, 8,
           '(probe_ssl_earliest_cert_expiry - time()) / 86400 > 0', "{{instance}}", unit="d",
           maximum=90,
           thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 14},
                       {"color": "green", "value": 30}])  # fmt: skip
    return b


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    overview().write("overview.json")
    linux().write("linux-hosts.json")
    windows().write("windows-hosts.json")
    containers().write("containers.json")
    endpoints().write("endpoints.json")
