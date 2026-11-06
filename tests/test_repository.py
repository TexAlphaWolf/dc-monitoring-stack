"""Consistency checks that need no Prometheus: python -m unittest discover -s tests -v"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_dashboards  # noqa: E402

try:
    import yaml
except ImportError:  # PyYAML is optional locally, CI installs it
    yaml = None

BUILDERS = {
    "overview.json": build_dashboards.overview,
    "linux-hosts.json": build_dashboards.linux,
    "windows-hosts.json": build_dashboards.windows,
    "containers.json": build_dashboards.containers,
    "endpoints.json": build_dashboards.endpoints,
}


class Dashboards(unittest.TestCase):
    def test_files_match_the_generator(self):
        """Edit tools/build_dashboards.py and regenerate: never edit the JSON by hand."""
        for name, build in BUILDERS.items():
            on_disk = json.loads((ROOT / "grafana" / "dashboards" / name).read_text("utf-8"))
            self.assertEqual(build().build(), on_disk, f"{name} is out of date")

    def test_no_stray_dashboard_files(self):
        found = {p.name for p in (ROOT / "grafana" / "dashboards").glob("*.json")}
        self.assertEqual(found, set(BUILDERS))

    def test_unique_uids_and_valid_links(self):
        boards = [build().build() for build in BUILDERS.values()]
        uids = [b["uid"] for b in boards]
        self.assertEqual(len(uids), len(set(uids)))
        for board in boards:
            for link in board["links"]:
                self.assertIn(link["url"].removeprefix("/d/"), uids)

    def test_panels_fit_the_grid_without_overlap(self):
        for name, build in BUILDERS.items():
            taken: set[tuple[int, int]] = set()
            for panel in build().build()["panels"]:
                pos = panel["gridPos"]
                self.assertLessEqual(pos["x"] + pos["w"], 24, f"{name}: {panel['title']}")
                cells = {
                    (x, y)
                    for x in range(pos["x"], pos["x"] + pos["w"])
                    for y in range(pos["y"], pos["y"] + pos["h"])
                }
                self.assertFalse(cells & taken, f"{name}: {panel['title']} overlaps")
                taken |= cells

    def test_every_panel_has_a_query_and_the_provisioned_datasource(self):
        for name, build in BUILDERS.items():
            for panel in build().build()["panels"]:
                self.assertTrue(panel["targets"], f"{name}: {panel['title']}")
                self.assertEqual(panel["datasource"]["uid"], "prometheus")
                for target in panel["targets"]:
                    self.assertTrue(target["expr"].strip())


@unittest.skipIf(yaml is None, "PyYAML not installed")
class AlertRules(unittest.TestCase):
    def rules(self):
        for path in sorted((ROOT / "prometheus" / "rules").glob("*.yml")):
            for group in yaml.safe_load(path.read_text("utf-8"))["groups"]:
                for rule in group["rules"]:
                    yield path.name, rule

    def test_every_alert_has_severity_summary_and_description(self):
        for file, rule in self.rules():
            if "alert" not in rule:
                continue
            name = f"{file}: {rule['alert']}"
            self.assertIn(rule["labels"]["severity"], {"critical", "warning", "info", "none"}, name)
            self.assertTrue(rule["annotations"].get("summary"), name)
            self.assertTrue(rule["annotations"].get("description"), name)

    def test_alert_names_are_unique(self):
        names = [rule["alert"] for _, rule in self.rules() if "alert" in rule]
        self.assertEqual(len(names), len(set(names)))

    def test_every_alert_has_a_unit_test(self):
        tested = set()
        for path in (ROOT / "prometheus" / "tests").glob("*.test.yml"):
            for case in yaml.safe_load(path.read_text("utf-8"))["tests"]:
                for check in case.get("alert_rule_test", []):
                    if check.get("exp_alerts"):
                        tested.add(check["alertname"])
        alerts = {rule["alert"] for _, rule in self.rules() if "alert" in rule}
        self.assertEqual(sorted(alerts - tested), [], "alerts without a positive unit test")

    def test_alert_documentation_is_current(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import build_docs

        on_disk = (ROOT / "docs" / "alerts.md").read_text("utf-8")
        self.assertEqual(build_docs.render(), on_disk, "run python tools/build_docs.py")

    def test_alertmanager_never_pages_the_heartbeat(self):
        config = yaml.safe_load((ROOT / "alertmanager" / "alertmanager.yml").read_text("utf-8"))
        first = config["route"]["routes"][0]
        self.assertEqual(first["receiver"], "null")
        self.assertIn("Watchdog", first["matchers"][0])


if __name__ == "__main__":
    unittest.main()
