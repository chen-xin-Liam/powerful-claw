# -*- coding: utf-8 -*-
"""
高危操作检测器（平台感知）

根据当前操作系统（Windows / Linux）加载对应的黑名单关键词与敏感路径规则，
判断 AI 即将执行的命令 / 热键 / 窗口控制是否属于"高危/系统级"操作，
从而触发用户的二次授权确认。

设计要点：
- 平台探测：platform.system() 一次探测，按平台加载规则集
- 白名单优先：查看类命令（ls/cat/ps/whoami 等）免确认，保证日常体验
- 单词边界匹配：避免 "format" 误匹配 "information"
- 支持自定义黑名单追加与白名单覆盖（通过 .env 配置）
"""

import platform
import re
from typing import Tuple, List

from src.utils.logger import get_logger

logger = get_logger(__name__)


class HighRiskDetector:
    """高危操作检测器（单例）。"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, extra_blacklist: str = "", whitelist: str = ""):
        if self._initialized:
            # 已初始化：仅在提供了新配置时更新规则
            if extra_blacklist or whitelist:
                self._apply_custom_rules(extra_blacklist, whitelist)
            return
        self._initialized = True

        self.platform = platform.system()  # 'Windows' / 'Linux' / 'Darwin'
        logger.info(f"高危检测器初始化，当前平台: {self.platform}")

        # ── 通用白名单（查看类命令，跨平台免确认）──
        self.whitelist = {
            "ls", "dir", "pwd", "echo", "cat", "head", "tail", "less", "more",
            "ps", "whoami", "date", "time", "hostname", "ipconfig", "ifconfig",
            "systeminfo", "uname", "uptime", "free", "df", "top", "tasklist",
            "where", "which", "ver", "help", "history", "env", "set",
        }

        # ── 平台特定规则 ──
        if self.platform == "Windows":
            self.blacklist_keywords = self._windows_blacklist()
            self.sensitive_paths = self._windows_sensitive_paths()
        else:
            # Linux / macOS 统一走 Unix 规则
            self.blacklist_keywords = self._unix_blacklist()
            self.sensitive_paths = self._unix_sensitive_paths()

        # 危险热键（跨平台）
        self.dangerous_hotkeys = {
            ("alt", "f4"),           # 关闭窗口
            ("win",),                # Win 键 / 开始菜单
            ("cmd",),                # macOS Command 键
            ("ctrl", "alt", "delete"),     # Windows 安全选项（注：通常拦截不到）
            ("ctrl", "shift", "escape"),    # 任务管理器
            ("ctrl", "alt", "del"),        # 同上简写
            ("alt", "tab"),                # 切换窗口（可选，体验考虑保留为高危）
        }

        # 应用自定义规则
        self._apply_custom_rules(extra_blacklist, whitelist)

    # ──────────────────────────────────────────────
    # 规则集定义
    # ──────────────────────────────────────────────

    def _windows_blacklist(self) -> List[str]:
        return [
            "runas", "netsh", "reg ", "reg.exe", "taskkill", "taskkill /f",
            "sc ", "sc.exe", "shutdown", "format", "diskpart", "takeown",
            "icacls", "net user", "net localgroup", "net accounts",
            "del /f", "rmdir /s", "rd /s", "del /s", "powershell -enc",
            "powershell -encodedcommand", "cmd /c", "cmd /k", "bcdedit",
            "reg add", "reg delete", "reg import", "regedit",
            "wmic", "set ", "setx", "certutil", "bitsadmin",
            "net stop", "net start", "sc stop", "sc start",
            "schtasks /create", "schtasks /delete",
        ]

    def _windows_sensitive_paths(self) -> List[str]:
        return [
            "c:\\windows", "c:/windows", "system32", "syswow64",
            "hkey_", "hklm", "hkcu", "%systemroot%", "%windir%",
            "c:\\program files", "c:/program files",
            "c:\\boot", "c:/boot", "c:\\$recycle.bin",
            "%appdata%", "%programdata%",
        ]

    def _unix_blacklist(self) -> List[str]:
        return [
            "sudo", "su ", "su -", "rm -rf", "rm -fr", "dd ", "dd if=",
            "mkfs", "shutdown", "reboot", "poweroff", "halt",
            "systemctl", "service ", "apt", "apt-get", "yum", "dnf",
            "chmod 777", "chmod -r", "chown", "chown root",
            "kill -9", "kill -kill", "killall", "pkill",
            "iptables", "ufw", "firewall-cmd",
            "useradd", "userdel", "usermod", "passwd", "groupadd", "groupdel",
            "crontab", "visudo", "mount ", "umount",
            "wget ", "curl ",  # 下载执行类，视情况
            "chmod +x", "nohup",
            "update-rc.d", "systemctl enable", "systemctl disable",
        ]

    def _unix_sensitive_paths(self) -> List[str]:
        return [
            "/etc", "/root", "/usr", "/boot", "/var/log",
            "/proc", "/sys", "/dev",
            "~/.ssh", "/etc/shadow", "/etc/passwd", "/etc/sudoers",
            "/var/lib", "/opt",
        ]

    def _apply_custom_rules(self, extra_blacklist: str, whitelist: str):
        """应用 .env 配置的自定义黑名单追加与白名单覆盖。"""
        if extra_blacklist:
            for kw in extra_blacklist.split(","):
                kw = kw.strip().lower()
                if kw and kw not in self.blacklist_keywords:
                    self.blacklist_keywords.append(kw)
        if whitelist:
            for kw in whitelist.split(","):
                kw = kw.strip().lower()
                if kw:
                    self.whitelist.add(kw)

    # ──────────────────────────────────────────────
    # 检测方法
    # ──────────────────────────────────────────────

    @staticmethod
    def _normalize_cmd(cmd: str) -> str:
        """归一化命令字符串：小写 + 压缩多余空白。"""
        return re.sub(r"\s+", " ", cmd.strip().lower())

    def _is_whitelisted(self, cmd_normalized: str) -> bool:
        """是否命中白名单（查看类命令免确认）。"""
        if not cmd_normalized:
            return False
        first_token = cmd_normalized.split(" ", 1)[0]
        # 去掉可能的路径前缀（如 /usr/bin/ls → ls）
        first_token = first_token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return first_token in self.whitelist

    def is_high_risk_command(self, cmd: str) -> Tuple[bool, str]:
        """判断命令是否高危。返回 (是否高危, 命中原因)。"""
        if not cmd or not cmd.strip():
            return False, ""

        normalized = self._normalize_cmd(cmd)

        # 1. 白名单优先：查看类命令直接放行
        if self._is_whitelisted(normalized):
            return False, ""

        # 2. 黑名单关键词匹配（单词边界，避免 format 误匹配 information）
        for kw in self.blacklist_keywords:
            kw_norm = kw.strip().lower()
            if not kw_norm:
                continue
            # 关键词作为命令前缀，或作为独立 token 出现
            if normalized == kw_norm.rstrip() or normalized.startswith(kw_norm):
                return True, f"命中黑名单关键词: {kw_norm}"

            # 管道/分号后的子命令也要检查（如 echo x | sudo apt）
            for sep in ("|", ";", "&&", "||"):
                if sep in normalized:
                    parts = re.split(r"[|;]|&&|\|\|", normalized)
                    for part in parts:
                        part = part.strip()
                        if part and (part == kw_norm.rstrip() or part.startswith(kw_norm)):
                            return True, f"命中黑名单关键词（子命令）: {kw_norm}"

        # 3. 敏感路径匹配
        for path in self.sensitive_paths:
            if path.lower() in normalized:
                return True, f"访问系统敏感路径: {path}"

        return False, ""

    def is_high_risk_hotkey(self, keys) -> Tuple[bool, str]:
        """判断组合键是否高危。keys 可为 list/tuple/单个字符串。"""
        if not keys:
            return False, ""
        # 归一化为 tuple，全部小写
        if isinstance(keys, str):
            key_list = [k.strip().lower() for k in keys.replace("+", " ").split()]
        else:
            key_list = [str(k).strip().lower() for k in keys]
        key_tuple = tuple(key_list)

        for danger in self.dangerous_hotkeys:
            # 完全匹配
            if key_tuple == danger:
                return True, f"危险组合键: {'+'.join(danger)}"
            # 子集匹配（如 keys 含 win 键）
            if len(danger) == 1 and danger[0] in key_list:
                return True, f"危险修饰键: {danger[0]}"

        return False, ""

    def is_high_risk_operation(self, op_type: str, operation: dict) -> Tuple[bool, str]:
        """统一入口：判断操作是否高危。

        仅对 execute_command / keyboard_hotkey / window_control 三类检测，
        其余类型（鼠标移动、截图、YOLO 等）直接返回 (False, "")。
        """
        if not op_type:
            return False, ""

        op_type = op_type.lower()

        if op_type == "execute_command":
            cmd = operation.get("command", "") if isinstance(operation, dict) else ""
            return self.is_high_risk_command(str(cmd))

        if op_type == "keyboard_hotkey":
            keys = operation.get("keys", []) if isinstance(operation, dict) else []
            return self.is_high_risk_hotkey(keys)

        if op_type in ("window_control", "window_minimize", "window_close",
                       "window_maximize", "window_focus"):
            # 窗口控制类统一视为需确认
            return True, f"窗口控制操作: {op_type}"

        # keyboard_press 单键：检查是否危险单键（如 win）
        if op_type == "keyboard_press":
            key = operation.get("key", "") if isinstance(operation, dict) else ""
            return self.is_high_risk_hotkey([str(key)])

        return False, ""


__all__ = ["HighRiskDetector"]
