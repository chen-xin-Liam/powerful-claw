import subprocess
import threading
from typing import Optional, Callable, Generator
from queue import Queue

class CommandExecutor:
    """命令执行器，支持多种方式运行命令"""

    def __init__(self):
        self._process = None
        self._is_running = False

    def run_simple_command(self, command: str, timeout: int = 30) -> tuple[str, str, int]:
        """使用subprocess运行简单命令（非交互式）"""
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
        except subprocess.TimeoutExpired:
            return "", "命令执行超时", -1
        except Exception as e:
            return "", str(e), -1

    def run_command_stream(
        self,
        command: str,
        callback: Callable[[str], None],
        timeout: int = 60
    ) -> int:
        """运行命令并流式返回输出"""
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
            process.kill()
            callback("[ERROR] 命令执行超时")
            return -1
        except Exception as e:
            callback(f"[ERROR] {str(e)}")
            return -1
        finally:
            self._is_running = False
            self._process = None

    def run_interactive_command(
        self,
        command: str,
        inputs: list[str],
        callback: Callable[[str], None],
        timeout: int = 60
    ) -> str:
        """使用pexpect运行交互式命令"""
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
            return ""

    def run_advanced_command(
        self,
        command: str,
        callback: Callable[[str], None]
    ) -> int:
        """使用plumbum运行高级命令"""
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
            return -1
        except Exception as e:
            callback(f"[ERROR] {str(e)}\n")
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
            except:
                pass
            self._process = None

command_executor = CommandExecutor()