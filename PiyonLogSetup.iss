; Piyon Log - Inno Setup kurulum betiği.
;
; PiyonLog.exe'yi (önce `pyinstaller PiyonLog.spec` ile üretilmiş olmalı)
; kullanıcıya özel bir klasöre (LocalAppData) kuran, yönetici izni
; gerektirmeyen bir kurulum dosyası üretir. Uygulama verisini exe'nin
; yanına yazdığı için (bkz. config.py) kurulum konumu mutlaka
; kullanıcının kendi yazabildiği bir yer olmalı - Program Files DEĞİL.
;
; Derlemek için:
;   "C:\Program Files\Inno Setup 7\ISCC.exe" PiyonLogSetup.iss

#define MyAppName "Piyon Log"
#define MyAppVersion "1.0.0"
#define MyAppExeName "PiyonLog.exe"
#define MyAppPublisher "Piyon Co."

[Setup]
AppId={{56B667D1-0D93-4830-9FDB-785954C53F11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\PiyonLog
DefaultGroupName=Piyon Log
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer
OutputBaseFilename=PiyonLogSetup
SetupIconFile=piyon-log.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü simgesi oluştur"; GroupDescription: "Ek simgeler:"
Name: "startupicon"; Description: "Bilgisayar açılınca otomatik başlat (sessizce, pencere açmadan)"; GroupDescription: "Ek simgeler:"

[Files]
Source: "dist\PiyonLog.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Piyon Log"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,Piyon Log}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Piyon Log"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\Piyon Log"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--background"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Piyon Log'u şimdi başlat"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Kaldırırken kullanıcı verisini SORMADAN silme - kasıtlı olarak veri
; klasörüne dokunulmuyor, sadece uygulama dosyası kaldırılıyor.
