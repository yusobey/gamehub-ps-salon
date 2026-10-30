; GameHub PS Salon - kurulum sihirbazı (Inno Setup 6). build.bat bunu otomatik çalıştırır.
; Elle derlemek isterseniz: önce PyInstaller (--onedir) ile dist\GameHub_PS_Salon üretin.
#ifndef Surum
  #define Surum "1.0.0"
#endif

[Setup]
; AppId'yi ASLA değiştirmeyin: güncellemelerin eski kurulumun üzerine yazması bununla olur.
AppId={{F48721BF-6B48-4FD9-B142-7391C13ECF20}
AppName=GameHub PS Salon
AppVersion={#Surum}
AppPublisher=GameHub
DefaultDirName={autopf}\GameHub PS Salon
DefaultGroupName=GameHub PS Salon
OutputDir=Output
OutputBaseFilename=GameHub_Kurulum_{#Surum}
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\GameHub_PS_Salon.exe
CloseApplications=yes
RestartApplications=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"

[Files]
Source: "dist\GameHub_PS_Salon\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\GameHub PS Salon"; Filename: "{app}\GameHub_PS_Salon.exe"
Name: "{group}\GameHub PS Salon'u Kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GameHub PS Salon"; Filename: "{app}\GameHub_PS_Salon.exe"; Tasks: desktopicon

[Run]
; Normal kurulumda "başlat" kutusu; otomatik (sessiz) güncellemede program kendiliğinden yeniden açılır.
Filename: "{app}\GameHub_PS_Salon.exe"; Description: "GameHub PS Salon'u başlat"; Flags: nowait postinstall skipifsilent
Filename: "{app}\GameHub_PS_Salon.exe"; Flags: nowait; Check: WizardSilent

; Kaldırırken %APPDATA%\GameHub (veriler) bilerek SİLİNMEZ.
