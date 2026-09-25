#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键自动构建 Windows EXE

完整流水线：环境检查 → 编译 C++ 原生后端（可选）→ 自动化测试 → 清理旧产物
→ PyInstaller 打包（基于 AIComputerControl.spec）→ 校验产物。

用法：
    python scripts/build_exe.py                    # 完整流水线（含原生 DLL + 测试）
    python scripts/build_exe.py --skip-tests       # 跳过自动化测试
    python scripts/build_exe.py --skip-native      # 不编译 C++ 原生后端
    python scripts/build_exe.py --windowed         # 生成无控制台窗口的 GUI 程序
    python scripts/build_exe.py --no-upx           # 关闭 UPX 压缩
    python scripts/build_exe.py --name MyApp       # 自定义产物名
    python scripts/build_exe.py --no-clean         # 保留旧 build/dist（增量构建）
    python scripts/build_exe.py --install-pyinstaller  # PyInstaller 缺失时自动 pip 安装（默认行为）

退出码：0 成功；1 环境/构建失败；2 测试失败。
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "AIComputerControl.spec"
ENTRY = ROOT / "src" / "main.py"
NATIVE_BUILDER = ROOT / "src" / "core" / "native" / "build_native.py"
NATIVE_DLL = ROOT / "src" / "core" / "native" / "nodecalc_native.dll"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"


def log(msg, level="info"):
    colors = {"info": "\033[36m", "ok": "\033[32m", "warn": "\033[33m",
              "err": "\033[31m", "dim": "\033[90m", "reset": "\033[0m"}
    prefix = {"info": "[i]", "ok": "[√]", "warn": "[!]", "err": "[×]", "dim": "   "}
    # Windows 旧终端无 ANSI 支持时静默降级
    try:
        print(f"{colors.get(level, '')}{prefix.get(level, '')} {msg}{colors['reset']}")
    except Exception:
        print(f"{prefix.get(level, '')} {msg}")


def run(cmd, cwd=ROOT, env=None):
    """运行子进程，实时继承输出；返回是否成功。"""
    log(" ".join(str(c) for c in cmd), "dim")
    result = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env)
    return result.returncode == 0


def step(title):
    print()
    log(title, "info")


# ───────── 步骤 1：环境检查 ─────────

def check_environment(auto_install):
    step("步骤 1/5：环境检查")
    if sys.platform != "win32":
        log("PyInstaller 不支持跨平台编译，本脚本需在 Windows 上运行", "err")
        return False
    if not ENTRY.exists():
        log(f"入口文件不存在: {ENTRY}", "err")
        return False
    if not SPEC.exists():
        log(f"spec 文件不存在: {SPEC}", "err")
        return False
    log(f"Python {sys.version.split()[0]} @ {sys.executable}")

    # PyInstaller
    try:
        import PyInstaller  # noqa: F401
        log(f"PyInstaller 已安装（{PyInstaller.__version__}）", "ok")
    except ImportError:
        if not auto_install:
            log("PyInstaller 未安装，请先执行: pip install pyinstaller", "err")
            return False
        log("PyInstaller 未安装，正在自动安装…", "warn")
        if not run([sys.executable, "-m", "pip", "install", "pyinstaller",
                    "--disable-pip-version-check"]):
            log("PyInstaller 安装失败", "err")
            return False
        try:
            import PyInstaller  # noqa: F401
            log(f"PyInstaller 安装成功（{PyInstaller.__version__}）", "ok")
        except ImportError:
            log("PyInstaller 安装后仍无法导入", "err")
            return False
    return True


# ───────── 步骤 2：编译 C++ 原生后端 ─────────

def build_native(skip_native):
    step("步骤 2/5：C++ 原生后端")
    if skip_native:
        log("已通过 --skip-native 跳过（打包后运行时将使用纯 Python 后端）", "warn")
        return True

    gpp = shutil.which("g++")
    if not gpp:
        log("未找到 g++（MinGW），跳过原生 DLL；功能完整但节点计算性能较低", "warn")
        log("如需加速：安装 MinGW-w64 后重新运行本脚本，或手动执行 "
            "python src/core/native/build_native.py", "dim")
        return True

    log(f"使用编译器: {gpp}")
    if run([sys.executable, NATIVE_BUILDER]):
        if NATIVE_DLL.exists():
            size_mb = NATIVE_DLL.stat().st_size / 1024 / 1024
            log(f"原生 DLL 已就绪: nodecalc_native.dll ({size_mb:.2f} MB)", "ok")
            return True
        log("构建脚本返回成功但未找到 DLL", "err")
        return False
    log("原生 DLL 构建失败（可加 --skip-native 继续纯 Python 打包）", "err")
    return False


