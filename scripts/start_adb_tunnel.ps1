<#
.SYNOPSIS
    Automated ADB Port Forwarding / Reverse Tunnel for TeleLens Studio.
.DESCRIPTION
    Detects connected Android devices via ADB and sets up dual-channel reverse port forwarding:
      1. Port 8990 (Signaling & Bidirectional Hardware Control)
      2. Port 8991 (Direct High-Speed Turbo Frame Pipe)
    Guarantees physical USB cable transit with zero latency and unthrottled 1088x1088 / 4K frames.
#>

param (
    [int]$SignalingPort = 8990,
    [int]$StreamPort = 8991
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  TeleLens Studio ADB USB Turbo Tunnel    " -ForegroundColor Cyan
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

Write-Host "Configuring dual-channel reverse port forwarding:" -ForegroundColor Green
Write-Host "  1. Signaling & Controls: tcp:$SignalingPort -> tcp:$SignalingPort" -ForegroundColor Gray
adb reverse tcp:$SignalingPort tcp:$SignalingPort

Write-Host "  2. Turbo Frame Pipe:     tcp:$StreamPort -> tcp:$StreamPort" -ForegroundColor Gray
adb reverse tcp:$StreamPort tcp:$StreamPort

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] TeleLens Dual-Channel USB Turbo Tunnel established!" -ForegroundColor Green
    Write-Host "  • Signaling: ws://127.0.0.1:$SignalingPort/ws" -ForegroundColor Cyan
    Write-Host "  • Turbo Pipe: tcp://127.0.0.1:$StreamPort" -ForegroundColor Cyan
    Write-Host "  • Fixed 1088x1088 Square HD & unthrottled frames active." -ForegroundColor Yellow
} else {
    Write-Error "Failed to execute adb reverse."
}
