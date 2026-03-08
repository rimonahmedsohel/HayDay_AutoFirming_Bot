# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Paths
project_dir = os.path.abspath('.')
images_dir = os.path.join(project_dir, 'images')
minitouch_file = os.path.join(project_dir, 'minitouch')
adb_dir = os.path.join(project_dir, 'adb')

a = Analysis(
    ['hfb_app.py'],
    pathex=[project_dir],
    binaries=[],
    datas=[
        (images_dir, 'images'),
        (minitouch_file, '.'),
        (adb_dir, 'adb'),
    ],
    hiddenimports=[
        'start',
        'planting',
        'harvesting',
        'sellingCrops',
        'crash_handler',
        'zoom',
        'adb_path',
        'cv2',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['keyboard'],
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
    name='HFB',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