# ───────── 步骤 3：自动化测试 ─────────

def run_tests(skip_tests):
    step("步骤 3/5：自动化测试")
    if skip_tests:
        log("已通过 --skip-tests 跳过", "warn")
        return True
    runner = ROOT / "auto_tests" / "run_tests.py"
    if not runner.exists():
        log("未找到 auto_tests/run_tests.py，跳过测试", "warn")
        return True
    if run([sys.executable, runner]):
        log("自动化测试全部通过", "ok")
        return True
    log("自动化测试存在失败用例（加 --skip-tests 可强制继续打包）", "err")
    return False


# ───────── 步骤 4：清理与打包 ─────────

def clean_old(no_clean):
    if no_clean:
        log("已通过 --no-clean 保留旧 build/dist（增量构建）", "warn")
        return
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            log(f"删除旧目录: {d.relative_to(ROOT)}")
            shutil.rmtree(d, ignore_errors=True)


def package(windowed, no_upx, name):
    step("步骤 4/5：PyInstaller 打包（可能需要数分钟）")
    env = os.environ.copy()
    env["AIAPP_CONSOLE"] = "0" if windowed else "1"
    env["AIAPP_UPX"] = "0" if no_upx else "1"
    if name:
        env["AIAPP_NAME"] = name

    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm",
           "--distpath", str(DIST_DIR), "--workpath", str(BUILD_DIR)]
    if run(cmd, env=env):
        log("PyInstaller 打包完成", "ok")
        return True
    log("PyInstaller 打包失败，请查看上方日志", "err")
    return False


# ───────── 步骤 5：产物校验 ─────────

def verify_output(name):
    step("步骤 5/5：产物校验")
    app_name = name or "AIComputerControl"
    exe_path = DIST_DIR / f"{app_name}.exe"
    if not exe_path.exists():
        log(f"未找到预期产物: {exe_path}", "err")
        if DIST_DIR.exists():
            log(f"dist 目录实际内容: {[p.name for p in DIST_DIR.iterdir()]}", "dim")
        return False
    size_mb = exe_path.stat().st_size / 1024 / 1024
    log("=" * 56, "ok")
    log("构建成功！", "ok")
    log(f"产物: {exe_path}", "ok")
    log(f"大小: {size_mb:.2f} MB", "ok")
    log(f"原生后端: {'已包含 (nodecalc_native.dll)' if NATIVE_DLL.exists() else '未包含（纯 Python 回退）'}", "dim")
    log("=" * 56, "ok")
    return True


def main():
    parser = argparse.ArgumentParser(description="一键自动构建 Windows EXE")
    parser.add_argument("--skip-tests", action="store_true", help="跳过自动化测试")
    parser.add_argument("--skip-native", action="store_true", help="不编译 C++ 原生后端")
    parser.add_argument("--windowed", action="store_true", help="无控制台窗口的 GUI 程序")
    parser.add_argument("--no-upx", action="store_true", help="关闭 UPX 压缩")
    parser.add_argument("--no-clean", action="store_true", help="保留旧 build/dist")
    parser.add_argument("--name", default=None, help="自定义 EXE 文件名（不含 .exe）")
    parser.add_argument("--install-pyinstaller", action="store_true", default=True,
                        help="PyInstaller 缺失时自动安装（默认开启）")
    parser.add_argument("--no-install-pyinstaller", dest="install_pyinstaller",
                        action="store_false", help="PyInstaller 缺失时直接报错")
    args = parser.parse_args()

    log("AI Computer Control — 自动构建 EXE", "info")

    if not check_environment(args.install_pyinstaller):
        return 1
    if not build_native(args.skip_native):
        return 1
    if not run_tests(args.skip_tests):
        return 2
    clean_old(args.no_clean)
    if not package(args.windowed, args.no_upx, args.name):
        return 1
    if not verify_output(args.name):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
