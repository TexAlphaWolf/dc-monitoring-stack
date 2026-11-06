<# Static checks of the whole configuration (needs Docker Desktop running and Python). #>
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$prom = (Select-String -Path docker-compose.yml -Pattern 'prom/prometheus:\S+').Matches[0].Value
$am = (Select-String -Path docker-compose.yml -Pattern 'prom/alertmanager:\S+').Matches[0].Value
$here = (Get-Location).Path

function Run-Docker { & docker @args; if ($LASTEXITCODE -ne 0) { throw "check failed" } }

Write-Host "== Prometheus configuration and rules ($prom)"
Run-Docker run --rm -v "${here}/prometheus:/etc/prometheus:ro" --entrypoint promtool $prom check config /etc/prometheus/prometheus.yml
Write-Host "== Alert rule unit tests"
foreach ($file in Get-ChildItem prometheus/tests/*.test.yml) {
    Run-Docker run --rm -v "${here}/prometheus:/etc/prometheus:ro" --entrypoint promtool $prom test rules "/etc/prometheus/tests/$($file.Name)"
}
Write-Host "== Alertmanager configuration ($am)"
$amtool = @('run', '--rm', '-v', "${here}/alertmanager:/etc/alertmanager:ro", '--entrypoint', 'amtool', $am)
Run-Docker @amtool check-config /etc/alertmanager/alertmanager.yml
$expected = @(
    @('null', 'alertname=Watchdog', 'severity=none'),
    @('telegram', 'alertname=HostDown', 'severity=critical'),
    @('telegram', 'alertname=HostHighCpu', 'severity=warning'),
    @('telegram', 'alertname=HostRebooted', 'severity=info')
)
foreach ($case in $expected) {
    $got = (& docker @amtool config routes test --config.file=/etc/alertmanager/alertmanager.yml $case[1] $case[2]).Trim()
    if ($got -ne $case[0]) { throw "routing: $($case[1]) $($case[2]) went to '$got', expected '$($case[0])'" }
}
Write-Host "routing ok"
Write-Host "== Dashboards and repository consistency"
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "unit tests failed" }
Write-Host "All static checks passed."
