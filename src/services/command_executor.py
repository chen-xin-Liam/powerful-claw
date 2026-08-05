import subprocess
import threading
from typing import Callable, List, Tuple

from src.utils.logger import get_logger
from src.utils.errors import ValidationError
from src.utils.error_codes import ErrorCode

logger = get_logger(__name__)


class CommandExecutor:
    """命令执行器，支持多种方式运行命令"""

    def __init__(self):
        self._process = None
        self._is_running = False

    def run_simple_command(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
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

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as e:
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

        process = None
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

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

        try:
            import pexpect

            child = pexpect.spawn(command, timeout=timeout, encoding='utf-8')
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

        try:
            from plumbum import local, CommandNotFound
            from plumbum.cmd import sh

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