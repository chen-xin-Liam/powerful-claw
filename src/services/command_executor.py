import os
import platform
import re
import shlex
import subprocess
import threading
from typing import Callable, List, Optional, Tuple

from src.utils.logger import get_logger
from src.utils.errors import ValidationError
from src.utils.error_codes import ErrorCode

logger = get_logger(__name__)

# Shell 语法特征：本服务层没有交互式授权管理器，出现即默认拒绝。
# 包含分隔符、分组括号/花括号、重定向、换行、反斜杠转义、$ 变量/展开、!、**。
_SHELL_FEATURE_RE = re.compile(r"[|;&(){}<>\n\r!\\$]|\*\*|(?:^|\s)~\S")
# 命令替换：本服务无确认管理器，一律拒绝（避免注入逃逸）
_CMD_SUBST_RE = re.compile(r"`|\$\(|\$\{")

IS_WINDOWS = platform.system() == "Windows"


def has_command_substitution(command: str) -> bool:
    """是否含反引号 / $( ) / ${ } 命令替换。"""
    return bool(_CMD_SUBST_RE.search(command))


def needs_shell(command: str) -> bool:
    """命令是否含 shell 语法特征（默认拒绝面，而非"需要 shell"的放行面）。"""
    return bool(_SHELL_FEATURE_RE.search(command))


# 单条命令最大长度（字节）：限制 shlex 解析工作量，防二次复杂度 DoS
_MAX_COMMAND_LEN = 4096


def default_command_gate(command: str) -> Tuple[bool, str]:
    """默认命令风险闸门（默认拒绝模型）。

    返回 (allowed, reason)：
    - 命令替换（反引号/$()）→ 拒绝；
    - POSIX：含任何 shell 语法特征 → 拒绝（本层无授权管理器，
      需要 shell 的高级命令必须由带确认能力的自定义闸门放行）；
    - POSIX：命令经 shlex（与执行层同一词法分析）切分为 argv，
      程序名必须在只读命令白名单内，且经高危/敏感路径检测；
    - Windows：保留高危黑名单检测后经 shell 执行（平台命令模型不同）。
    """
    if has_command_substitution(command):
        return False, "命令包含命令替换（反引号/$()），存在注入风险"

    if len(command) > _MAX_COMMAND_LEN:
        return False, f"命令长度超过 {_MAX_COMMAND_LEN} 字节上限"

    if "\x00" in command:
        return False, "命令包含非法空字节"

    try:
        from src.system.high_risk_detector import HighRiskDetector

        detector = HighRiskDetector()
    except Exception as e:  # 检测器不可用：fail-closed
        logger.error(f"命令风险检测器不可用，按拒绝处理: {e}")
        return False, "风险检测失败"

    if IS_WINDOWS:
        try:
            is_high, reason = detector.is_high_risk_command(command)
        except Exception as e:
            logger.error(f"命令风险检测器异常，按拒绝处理: {e}")
            return False, "风险检测失败"
        if is_high:
            return False, reason
        return True, "shell"

    # POSIX：含 shell 特征的命令默认拒绝
    if needs_shell(command):
        return False, ("命令包含 shell 语法特征，默认拒绝"
                       "（需 shell 的命令须经带授权能力的自定义闸门放行）")

    argv = _argv_for(command)
    if not argv:
        return False, "命令无法解析为 argv"

    # argv[0] 必须是 PATH 中的裸程序名：拒绝 ./ls、/tmp/ls 等同名伪装
    program_token = argv[0]
    if "/" in program_token or "\\" in program_token:
        return False, "仅允许通过 PATH 调用程序（拒绝路径形式 argv[0]）"

    # 以真实 argv（与执行层同一 lexer 的产物）再过高危/敏感路径检测
    try:
        is_high, reason = detector.is_high_risk_command(" ".join(argv))
    except Exception as e:
        logger.error(f"命令风险检测器异常，按拒绝处理: {e}")
        return False, "风险检测失败"
    if is_high:
        return False, reason

    # 逐参数组件级保护：SSH 私钥、.env、credentials、系统敏感路径等
    for token in argv[1:]:
        if detector.is_protected_path_token(token):
            return False, f"参数指向受保护内容: {token}"

    program = program_token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if program not in detector.whitelist:
        return False, f"程序 {program} 不在允许列表内"

    return True, "argv"


def _argv_for(command: str) -> List[str]:
    """将无元字符命令切分为 argv（POSIX）。Windows 下返回空表示沿用 shell。"""
    if IS_WINDOWS:
        return []
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return []


