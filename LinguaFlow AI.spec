# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['translator_app\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('assets\\app_icon.ico', 'assets'), ('assets\\app_icon.png', 'assets'), ('assets\\dropdown_arrow.svg', 'assets')],
    hiddenimports=['keyring.backends.Windows'],
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
    name='LinguaFlow AI',
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
    version='version_info_app.txt',
    icon=['assets\\app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LinguaFlow AI',
)
