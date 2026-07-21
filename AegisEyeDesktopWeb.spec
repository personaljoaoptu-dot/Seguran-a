# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['AegisEyeDesktopWeb.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('desktop_ui.html', '.'), 
        ('frontend/style.css', '.'),
        ('yolov8n.pt', '.'),
        ('config_roi.json', '.'),
        ('cameras.json', '.')
    ],
    hiddenimports=['pg8000', 'cv2', 'ultralytics', 'webview', 'torch', 'torchvision'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AegisEyeDesktopWeb',
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
