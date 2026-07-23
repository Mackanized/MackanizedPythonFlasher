# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Packaging Specification for PythonFlasher Standalone Executable.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

added_files = [
    ('web/dist', 'web/dist'),
] + collect_data_files('firmware')

hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'webview',
    'serial',
    'serial.tools.list_ports',
] + collect_submodules('ecus') + collect_submodules('adapters') + collect_submodules('protocols') + collect_submodules('infrastructure') + collect_submodules('application') + collect_submodules('domain')

# canlib is optional (the [kvaser] extra) and imported inside a try/except in
# adapters/kvaser.py, which PyInstaller's static analysis can miss. Only add
# it when actually installed in the build venv, so a build without the
# [kvaser] extra doesn't warn about a hidden import that can't be found.
try:
    import canlib  # noqa: F401
    hidden_imports += collect_submodules('canlib')
except ImportError:
    pass

a = Analysis(
    ['run_web.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='PythonFlasher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
