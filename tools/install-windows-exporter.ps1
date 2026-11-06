<#
.SYNOPSIS
  Installs windows_exporter on this PC so Prometheus can monitor it. Run in an elevated PowerShell.
.DESCRIPTION
  Downloads the official MSI from GitHub, verifies its SHA-256 against the checksum file published
  in the same release, installs it as a service on port 9182 and opens the firewall only for
  private network ranges (Docker Desktop reaches the PC from one of them).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\install-windows-exporter.ps1
#>
param(
    [string]$Version = '0.31.8',
    [int]$Port = 9182,
    # Only these sources may connect (comma separated). Narrow it down if you know the range.
    [string]$AllowFrom = '127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16',
    # Expected SHA-256 of the MSI; looked up in the release's checksum file when omitted.
    [string]$Sha256 = ''
)
$ErrorActionPreference = 'Stop'

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script in an elevated PowerShell (Run as administrator)."
}

$base = "https://github.com/prometheus-community/windows_exporter/releases/download/v$Version"
$name = "windows_exporter-$Version-amd64.msi"
$msi = Join-Path $env:TEMP $name

Write-Host "Downloading $name"
Invoke-WebRequest -Uri "$base/$name" -OutFile $msi -UseBasicParsing

if (-not $Sha256) {
    $sums = (Invoke-WebRequest -Uri "$base/sha256sums.txt" -UseBasicParsing).Content
    # GitHub serves this file as application/octet-stream, so PowerShell 5.1 returns raw bytes.
    if ($sums -is [byte[]]) { $sums = [System.Text.Encoding]::UTF8.GetString($sums) }
    $line = ($sums -split "`n") | Where-Object { $_ -match [regex]::Escape($name) } | Select-Object -First 1
    if (-not $line) { throw "No checksum for $name in the release. Pass -Sha256 explicitly." }
    $Sha256 = ($line.Trim() -split '\s+')[0]
}
$actual = (Get-FileHash -Algorithm SHA256 -Path $msi).Hash
if ($actual -ne $Sha256.ToUpper()) {
    Remove-Item $msi -Force
    throw "SHA-256 mismatch for $name (expected $Sha256, got $actual). Nothing was installed."
}
Write-Host "SHA-256 verified"

$args = @('/i', "`"$msi`"", '/qn', "LISTEN_PORT=$Port", "REMOTE_ADDR=$AllowFrom")
$process = Start-Process msiexec.exe -ArgumentList $args -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "msiexec failed with exit code $($process.ExitCode)" }
Remove-Item $msi -Force

Start-Sleep -Seconds 3
Get-Service windows_exporter | Format-Table Name, Status, StartType
$response = Invoke-WebRequest -Uri "http://localhost:$Port/metrics" -UseBasicParsing
Write-Host "windows_exporter answers on port $Port ($($response.Content.Length) bytes of metrics)."
Write-Host "Next: docker compose up -d, then check http://localhost:9090/targets"
