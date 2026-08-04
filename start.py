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

    # ✅ 用 PowerShell 无窗口执行脚本（核心修复）
    cmd = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-WindowStyle", "Hidden",
        "-File", ps1_path
    ]

    subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

if __name__ == "__main__":
    run_in_background()
    sys.exit(0)