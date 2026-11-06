# Architecture

## Components

| Service | Image | Role |
|---|---|---|
| `prometheus` | `prom/prometheus` (3.13 LTS) | Scrapes targets every 30 s, evaluates rules, stores 30 days |
| `alertmanager` | `prom/alertmanager` | Groups, deduplicates, inhibits and delivers alerts to Telegram |
| `node-exporter` | `prom/node-exporter` | Host metrics of the machine Docker runs on |
| `cadvisor` | `gcr.io/cadvisor/cadvisor` | Per-container metrics |
| `blackbox` | `prom/blackbox-exporter` | HTTP, TCP and TLS probes |
| `grafana` | `grafana/grafana` | Dashboards, provisioned from files |
| `windows_exporter` | installed on Windows (not a container) | Metrics of a Windows PC |

All ports are published on `127.0.0.1` only. Exporters are not published at all: they are
reached on the Compose network.

## Data flow

1. Prometheus reads `prometheus/targets/*.yml` (file-based service discovery) and scrapes
   each target. Blackbox targets go through `/probe` with the target as a parameter.
2. Rules in `prometheus/rules/` run every 30 s. Recording rules (`node:cpu_busy:ratio`,
   `node:filesystem_avail:ratio`, ...) sit in the same group as the alerts and come first, so an
   alert always sees the value of the same evaluation cycle. Dashboards use the same series.
3. Firing alerts go to Alertmanager, which groups by `alertname, host, instance`, waits 30 s to
   collect related alerts, applies the inhibition rules and renders a Telegram message
   from `alertmanager/templates/telegram.tmpl`.
4. `Watchdog` always fires and is routed to the `null` receiver. If you add a dead man's switch
   service later, point that route at it.

## Inhibition

| A firing alert... | ...silences |
|---|---|
| any `critical` | the `warning` with the same name and instance |
| `HostDown`, `WindowsHostDown` | every warning/info about the same host |
| `HostDiskSpaceCritical` | `HostDiskSpaceLow` and `HostDiskWillFillIn24Hours` for that mount point |
| `TlsCertificateExpiresVerySoon` | `TlsCertificateExpiresSoon` |

## Choices and trade-offs

- **Prometheus LTS (3.13)** rather than the newest release: security fixes until mid 2027 and
  fewer surprises. Dependabot is told to leave major and minor versions alone.
- **File-based discovery** instead of static targets in `prometheus.yml`: adding a host needs
  no restart and no change to the main configuration.
- **Allow-list of filesystem types** (`ext4`, `xfs`, `btrfs`, `zfs`, `ntfs`...) instead of an
  ignore list: pseudo and overlay filesystems can never trigger a disk alert.
- **Docker secrets from `.env`** for the Telegram credentials, so they never appear in a
  config file, a command line or `docker inspect` output of the container environment.
- **cAdvisor with `store_container_labels=false`** keeps the number of series small; the
  container name is enough for a home rack.
