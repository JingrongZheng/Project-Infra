; Build with Inno Setup 6.7+. No project data is shipped or removed.
#ifndef SourceDir
  #define SourceDir "..\dist\portable\ProjectInfra"
#endif
#ifndef ProductId
  #define ProductId "ProjectInfra.Desktop"
#endif
#ifndef ProductName
  #define ProductName "Project Infra"
#endif
#ifndef ProductVersion
  #error Build with scripts/build_installer.py to supply ProductVersion
#endif
#ifndef OutputName
  #define OutputName "ProjectInfra-" + ProductVersion + "-Setup"
#endif
#ifndef RuntimeMutex
  #define RuntimeMutex "Local\ProjectInfra.Desktop"
#endif

[Setup]
AppId={#ProductId}
AppName={#ProductName}
AppVersion={#ProductVersion}
AppVerName={#ProductName} {#ProductVersion}
DefaultDirName={localappdata}\Programs\ProjectInfra
DefaultGroupName={#ProductName}
DisableDirPage=no
DisableProgramGroupPage=yes
DisableWelcomePage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename={#OutputName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
SetupIconFile=..\project_infra\assets\pi-monogram.ico
UninstallDisplayIcon={app}\ProjectInfra.exe
AppMutex={#RuntimeMutex}
CloseApplications=no
RestartApplications=no
SetupLogging=yes
InfoBeforeFile=install-notes.txt

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "settings.json,settings.tmp"

[Icons]
Name: "{autoprograms}\{#ProductName}"; Filename: "{app}\ProjectInfra.exe"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\project_infra\assets\pi-monogram.ico"
Name: "{autodesktop}\{#ProductName}"; Filename: "{app}\ProjectInfra.exe"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\project_infra\assets\pi-monogram.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\ProjectInfra.exe"; Description: "启动 {#ProductName}"; Flags: nowait postinstall skipifsilent

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if FileExists(ExpandConstant('{app}\.project\config.toml')) then
    Result := '不能直接安装到项目根目录。请选择独立的软件安装目录，启动后再选择项目。';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpSelectDir then begin
    if FileExists(ExpandConstant('{app}\.project\config.toml')) then begin
      MsgBox('请选择独立的软件安装目录，不能直接安装到已初始化的项目根目录。项目位置在软件启动后单独选择。', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

{ No uninstall wildcard: user projects and recent-project settings are retained. }
