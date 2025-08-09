; Скрипт для Inno Setup 6
; EchoScript Installer

#define AppName "EchoScript"
#define AppVersion "0.1.0"
#define AppPublisher "Relayn"
#define AppURL "https://github.com/Relayn/EchoScript"
#define AppExeName "gui_main.exe"
#define SourceDir "..\dist\EchoScript"

[Setup]
; Основная информация о приложении и инсталляторе
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputBaseFilename=EchoScript-{#AppVersion}-Setup
OutputDir=.\
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
; Задачи, которые пользователь может выбрать при установке
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Самая важная секция: указываем, какие файлы и папки включить в инсталлятор.
; Source: путь к файлам относительно этого скрипта.
; DestDir: {app} - это папка, которую пользователь выберет для установки.
; Flags: recursesubdirs - рекурсивно включить все подпапки; createallsubdirs - создать все подпапки.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Создание ярлыков в меню "Пуск" и на рабочем столе
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#AppName}}"; Filename: "{#AppURL}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Запустить приложение после завершения установки, если пользователь поставит галочку
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
