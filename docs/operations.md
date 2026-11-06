# Operations

## Telegram

1. In Telegram open `@BotFather`, send `/newbot` and copy the token.
2. Send any message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `"chat":{"id":...}`.
3. Put both in `.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) and run
   `docker compose up -d` again. Test with `tools\test-alert.ps1`.

Never paste the token in a chat or an issue. If it leaks, revoke it with `/revoke` in BotFather.
If notifications stop, `AlertmanagerNotificationsFailing` fires once any other channel is
working, and `docker compose logs alertmanager` shows why.

## Add a machine, an endpoint or a service

Edit the files in `prometheus/targets/` (see the comments in each file). Prometheus picks the
change up in under a minute. Linux hosts need `node_exporter` installed on them
(`apt install prometheus-node-exporter` or the official binary) listening on port 9100.

## Silence an alert

Open <http://localhost:9093>, find the alert and press *Silence*. Use this for planned work or
for a PC that sleeps.

## Retention and backups

`PROMETHEUS_RETENTION` (default `30d`) in `.env`. Data lives in the Docker volume
`dc-monitoring-stack_prometheus-data`; Grafana's own database in `..._grafana-data`
(dashboards come from files, so only users and preferences are in it).

## Upgrades

Versions are pinned in `docker-compose.yml`. Change a tag, run `tools\check.ps1` (it uses the
same image versions for `promtool` and `amtool`), then `docker compose up -d`. Dependabot opens
pull requests for patch updates only.

## Troubleshooting

| Symptom | Check |
|---|---|
| A panel says *No data* | <http://localhost:9090/targets>: is the job UP? Is the time range right? |
| `windows` job is DOWN | `docs/windows.md`: service running? firewall range? `host.docker.internal` resolves inside the container? |
| Container dashboard empty, no names | cAdvisor cannot read container names on some Docker Desktop setups. `docker compose logs cadvisor` shows why; dashboards that only need host metrics are not affected. |
| `port is already allocated` | Another program uses the port: set `GRAFANA_PORT`, `PROMETHEUS_PORT` or `ALERTMANAGER_PORT` in `.env` and run `docker compose up -d` again. |
| `docker compose up` complains about `TELEGRAM_BOT_TOKEN` | Run `tools\init-env.ps1` or copy `.env.example` to `.env`. |
| Alerts do not arrive | `docker compose logs alertmanager`, then `tools\test-alert.ps1`. |
| `AlertmanagerNotificationsFailing` fires right after install | Telegram is not configured yet (the token is `not-configured`). Put the real token and chat id in `.env` and run `docker compose up -d`. |
| `HostClockNotSynchronising` on Docker Desktop | The WSL2 VM keeps its time through Hyper-V, so the kernel never reports an NTP sync. The clock is fine: silence the alert for `docker-host`. On a real Linux server it means chrony or systemd-timesyncd is not working. |