def _resolve_safe_cwd(cwd: Optional[str]) -> Optional[str]:
    """默认闸门下 cwd 必须位于项目根之内（None → 项目根）；
    项目外目录返回 None，防止借助 AI 可控 cwd 读取任意目录内容。"""
    from src.utils.net_auth import project_root

    root = os.path.abspath(project_root())
    if cwd is None:
        return root
    target = os.path.abspath(cwd)
    if target == root or target.startswith(root + os.sep):
        return target
    return None


class CommandExecutor:
    """命令执行器，支持多种方式运行命令。

    所有执行方法均先经过命令风险闸门（可通过 :meth:`set_gate` 替换）：
    命令替换/高危命令在本服务直接拒绝；返回结构与历史版本保持一致。
    """

    def __init__(self, gate: Optional[Callable[[str], Tuple[bool, str]]] = None):
        self._process = None
        self._is_running = False
        self._gate = gate or default_command_gate

    def set_gate(self, gate: Callable[[str], Tuple[bool, str]]) -> None:
        """替换命令风险闸门（主要用于测试）。"""
        self._gate = gate

    def _check(self, command: str) -> Tuple[bool, str, str]:
        """返回 (allowed, mode, reason)。mode ∈ argv/shell。"""
        allowed, reason = self._gate(command)
        if not allowed:
            return False, "", reason
        mode = "shell" if (IS_WINDOWS or needs_shell(command)) else "argv"
        return True, mode, ""

    def run_simple_command(self, command: str, timeout: int = 30,
                           cwd: Optional[str] = None) -> Tuple[str, str, int]:
        """使用subprocess运行简单命令（非交互式）。

        返回 (stdout, stderr, returncode)。
        """
        # 输入校验
        if not isinstance(command, str) or not command.strip():
            raise ValidationError(
                ErrorCode.E_VAL_MISSING_REQUIRED,
                "command 不能为空字符串",
                details={"arg": "command"},
            )
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValidationError(
                ErrorCode.E_VAL_OUT_OF_RANGE,
                f"timeout 必须是正整数，实际收到 {timeout}",
                details={"arg": "timeout", "value": timeout},
            )
        if cwd is not None and not isinstance(cwd, str):
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"cwd 必须为字符串，实际收到 {type(cwd).__name__}",
                details={"arg": "cwd"},
            )

        allowed, mode, reason = self._check(command)
        if not allowed:
            logger.warning(f"命令被风险闸门拒绝: {reason}")
            return "", f"命令被拒绝: {reason}", -1

        # 默认闸门：cwd 锁定项目根之内；自定义闸门不受此约束
        effective_cwd = cwd
        if self._gate is default_command_gate:
            effective_cwd = _resolve_safe_cwd(cwd)
            if effective_cwd is None:
                msg = f"cwd {cwd} 不在项目根之内，默认拒绝"
                logger.warning(msg)
                return "", f"命令被拒绝: {msg}", -1

        argv = _argv_for(command)
        try:
            if mode == "argv" and argv:
                result = subprocess.run(
                    argv,
                    shell=False,
                    cwd=effective_cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=effective_cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='replace'
                )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            # 软失败：超时返回错误码，不抛异常（保留原 API 契约）
            logger.warning(f"命令执行超时（{timeout}s）: {command}")
            return "", f"命令执行超时（{timeout}s）", -1
        except (FileNotFoundError, OSError) as e:
            logger.error(f"命令无法执行: {command} - {e}")
            return "", f"命令不可执行: {e}", -1
        # 不再捕获 Exception 兜底，让真正未预期的错误冒泡由调用方决定

    def run_command_stream(
        self,
        command: str,
        callback: Callable[[str], None],
        timeout: int = 60
    ) -> int:
        """运行命令并流式返回输出"""
        if not isinstance(command, str) or not command.strip():
            raise ValidationError(
                ErrorCode.E_VAL_MISSING_REQUIRED,
                "command 不能为空字符串",
                details={"arg": "command"},
            )

        allowed, mode, reason = self._check(command)
        if not allowed:
            callback(f"[ERROR] 命令被拒绝: {reason}")
            logger.warning(f"流式命令被拒绝: {reason}")
            return -1

        argv = _argv_for(command)
        process = None
        try:
            popen_args = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if mode == "argv" and argv:
                process = subprocess.Popen(argv, shell=False, **popen_args)
            else:
                process = subprocess.Popen(command, shell=True, **popen_args)

            self._process = process
            self._is_running = True

            def read_output(pipe, is_error=False):
                while self._is_running and process.poll() is None:
                    line = pipe.readline()
                    if line:
                        prefix = "[ERROR] " if is_error else ""
                        callback(prefix + line)

            stdout_thread = threading.Thread(target=read_output, args=(process.stdout, False))
            stderr_thread = threading.Thread(target=read_output, args=(process.stderr, True))

            stdout_thread.start()
            stderr_thread.start()

            process.wait(timeout=timeout)
            self._is_running = False

            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)

            return process.returncode

        except subprocess.TimeoutExpired:
            if process is not None:
                process.kill()
            callback("[ERROR] 命令执行超时")
            logger.warning(f"流式命令执行超时（{timeout}s）: {command}")
            return -1
        except (FileNotFoundError, OSError) as e:
            callback(f"[ERROR] 命令不可执行: {e}")
            logger.error(f"流式命令无法执行: {command} - {e}")
            return -1
        finally:
            self._is_running = False
            self._process = None

    def run_interactive_command(
        self,
        command: str,
        inputs: List[str],
        callback: Callable[[str], None],
        timeout: int = 60
    ) -> str:
        """使用pexpect运行交互式命令"""
        if not isinstance(command, str) or not command.strip():
            raise ValidationError(
                ErrorCode.E_VAL_MISSING_REQUIRED,
                "command 不能为空字符串",
                details={"arg": "command"},
            )

        allowed, mode, reason = self._check(command)
        if not allowed:
            callback(f"[ERROR] 命令被拒绝: {reason}\n")
            return ""

        try:
            import pexpect

            spawn_target = _argv_for(command) if mode == "argv" else command
            child = pexpect.spawn(spawn_target, timeout=timeout, encoding='utf-8')
            output = []

            def read_until_prompt(pattern):
                try:
                    index = child.expect(pattern, timeout=timeout)
                    if child.before:
                        output.append(child.before)
                    return index
                except pexpect.TIMEOUT:
                    output.append(str(child.before))
                    return -1

            callback(f"[INFO] 开始执行: {command}\n")

            for inp in inputs:
                if inp.strip():
                    callback(f"[INPUT] {inp}\n")
                    child.sendline(inp)
                    child.expect(pexpect.EOF, timeout=timeout)

            child.close()
            return ''.join(output)

        except ImportError:
            callback("[WARNING] pexpect未安装，使用简单方式执行\n")
            stdout, stderr, code = self.run_simple_command(command)
            callback(stdout)
            if stderr:
                callback(f"[ERROR] {stderr}")
            return stdout
        except Exception as e:
            callback(f"[ERROR] {str(e)}\n")
            logger.error(f"交互式命令执行失败: {command} - {e}", exc_info=True)
            return ""

    def run_advanced_command(
        self,
        command: str,
        callback: Callable[[str], None]
    ) -> int:
        """使用plumbum运行高级命令"""
        if not isinstance(command, str) or not command.strip():
            raise ValidationError(
                ErrorCode.E_VAL_MISSING_REQUIRED,
                "command 不能为空字符串",
                details={"arg": "command"},
            )

        allowed, mode, reason = self._check(command)
        if not allowed:
            callback(f"[ERROR] 命令被拒绝: {reason}\n")
            return -1

        try:
            from plumbum import local, CommandNotFound

            cmd = local[command.split()[0]]
            args = command.split()[1:]

            callback(f"[INFO] 使用plumbum执行: {command}\n")

            proc = cmd.popen(*args)
            self._process = proc
            self._is_running = True

            while self._is_running and proc.poll() is None:
                line = proc.readline()
                if line:
                    callback(line)

            return proc.poll()

        except ImportError:
            callback("[WARNING] plumbum未安装，使用subprocess执行\n")
            return self.run_command_stream(command, callback)
        except CommandNotFound:
            callback(f"[ERROR] 命令未找到: {command.split()[0]}\n")
            logger.warning(f"plumbum: 命令未找到: {command.split()[0]}")
            return -1
        except Exception as e:
            callback(f"[ERROR] {str(e)}\n")
            logger.error(f"plumbum 执行失败: {command} - {e}", exc_info=True)
            return -1
        finally:
            self._is_running = False
            self._process = None

    def stop(self):
        """停止当前运行的命令"""
        self._is_running = False
        if self._process:
            try:
                if hasattr(self._process, 'kill'):
                    self._process.kill()
                elif hasattr(self._process, 'terminate'):
                    self._process.terminate()
            except (ProcessLookupError, OSError) as e:
                # 进程已结束或无权限，无需静默吞掉
                logger.debug(f"停止命令时进程已结束或无法终止: {e}")
            finally:
                self._process = None


command_executor = CommandExecutor()
