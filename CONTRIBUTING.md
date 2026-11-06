# Contributing

```bash
bash tools/check.sh        # promtool, amtool, alert unit tests, routing, dashboards (needs Docker)
```

- Add or change an alert in `prometheus/rules/`, **and** a unit test for it in
  `prometheus/tests/` (a test checks that every alert has one), then `python tools/build_docs.py`.
- Change dashboards in `tools/build_dashboards.py`, then `python tools/build_dashboards.py`.
  Never edit the JSON by hand.
- Keep secrets out of the repository and real host names out of examples.
