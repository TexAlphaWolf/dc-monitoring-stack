# Alerts

Generated from `prometheus/rules/*.yml` by `tools/build_docs.py`: do not edit by hand.
Every alert has a unit test in `prometheus/tests/`. Severities: **critical** repeats
every hour, **warning** every 4 hours, **info** once a day, **none** is the heartbeat
and is never sent to a person.

## Monitoring the monitoring

| Alert | Severity | Fires when | For |
|---|---|---|---|
| `Watchdog` | none | This alert always fires. If it stops arriving at the heartbeat receiver, alerting is broken. <br><sub>`vector(1)`</sub> | 0m |
| `TargetDown` | warning | Prometheus has not been able to scrape … (job …) for 5 minutes. <br><sub>`up{job!~"node\|windows"} == 0`</sub> | 5m |
| `PrometheusConfigReloadFailed` | critical | The last reload of prometheus.yml failed: Prometheus keeps running the previous configuration. <br><sub>`prometheus_config_last_reload_successful == 0`</sub> | 1m |
| `PrometheusRuleEvaluationFailing` | warning | … rule evaluations failed in the last 10 minutes. <br><sub>`increase(prometheus_rule_evaluation_failures_total[10m]) > 0`</sub> | 5m |
| `PrometheusNotConnectedToAlertmanager` | critical | No Alertmanager is discovered, so no alert can be delivered. <br><sub>`prometheus_notifications_alertmanagers_discovered < 1`</sub> | 5m |
| `AlertmanagerNotificationsFailing` | warning | Check the Telegram token and chat id (docker compose logs alertmanager). <br><sub>`sum by (integration) (rate(alertmanager_notifications_failed_total[10m])) > 0`</sub> | 5m |
| `AlertmanagerConfigReloadFailed` | critical | Alertmanager keeps running the previous configuration. <br><sub>`alertmanager_config_last_reload_successful == 0`</sub> | 1m |

## Linux hosts

| Alert | Severity | Fires when | For |
|---|---|---|---|
| `HostDown` | critical | node_exporter on … (…) has not answered for 2 minutes. <br><sub>`up{job="node"} == 0`</sub> | 2m |
| `HostHighCpu` | warning | CPU has been above 85% for 15 minutes (now …). <br><sub>`node:cpu_busy:ratio > 0.85`</sub> | 15m |
| `HostMemoryLow` | warning | Only … of memory is available. <br><sub>`node:memory_available:ratio < 0.10`</sub> | 10m |
| `HostSwapHeavilyUsed` | warning | More than 80% of swap has been in use for 15 minutes: the host is short of memory. <br><sub>`(node_memory_SwapTotal_bytes > 0) and (1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes > 0.80)`</sub> | 15m |
| `HostLoadHigh` | warning | The 15-minute load average is more than twice the number of CPU cores. <br><sub>`node_load15 / on (instance) count by (instance) (node_cpu_seconds_total{mode="idle"}) > 2`</sub> | 30m |
| `HostDiskSpaceLow` | warning | Less than 15% of … (…) is free. <br><sub>`node:filesystem_avail:ratio < 0.15`</sub> | 10m |
| `HostDiskSpaceCritical` | critical | Less than 5% of … (…) is free. <br><sub>`node:filesystem_avail:ratio < 0.05`</sub> | 5m |
| `HostDiskWillFillIn24Hours` | warning | At the rate of the last 6 hours, … runs out of space in less than 24 hours. <br><sub>`(predict_linear(node_filesystem_avail_bytes{fstype=~"ext[234]\|xfs\|btrfs\|zfs\|vfat\|exfat\|ntfs3?\|fuseblk\|f2fs"}[6h], 24 * 3600) < 0) and on (instance, device, mountpoint) (node:filesystem_avail:ratio < 0.40)`</sub> | 1h |
| `HostInodesLow` | warning | Less than 10% of inodes are free on …. <br><sub>`node_filesystem_files_free{fstype=~"ext[234]\|xfs\|btrfs\|f2fs"} / (node_filesystem_files{fstype=~"ext[234]\|xfs\|btrfs\|f2fs"} > 0) < 0.10`</sub> | 10m |
| `HostFilesystemReadOnly` | critical | A filesystem switched to read-only, usually after a disk error. Check dmesg and SMART data. <br><sub>`node_filesystem_readonly{fstype=~"ext[234]\|xfs\|btrfs\|f2fs"} == 1`</sub> | 2m |
| `HostNetworkErrors` | warning | More than one packet error per second for 15 minutes: check the cable, port and driver. <br><sub>`sum by (instance, host, device) ( rate(node_network_receive_errs_total{device!~"lo\|veth.*\|docker.*\|br-.*"}[10m]) + rate(node_network_transmit_errs_total{device!~"lo\|veth.*\|docker.*\|br-.*"}[10m]) ) > 1`</sub> | 15m |
| `HostClockSkew` | warning | The clock is … away from its reference. <br><sub>`abs(node_timex_offset_seconds) > 0.05 and node_timex_sync_status == 1`</sub> | 10m |
| `HostClockNotSynchronising` | warning | NTP/chrony is not keeping this clock in sync. <br><sub>`node_timex_sync_status == 0`</sub> | 30m |
| `HostOomKillDetected` | warning | An out-of-memory kill happened in the last 10 minutes. <br><sub>`increase(node_vmstat_oom_kill[10m]) > 0`</sub> | 0m |
| `HostRebooted` | info | The host has been up for less than 10 minutes. <br><sub>`time() - node_boot_time_seconds < 600`</sub> | 0m |

