# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['talk_to_plot_ui.py'],
    pathex=[],
    binaries=[],
    datas=[('voicescript_settings.json', '.')],
    hiddenimports=['serial', 'HersheyFonts', 'speech_recognition'],
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
    name='talk_to_plot_ui',
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
app = BUNDLE(
    exe,
    name='talk_to_plot_ui.app',
    icon=None,
    bundle_identifier=None,
)
