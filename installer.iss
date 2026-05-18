; Metering Station Designer v1.0.0 — Inno Setup Installer Script

[Setup]
AppName=Metering Station Designer
AppVersion=1.0.0
AppPublisher=Metering Designer Team
AppPublisherURL=https://github.com/SLedgehammer-dev12/metering-station-designer
DefaultDirName={autopf}\MeteringStationDesigner
DefaultGroupName=Metering Station Designer
OutputBaseFilename=MeteringDesigner_Setup_v1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Metering Station Designer v1.0.0
PrivilegesRequired=asInvoker
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion=1.0.0
VersionInfoCompany=Metering Designer Team
VersionInfoDescription=Measurement Station Design Tool
VersionInfoProductName=Metering Station Designer
VersionInfoProductVersion=1.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Create &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startmenu"; Description: "Create Start &Menu entry"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\app.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Metering Station Designer"; Filename: "{app}\app.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall Metering Station Designer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Metering Station Designer"; Filename: "{app}\app.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\app.exe"; Description: "Launch Metering Station Designer"; Flags: nowait postinstall skipifsilent
