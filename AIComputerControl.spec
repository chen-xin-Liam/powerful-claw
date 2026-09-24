# -*- mode: python ; coding: utf-8 -*-
import os

# nodecalc C++ 原生后端（缺失时 Python 侧自动回退纯 Python，不阻断打包）
_native_dll = os.path.join('src', 'core', 'native', 'nodecalc_native.dll')
_extra_datas = [('src/web', 'web'), ('src/web_api', 'web_api')]
if os.path.exists(_native_dll):
    _extra_datas.append((_native_dll, os.path.join('src', 'core', 'native')))

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=_extra_datas,
    hiddenimports=['websockets', 'soundcard', 'cv2', 'pyautogui', 'keyboard', 'customtkinter', 'pydantic', 'pydantic_settings', 'dotenv', 'cffi', 'src.core.native.native_backend'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
    name='AIComputerControl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
