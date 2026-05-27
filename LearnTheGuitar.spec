# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('tracks.sqlite', '.'), ('accords', 'accords'), ('battle', 'battle'), ('chords', 'chords'), ('lrc', 'lrc'), ('menu_background_covers', 'menu_background_covers'), ('menu_background_music', 'menu_background_music'), ('pics', 'pics'), ('songs_audios', 'songs_audios'), ('songs_settings', 'songs_settings'), ('songs_texts', 'songs_texts'), ('styles', 'styles'), ('choose_screen.ui', '.'), ('practice_screen.ui', '.'), ('help_text.txt', '.'), ('icon.png', '.'), ('Lupa.png', '.'), ('moon.png', '.'), ('sun.png', '.')],
    hiddenimports=[],
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
    name='LearnTheGuitar',
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
    name='LearnTheGuitar',
)
