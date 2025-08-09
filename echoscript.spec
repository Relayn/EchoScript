# -*- mode: python ; coding: utf-8 -*-

# Этот файл является основным конфигурационным файлом для PyInstaller.
# Он позволяет точно настроить процесс сборки приложения.

import os
import whisper

block_cipher = None

# --- Находим путь к ассетам whisper ---
# Это гарантирует, что мы найдем их независимо от того, где установлен whisper
whisper_assets_path = os.path.join(os.path.dirname(whisper.__file__), 'assets')


# Анализ зависимостей приложения
a = Analysis(
    ['app/gui_main.py'],
    pathex=['.'],  # Добавляем корневую директорию проекта в пути поиска
    binaries=[],
    datas=[
        (whisper_assets_path, 'whisper/assets'),
        ('vendor/ffmpeg', 'ffmpeg') # Добавляем ffmpeg в сборку
    ],
    hiddenimports=[
        'customtkinter',
        'customtkinter.windows',
        'customtkinter.windows.widgets',
        'customtkinter.macOS',
        'customtkinter.macOS.widgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Создание архива с чистым Python-кодом
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Создание исполняемого файла (.exe)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gui_main',  # Имя исполняемого файла
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # False - для GUI-приложений, чтобы не открывалась консоль
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Сборка всех файлов в одну директорию (режим onedir)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EchoScript', # Имя итоговой папки в dist/
)
