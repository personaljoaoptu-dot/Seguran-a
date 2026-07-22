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
    hiddenimports=[
        'unicodedata',
        'pg8000',
        'cv2',
        'ultralytics',
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'torch',
        'torchvision',
        'av',
        'http.server',
        'urllib.parse',
        'urllib.request'
    ],
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
    [],
    exclude_binaries=True,
    name='AegisEyeDesktopWeb',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AegisEyeDesktopWeb',
)