## Windows hosts

| Alert | Severity | Fires when | For |
|---|---|---|---|
| `WindowsHostDown` | warning | windows_exporter on … has not answered for 10 minutes. A desktop PC that is switched off or asleep triggers this: silence it or remove the target. <br><sub>`up{job="windows"} == 0`</sub> | 10m |
| `WindowsHighCpu` | warning | CPU has been above 90% for 15 minutes (now …). <br><sub>`windows:cpu_busy:ratio > 0.90`</sub> | 15m |
| `WindowsMemoryLow` | warning | Only … of physical memory is available. <br><sub>`windows:memory_available:ratio < 0.10`</sub> | 10m |
| `WindowsDiskSpaceLow` | warning | Less than 10% of drive … is free. <br><sub>`windows:disk_free:ratio < 0.10`</sub> | 10m |

## Containers

| Alert | Severity | Fires when | For |
|---|---|---|---|
| `ContainerMissing` | warning | cAdvisor reported container … during the last hour but not any more. <br><sub>`count by (instance, name) (present_over_time(container_last_seen{name!=""}[1h])) unless count by (instance, name) (container_last_seen{name!=""})`</sub> | 2m |
| `ContainerRestartLoop` | warning | It restarted … times in 15 minutes. <br><sub>`changes(container_start_time_seconds{name!=""}[15m]) >= 3`</sub> | 0m |
| `ContainerMemoryNearLimit` | warning | It uses … of its memory limit. <br><sub>`container_memory_working_set_bytes{name!=""} / (container_spec_memory_limit_bytes{name!=""} > 0) > 0.90`</sub> | 10m |
| `ContainerCpuNearLimit` | warning | It uses … of its CPU limit. <br><sub>`sum by (instance, name) (rate(container_cpu_usage_seconds_total{name!=""}[5m])) / (sum by (instance, name) (container_spec_cpu_quota{name!=""} / container_spec_cpu_period{name!=""}) > 0) > 0.90`</sub> | 15m |

## Endpoints

| Alert | Severity | Fires when | For |
|---|---|---|---|
| `EndpointDown` | critical | The … probe of … has been failing for 2 minutes. <br><sub>`probe_success == 0`</sub> | 2m |
| `EndpointSlow` | warning | The request takes …. <br><sub>`probe_duration_seconds{job="probe-http"} > 2 and probe_success == 1`</sub> | 10m |
| `TlsCertificateExpiresSoon` | warning | Renew the certificate before it expires. <br><sub>`probe_ssl_earliest_cert_expiry - time() < 14 * 86400`</sub> | 1h |
| `TlsCertificateExpiresVerySoon` | critical | Renew the certificate now. <br><sub>`probe_ssl_earliest_cert_expiry - time() < 3 * 86400`</sub> | 10m |
