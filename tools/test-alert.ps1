<# Sends a test alert through Alertmanager so you can see it arrive on Telegram. #>
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose exec alertmanager amtool alert add alertname=TestAlert severity=warning host=manual `
    --annotation=summary="Test alert from dc-monitoring-stack" `
    --annotation=description="If you can read this on Telegram, notifications work." `
    --alertmanager.url=http://localhost:9093
Write-Host "Sent. It reaches Telegram after the group wait (about 30 seconds)."
