<#
.SYNOPSIS
  Creates .env with a random Grafana password and your Telegram settings.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\init-env.ps1
#>
param([switch]$Force)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

if ((Test-Path .env) -and -not $Force) {
    throw ".env already exists. Use -Force to overwrite it (the old values are lost)."
}

function New-Secret {
    $bytes = New-Object byte[] 24
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    ([Convert]::ToBase64String($bytes) -replace '[+/=]', '').Substring(0, 24)
}

Write-Host "Telegram alerts: create a bot with @BotFather, then send it a message and read the chat id"
Write-Host "from https://api.telegram.org/bot<TOKEN>/getUpdates. Press Enter to skip and set it later in .env."
$secure = Read-Host "Telegram bot token" -AsSecureString
$token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
$chat = Read-Host "Telegram chat id"
if (-not $token) { $token = 'not-configured' }
if ($chat -notmatch '^-?\d+$') { $chat = '0' }

$lines = @(
    "GRAFANA_ADMIN_PASSWORD=$(New-Secret)",
    "TELEGRAM_BOT_TOKEN=$token",
    "TELEGRAM_CHAT_ID=$chat",
    "PROMETHEUS_RETENTION=30d",
    "GRAFANA_PORT=3000",
    "PROMETHEUS_PORT=9090",
    "ALERTMANAGER_PORT=9093"
)
Set-Content -Path .env -Value $lines -Encoding ascii
Write-Host ".env written. Grafana password: Select-String -Path .env -Pattern GRAFANA_ADMIN_PASSWORD"
