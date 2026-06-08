; Inno Setup 6 安装脚本 — TracePipeline (模板)
; 由 scripts/package.py 运行时动态生成完整路径
; 请勿手动编辑 OutputDir / SetupIconFile，运行 package.py 将自动填充

[Setup]
AppId={{7B3F1C9A-5D2E-40F8-A61B-C8E4D9F01236}}
AppName=TracePipeline
AppVersion=3.7.6
AppPublisher=ECUT
AppPublisherURL=https://github.com/ECUT
AppSupportURL=https://github.com/ECUT
DefaultDirName={autopf}\TracePipeline
DefaultGroupName=TracePipeline
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
OutputDir=dist
OutputBaseFilename=TracePipeline-Setup-v3.7.2
SetupIconFile=reference\ECUT.ico
UninstallDisplayIcon={app}\reference\ECUT.ico
UninstallDisplayName=TracePipeline v3.7.2
VersionInfoVersion=3.7.2

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\TracePipeline\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\TracePipeline"; Filename: "{app}\TracePipeline.exe"; IconFilename: "{app}\reference\ECUT.ico"
Name: "{group}\卸载 TracePipeline"; Filename: "{uninstallexe}"
Name: "{commondesktop}\TracePipeline"; Filename: "{app}\TracePipeline.exe"; IconFilename: "{app}\reference\ECUT.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "其他快捷方式"

[Run]
Filename: "{app}\TracePipeline.exe"; Description: "启动 TracePipeline"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\config.json"
