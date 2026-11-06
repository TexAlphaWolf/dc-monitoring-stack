# Monitoring a Windows PC

Docker Desktop's `node-exporter` reports the Linux VM that runs Docker, not Windows. To see the
PC itself install [windows_exporter](https://github.com/prometheus-community/windows_exporter)
(official Prometheus community exporter) as a service. In an **elevated** PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install-windows-exporter.ps1
```

The script downloads the MSI from the GitHub release, **verifies its SHA-256** against the
checksum file of the same release (it refuses to install on a mismatch), installs the service on
port 9182 and opens the Windows firewall only for private network ranges
(`127.0.0.1, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16`). Narrow it with `-AllowFrom` if you
know the range Docker uses.

## Check it works

```powershell
Get-Service windows_exporter
docker compose exec prometheus wget -qO- http://host.docker.internal:9182/metrics | Select-Object -First 5
```

Then open <http://localhost:9090/targets>: job `windows` must be **UP**. The dashboard
*Windows hosts* fills within a minute.

## A PC that is switched off

`WindowsHostDown` fires after 10 minutes without an answer. A desktop that sleeps at night will
trigger it: create a silence in Alertmanager (<http://localhost:9093>) or remove
`prometheus/targets/windows.yml`'s content. On a server this alert is the one you want.

## Several Windows machines

Add them to `prometheus/targets/windows.yml`:

```yaml
- targets: ["192.168.0.20:9182"]
  labels:
    host: office-pc
```
