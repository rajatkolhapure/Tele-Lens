; ─────────────────────────────────────────────────────────────────────────────
; TeleLens Inno Setup Installer Script
; Produces:  TeleLens-Setup.exe
;
; Requirements:
;   - Inno Setup 6+  (https://jrsoftware.org/isdl.php)
;   - PyInstaller output folder at: receiver\dist\TeleLens\
;   - App icon at: installer\assets\telelens.ico
;   - OBS DirectShow filter DLLs at: installer\drivers\obs-virtualcam\
; ─────────────────────────────────────────────────────────────────────────────

#define MyAppName        "TeleLens"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "Rajat"
#define MyAppURL         "https://github.com/rmk19/rajats-take-on-webcams"
#define MyAppExeName     "TeleLens.exe"
#define MyDistDir        "..\receiver\dist\TeleLens"
#define MyDriverDir      "drivers\obs-virtualcam"

[Setup]
AppId={{F3A1C2B4-9E77-4D8A-B012-6E7F0A3C1D55}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\TeleLens
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist-installer
OutputBaseFilename=TeleLens-Setup
SetupIconFile=assets\telelens.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=120
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
; Minimum Windows 10
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "Create Start Menu shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "registervcam"; Description: "Register OBS Virtual Camera driver (required for Zoom, Teams, Meet)"; GroupDescription: "Virtual Camera Driver"; Flags: checkedonce

[Files]
; ── Main Application Binaries ────────────────────────────────────────────────
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── OBS Virtual Camera DirectShow Filter ────────────────────────────────────
; These DLLs are bundled from the open-source obs-studio project (MIT-compatible GPLv2).
; We register them silently during install so users never need to install full OBS Studio.
Source: "{#MyDriverDir}\obs-virtualcam-startup.dll"; DestDir: "{sys}"; Flags: ignoreversion; Tasks: registervcam
Source: "{#MyDriverDir}\obs-virtualcam-startup-32bit.dll"; DestDir: "{syswow64}"; Flags: ignoreversion; Tasks: registervcam; Check: IsWin64

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
; ── Register Virtual Camera DLLs ─────────────────────────────────────────────
Filename: "{sys}\regsvr32.exe"; Parameters: "/s ""{sys}\obs-virtualcam-startup.dll"""; StatusMsg: "Registering virtual webcam driver..."; Tasks: registervcam; Flags: runhidden waituntilterminated
Filename: "{syswow64}\regsvr32.exe"; Parameters: "/s ""{syswow64}\obs-virtualcam-startup-32bit.dll"""; StatusMsg: "Registering 32-bit virtual webcam driver..."; Tasks: registervcam; Check: IsWin64; Flags: runhidden waituntilterminated

; ── Launch App After Install ─────────────────────────────────────────────────
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Unregister virtual camera DLLs on uninstall
Filename: "{sys}\regsvr32.exe"; Parameters: "/s /u ""{sys}\obs-virtualcam-startup.dll"""; Tasks: registervcam; Flags: runhidden
Filename: "{syswow64}\regsvr32.exe"; Parameters: "/s /u ""{syswow64}\obs-virtualcam-startup-32bit.dll"""; Tasks: registervcam; Check: IsWin64; Flags: runhidden

[Code]
// Verify that Windows 10+ is the running OS (belt-and-suspenders check)
function InitializeSetup(): Boolean;
begin
  Result := True;
  if GetWindowsVersion < $0A000000 then begin
    MsgBox('TeleLens requires Windows 10 or later.', mbError, MB_OK);
    Result := False;
  end;
end;
