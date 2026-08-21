# -*- mode: python ; coding: utf-8 -*-


datas = [
    (
        "src/nightscout_widget/resources/default_config.toml",
        "nightscout_widget/resources",
    ),
    (
        "src/nightscout_widget/resources/default_secrets.toml",
        "nightscout_widget/resources",
    ),
]

a = Analysis(
    ["src/nightscout_widget/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NightscoutWidget",
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
    icon="assets/nightscout_widget.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NightscoutWidget",
)
