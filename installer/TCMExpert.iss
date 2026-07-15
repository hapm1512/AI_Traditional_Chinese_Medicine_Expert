#define MyAppName "AI Traditional Chinese Medicine Expert"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Hai Pham"
#define MyAppExeName "TCMExpert.exe"

[Setup]
AppId={{86B8E47F-BDD1-4A0D-B97F-31F569D046DC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\TCMExpert
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=TCMExpert-2.0.0-Setup-Windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\TCMExpert\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài màn hình"; GroupDescription: "Tùy chọn:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Khởi động ứng dụng"; Flags: nowait postinstall skipifsilent
