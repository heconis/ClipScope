# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_clipscope.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets\\sound\\notify.wav', 'assets\\sound'),
        ('assets\\icons\\booth.png', 'assets\\icons'),
        ('assets\\icons\\twitch.png', 'assets\\icons'),
        ('assets\\icons\\website.png', 'assets\\icons'),
        ('assets\\icons\\x.png', 'assets\\icons'),
        ('assets\\icons\\youtube.png', 'assets\\icons'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

splash = Splash(
    'assets\\splash\\clipscope_splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    [],
    exclude_binaries=False,
    name='ClipScope',
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
    icon='assets\\icon\\clipscope.ico',
)
