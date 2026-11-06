# Security

## Reporting a problem

Open a private security advisory on GitHub (Security tab → Report a vulnerability) or contact
the maintainer through the profile. Please do not file public issues for vulnerabilities.

## Design notes

- Every published port is bound to `127.0.0.1`. Exporters are only reachable on the Compose
  network. Put a TLS reverse proxy with authentication in front of Grafana before exposing it.
- Secrets (Grafana password, Telegram token and chat id) live in `.env`, which Git ignores, and
  reach containers as environment variables or Docker secrets, never inside config files.
- Containers drop all capabilities, run with `no-new-privileges` and a read-only root filesystem
  where the software allows it (Alertmanager needs a writable one so Compose can inject the
  Telegram secrets). cAdvisor needs read access to the Docker data directory and
  `/dev/kmsg`, and node-exporter shares the host PID namespace: both are read-only and only
  expose metrics. Grafana needs a writable data directory.
- `windows_exporter` is installed from the official release after a SHA-256 check, and the
  firewall rule only admits private address ranges. Its metrics are not authenticated: do not
  open the port to untrusted networks.
- The Blackbox exporter verifies TLS certificates; a bad certificate is reported as a failure.
- Metrics can reveal host names and which services you run. Do not publish dashboards or
  screenshots of a real network without checking them first.

## Not covered

- Authentication between Prometheus and the exporters (they sit on a private network).
- Hardening of the hosts being monitored.
