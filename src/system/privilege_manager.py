# -*- coding: utf-8 -*-
"""
提权管理器（Privilege Manager）

让 AI 可以调用提权执行能力，以管理员 / root 权限运行命令。

设计要点：
- 平台感知：Windows 用 ShellExecuteW 'runas' 触发 UAC；Linux 用 sudo；macOS 预留（sudo 兜底 + osascript TODO）
- 双重授权：
    ① 项目层二次授权 —— ConfirmationManager.confirm()（GUI 弹窗 / 终端 input）
    ② OS 层系统授权 —— UAC 弹框 / sudo 密码（由操作系统强制）
- fail-safe：确认管理器未配置 → 拒绝；用户拒绝 → 拒绝；平台不支持 → 拒绝

注意：
- Windows 的 ShellExecuteW 启动的是独立提权进程，无法直接捕获 stdout/stderr。
  本实现通过临时 .bat 把输出重定向到临时文件，再轮询读回。
- Linux 的 sudo 需要免密（NOPASSWD）配置，否则 subprocess 无法交互输密码。
"""

import os
import sys
import time
import platform
import subprocess
import tempfile
from typing import Dict, Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


class PrivilegeManager:
    """提权管理器（单例）。"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.platform = platform.system()  # 'Windows' / 'Linux' / 'Darwin'
        logger.info(f"提权管理器初始化，当前平台: {self.platform}")

    # ──────────────────────────────────────────────
    # 公开入口
    # ──────────────────────────────────────────────

    def execute_privileged(self, command: str, reason: str = "",
                           timeout: int = 60, cwd: str = None) -> Dict[str, Any]:
        """以管理员/root 权限执行命令。

        参数:
            command: 要执行的命令
            reason:  提权原因（展示给用户，便于二次授权判断）
            timeout: 执行超时（秒）
            cwd:     工作目录

        返回:
            dict: {"success": bool, "message": str, "output": str, "returncode": int}
        """
        if not command or not command.strip():
            return {"success": False, "message": "命令不能为空", "output": "", "returncode": -1}

        # ── 第一层：项目二次授权 ──
        from src.system.confirmation import ConfirmationManager
        mgr = ConfirmationManager()
        if not mgr.is_configured():
            logger.warning("提权被拒绝：确认管理器未配置")
            return {"success": False,
                    "message": "提权被拒绝：确认管理器未配置（fail-safe）",
                    "output": "", "returncode": -1}

        desc = (f"【提权执行请求】\n原因: {reason or '未提供'}\n"
                f"平台: {self.platform}\n命令: {command}\n"
                f"超时: {timeout}s")
        logger.info(f"提权请求触发二次授权: {reason}")
        if not mgr.confirm(desc):
            logger.warning("用户拒绝提权请求")
            return {"success": False,
                    "message": "用户未授权提权操作（已拒绝）",
                    "output": "", "returncode": -1}

        logger.info("用户已授权提权，开始 OS 级提权执行")

        # ── 第二层：OS 系统授权 + 执行 ──
        try:
            # 特殊：提权验证（在系统目录创建/写/删 test.txt）
            if command == "__verify__":
                return self._do_verify(timeout, cwd)
            # 当前进程已具备特权（管理员/root）→ 直接执行，无需再触发 UAC/sudo
            if self.is_elevated():
                logger.info("当前进程已具备特权，直接执行命令（无需 OS 提权）")
                return self._exec_direct(command, timeout, cwd)
            if self.platform == "Windows":
                return self._exec_windows_uac(command, timeout, cwd)
            elif self.platform == "Linux":
                return self._exec_linux_sudo(command, timeout, cwd)
            elif self.platform == "Darwin":
                return self._exec_macos(command, timeout, cwd)
            else:
                return {"success": False,
                        "message": f"不支持的平台: {self.platform}",
                        "output": "", "returncode": -1}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "提权执行超时", "output": "", "returncode": -1}
        except Exception as e:
            logger.error(f"提权执行异常: {e}", exc_info=True)
            return {"success": False, "message": f"提权执行异常: {e}", "output": "", "returncode": -1}

    # ──────────────────────────────────────────────
    # Windows：ShellExecuteW 'runas' 触发 UAC
    # ──────────────────────────────────────────────

    def _exec_windows_uac(self, command: str, timeout: int, cwd: str) -> Dict[str, Any]:
        """Windows 提权：用 ShellExecuteW 'runas' 触发 UAC，输出重定向到临时文件后读回。"""
        import ctypes

        out_path = os.path.join(tempfile.gettempdir(), f"aiclaw_priv_{os.getpid()}.out")
        done_path = os.path.join(tempfile.gettempdir(), f"aiclaw_priv_{os.getpid()}.done")
        bat_path = os.path.join(tempfile.gettempdir(), f"aiclaw_priv_{os.getpid()}.bat")

        # .bat：执行命令 → 输出重定向 → 写完成标记（路径用 ASCII 双引号包裹）
        bat_content = (
            f'@echo off\n'
            f'chcp 65001 >nul\n'
            f'{command} > "{out_path}" 2>&1\n'
            f'echo done > "{done_path}"\n'
        )
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        try:
            # ShellExecuteW(hwnd, verb, file, params, dir, show)
            # verb='runas' 触发 UAC；show=0 (SW_HIDE) 隐藏窗口
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", bat_path, None, cwd or os.getcwd(), 0)
            # 返回值 > 32 表示成功启动（不代表命令执行完成）
            if ret <= 32:
                codes = {0: "内存不足", 2: "文件未找到", 3: "路径未找到",
                         5: "拒绝访问", 8: "无法启动", 26: "共享冲突",
                         27: "关联无效", 28: "DDE 超时", 31: "无关联程序",
                         32: "DLL 加载失败"}
                msg = codes.get(ret, f"UAC 提权失败或被用户拒绝（码: {ret}）")
                logger.warning(f"Windows UAC 提权失败: {msg}")
                return {"success": False, "message": msg, "output": "", "returncode": ret}

            # 轮询等待完成标记
            start = time.time()
            while not os.path.exists(done_path):
                if time.time() - start > timeout:
                    logger.warning("Windows 提权执行超时")
                    return {"success": False, "message": "提权执行超时",
                            "output": self._read_file(out_path), "returncode": -1}
                time.sleep(0.3)

            output = self._read_file(out_path)
            logger.info("Windows 提权执行完成")
            return {"success": True, "message": "提权执行完成（UAC 已授权）",
                    "output": output, "returncode": 0}
        finally:
            for p in (bat_path, out_path, done_path):
                try:
                    if os.path.exists(p):
                        os.unlink(p)
                except OSError:
                    pass

    # ──────────────────────────────────────────────
    # Linux：sudo
    # ──────────────────────────────────────────────

    def _exec_linux_sudo(self, command: str, timeout: int, cwd: str) -> Dict[str, Any]:
        """Linux 提权：用 sudo 执行。需要 sudoers 配置 NOPASSWD（免密）。"""
        # 先检查 sudo 免密是否可用
        check = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=10)
        if check.returncode != 0:
            return {"success": False,
                    "message": "sudo 需要密码：请在 /etc/sudoers 配置 NOPASSWD，或改用交互式终端手动执行",
                    "output": "", "returncode": -1}

        result = subprocess.run(
            ["sudo", "bash", "-c", command],
            capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"success": result.returncode == 0,
                "message": "提权执行完成" if result.returncode == 0 else f"命令返回非零: {result.returncode}",
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode}

    # ──────────────────────────────────────────────
    # macOS：预留（sudo 兜底 + osascript TODO）
    # ──────────────────────────────────────────────

    def _exec_macos(self, command: str, timeout: int, cwd: str) -> Dict[str, Any]:
        """macOS 提权：暂用 sudo 兜底，osascript 图形授权预留 TODO。

        TODO: 用 osascript 'do shell script "..." with administrator privileges'
              实现图形化授权框（类似 UAC），无需配置 sudoers 免密。
        """
        logger.warning("macOS 提权：osascript 图形授权尚未实现，暂用 sudo 兜底")
        # 先尝试 sudo 免密
        check = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=10)
        if check.returncode != 0:
            # TODO: 改用 osascript with administrator privileges
            return {"success": False,
                    "message": "macOS 提权暂用 sudo 兜底，需要密码（osascript 图形授权尚未实现）。"
                               "请配置 sudoers NOPASSWD 或等待 osascript 支持。",
                    "output": "", "returncode": -1}

        result = subprocess.run(
            ["sudo", "bash", "-c", command],
            capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"success": result.returncode == 0,
                "message": "提权执行完成（sudo 兜底）" if result.returncode == 0 else f"命令返回非零: {result.returncode}",
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode}

    # ──────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────

    @staticmethod
    def _read_file(path: str) -> str:
        """安全读取临时输出文件。"""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def is_elevated(self) -> bool:
        """检测当前进程是否已具备管理员/root 权限（真实检测，不弹框）。"""
        try:
            if self.platform == "Windows":
                import ctypes
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            else:  # Linux / macOS
                return os.geteuid() == 0
        except Exception as e:
            logger.warning(f"权限检测失败: {e}")
            return False

    def _exec_direct(self, command: str, timeout: int, cwd: str) -> Dict[str, Any]:
        """已提权时直接执行命令（无需再触发 UAC/sudo，仍已过项目二次授权）。"""
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd)
        return {"success": result.returncode == 0,
                "message": "提权执行完成（当前已具备特权）" if result.returncode == 0 else f"命令返回非零: {result.returncode}",
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode}

    def verify_privilege(self, target_dir: str = None) -> Dict[str, Any]:
        """真实提权验证：在系统目录创建 test.txt 写随机数并删除（需已具备特权）。

        Windows: C:\\Windows；Linux/macOS: /root
        普通权限会在创建时 PermissionError 失败 → 验证提权是否真实生效。
        """
        import random
        import string
        if target_dir is None:
            if self.platform == "Windows":
                target_dir = os.environ.get("SystemRoot", r"C:\Windows")
            else:
                target_dir = "/root"
        rand_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        filepath = os.path.join(target_dir, f"aiclaw_priv_test_{rand_suffix}.txt")
        content = str(random.randint(10**9, 10**10 - 1))
        steps = []
        try:
            with open(filepath, "w") as f:
                f.write(content)
            steps.append(f"创建+写入: {filepath}")
            with open(filepath, "r") as f:
                read_back = f.read()
            if read_back == content:
                steps.append(f"读回验证一致: {content}")
            else:
                steps.append(f"读回不一致: 期望 {content}, 实际 {read_back}")
            os.remove(filepath)
            steps.append(f"删除成功: {filepath}")
            return {"success": True,
                    "message": f"提权验证成功（在 {target_dir} 创建/写/删文件）",
                    "output": "\n".join(steps), "steps": steps, "returncode": 0}
        except PermissionError as e:
            steps.append(f"权限不足: {e}")
            return {"success": False,
                    "message": f"提权验证失败（权限不足，未提权）: {e}",
                    "output": "\n".join(steps), "steps": steps, "returncode": -1}
        except Exception as e:
            steps.append(f"异常: {e}")
            return {"success": False,
                    "message": f"提权验证异常: {e}",
                    "output": "\n".join(steps), "steps": steps, "returncode": -1}

    def _verify_shell_command(self) -> str:
        """返回用于 OS 提权（UAC/sudo）的 verify shell 命令。"""
        if self.platform == "Windows":
            target = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "aiclaw_priv_test.txt")
            return f'echo %RANDOM% > "{target}" && type "{target}" && del "{target}"'
        else:
            target = "/root/aiclaw_priv_test.txt"
            return f'echo $$ > "{target}" && cat "{target}" && rm -f "{target}"'

    def _do_verify(self, timeout: int, cwd: str) -> Dict[str, Any]:
        """提权验证分发：已提权用 Python verify，未提权用 shell 命令走 OS 提权。"""
        if self.is_elevated():
            logger.info("已提权，执行 Python verify（系统目录文件操作）")
            return self.verify_privilege()
        cmd = self._verify_shell_command()
        logger.info("未提权，用 shell verify 命令走 OS 提权")
        if self.platform == "Windows":
            return self._exec_windows_uac(cmd, timeout, cwd)
        elif self.platform == "Linux":
            return self._exec_linux_sudo(cmd, timeout, cwd)
        elif self.platform == "Darwin":
            return self._exec_macos(cmd, timeout, cwd)
        return {"success": False, "message": f"不支持的平台: {self.platform}",
                "output": "", "returncode": -1}

    def is_available(self) -> bool:
        """当前平台是否支持提权。"""
        return self.platform in ("Windows", "Linux", "Darwin")


if __name__ == "__main__":
    # 手动真实提权测试入口（须用 -m 以 src 作为包运行）：
    #   python -m src.system.privilege_manager [命令]
    # 会真实触发：项目二次授权（终端 input）→ OS 提权（UAC/sudo 或已提权直接执行）→ 打印结果
    import json as _json
    cmd = sys.argv[1] if len(sys.argv) > 1 else "__verify__"
    m = PrivilegeManager()
    print(f"平台: {m.platform}")
    print(f"当前已提权: {m.is_elevated()}")
    if cmd == "__verify__":
        print(f"待执行: 提权验证（在系统目录创建/写/删 test.txt）")
    else:
        print(f"待执行命令: {cmd}")
    # 终端模式确认（手动运行时用户可 input 确认）
    from src.system.confirmation import ConfirmationManager
    ConfirmationManager().configure_terminal(timeout=120)
    print("-" * 50)
    result = m.execute_privileged(cmd, reason="手动提权测试")
    print("-" * 50)
    print(_json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


__all__ = ["PrivilegeManager"]
