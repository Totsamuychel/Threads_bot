# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Threads Worker.

Build:
    cd worker_app
    pyinstaller threads_worker.spec

Output: worker_app/dist/ThreadsWorker.exe
"""

import sys
from pathlib import Path
import customtkinter

block_cipher = None

# Collect customtkinter assets (themes, images)
ctk_path = Path(customtkinter.__file__).parent

a = Analysis(
    ['main.py'],
    pathex=[str(Path('.').resolve().parent)],  # repo root on path
    binaries=[],
    datas=[
        (str(ctk_path), 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'psutil',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test'],
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
    name='ThreadsWorker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # add icon path here if you have one
)
