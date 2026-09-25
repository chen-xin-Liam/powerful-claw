# -*- mode: python ; coding: utf-8 -*-
import os

# ───────── 数据资源 ─────────
# 目标路径与源码目录结构保持一致（代码内用相对 __file__ 的 src/<dir> 定位）
_extra_datas = [
    ('src/web', 'web'),
    ('src/web_api', 'web_api'),
    ('src/web_monitor', 'web_monitor'),
    ('src/video_editor', 'video_editor'),
]

# nodecalc C++ 原生后端（缺失时 Python 侧自动回退纯 Python，不阻断打包）
_native_dll = os.path.join('src', 'core', 'native', 'nodecalc_native.dll')
if os.path.exists(_native_dll):
    _extra_datas.append((_native_dll, os.path.join('src', 'core', 'native')))

# ───────── 构建参数（可被环境变量覆盖，供 scripts/build_exe.py 调用） ─────────
# AIAPP_CONSOLE=0 生成无控制台窗口的 GUI 程序
_console = os.environ.get('AIAPP_CONSOLE', '1') != '0'
# AIAPP_UPX=0 关闭 UPX 压缩（杀软误报或压缩异常时使用）
_upx = os.environ.get('AIAPP_UPX', '1') != '0'
# AIAPP_NAME 自定义产物名
_app_name = os.environ.get('AIAPP_NAME', 'AIComputerControl')

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=_extra_datas,
    hiddenimports=[
        'websockets', 'soundcard', 'cv2', 'pyautogui', 'keyboard',
        'customtkinter', 'pydantic', 'pydantic_settings', 'dotenv',
        'cffi', 'src.core.native.native_backend',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 应用使用 CustomTkinter(tkinter) + PySide6，仅排除 PyQt5/PyQt6/matplotlib
    excludes=['PyQt5', 'PyQt6', 'matplotlib'],
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
    name=_app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=_upx,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=_console,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
