<#
.SYNOPSIS
    Automated ADB Port Forwarding / Reverse Tunnel for TeleLens.
.DESCRIPTION
    Detects connected Android devices via ADB and sets up reverse port forwarding
    so the phone can communicate with the laptop's TeleLens server over USB.
#>

param (
    [int]$Port = 8990
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  TeleLens ADB USB Reverse Tunnel Helper  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if ADB is installed
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adbCmd) {
    Write-Warning "ADB (Android Debug Bridge) is not found in your PATH."
    Write-Host "Please install Android Platform Tools or run through Wi-Fi mDNS mode." -ForegroundColor Yellow
    exit 1
}

Write-Host "Checking for connected Android devices..." -ForegroundColor Gray
$devices = adb devices | Select-String -Pattern "\bdevice\b" | Where-Object { $_ -notmatch "List of devices" }

if (-not $devices) {
    Write-Warning "No Android devices detected with USB Debugging enabled."
    Write-Host "Ensure USB Debugging is ON in Developer Options on your phone." -ForegroundColor Yellow
    exit 1
}

Write-Host "Configuring reverse port forwarding: tcp:$Port -> tcp:$Port" -ForegroundColor Green
adb reverse tcp:$Port tcp:$Port

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] TeleLens USB ADB Tunnel established!" -ForegroundColor Green
    Write-Host "Your phone can now connect to ws://127.0.0.1:$Port via USB." -ForegroundColor Cyan
} else {
    Write-Error "Failed to execute adb reverse."
}
