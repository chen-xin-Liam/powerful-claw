"""
启动器入口

通过 PowerShell 无窗口运行 start_app.ps1。
本文件作为打包入口（start.exe），不依赖 src.utils 包，
直接以 [Exxxx] 错误码字符串形式输出，与内部 AppError 体系保持编号一致。
"""

import subprocess
import sys
import os


def run_in_background():
    # 获取程序所在目录（兼容 py 运行和 exe 打包）
    if getattr(sys, 'frozen', False):
        current_dir = os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))

    # 正确文件名：start_app.ps1
    ps1_path = os.path.join(current_dir, "start_app.ps1")

    # 校验启动脚本是否存在
    if not os.path.isfile(ps1_path):
        print(f"[E4001][start] 启动脚本不存在: {ps1_path}")
        print("  建议: 重新安装程序，或确认 start_app.ps1 在程序目录下")
        sys.exit(2)

    # ✅ 用 PowerShell 无窗口执行脚本（核心修复）
    cmd = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-WindowStyle", "Hidden",
        "-File", ps1_path
    ]

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except FileNotFoundError:
        print("[E7002][start] 未找到 powershell.exe")
        print("  建议: 请确认系统 PATH 中包含 PowerShell（通常位于 C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\）")
        sys.exit(2)
    except OSError as e:
        print(f"[E7001][start] 启动 PowerShell 失败: {e}")
        print("  建议: 检查 powershell.exe 是否可执行，或以管理员身份运行")
        sys.exit(2)


if __name__ == "__main__":
    run_in_background()
    sys.exit(0)
