# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Tomodoro
# Build: pyinstaller tomodoro.spec

import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collect all customtkinter assets (themes, images, fonts)
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

# Collect pygame data
pg_datas, pg_binaries, pg_hiddenimports = collect_all("pygame")

a = Analysis(
    ["tomodoro.py"],
    pathex=[],
    binaries=ctk_binaries + pg_binaries,
    datas=ctk_datas + pg_datas,
    hiddenimports=(
        ctk_hiddenimports
        + pg_hiddenimports
        + ["customtkinter", "pygame", "pygame.mixer",
           "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageTk",
           "darkdetect", "packaging"]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["numpy", "matplotlib", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Tomodoro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="tomato.ico",     # uncomment and provide a .ico file if desired
    version_file=None,
)
