# -*- coding: utf-8 -*-
"""
确认管理器（线程安全）

为高危操作提供"二次授权确认"机制，支持两种模式：
- GUI 模式：子线程发起确认请求 → 队列传递 → 主线程弹出 messagebox.askyesno → 结果回传
            （messagebox 必须在主线程调用，故用 root.after 轮询桥接）
- 终端模式：直接 input() 提示用户（阻塞调用线程，合理）

安全默认（fail-safe）：
- 确认超时 → 拒绝（False）
- 管理器未配置（未调用 configure_*） → 拒绝（False）
- input 被 Ctrl+C/EOF 中断 → 拒绝（False）
"""

import queue
import threading
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfirmationManager:
    """确认管理器（单例）。"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._mode: str = "unconfigured"   # "gui" / "terminal" / "unconfigured"
        self._root = None                   # tkinter root（GUI 模式）
        self._gui_queue: Optional[queue.Queue] = None  # GUI 请求队列
        self._default_timeout: int = 30

    # ──────────────────────────────────────────────
    # 配置方法
    # ──────────────────────────────────────────────

    def configure_gui(self, root, timeout: int = 30) -> None:
        """配置 GUI 模式：注入 tkinter root，启动 after 轮询。"""
        self._mode = "gui"
        self._root = root
        self._default_timeout = timeout
        self._gui_queue = queue.Queue()
        logger.info("确认管理器: GUI 模式已配置")
        self._start_polling()

    def configure_terminal(self, timeout: int = 30) -> None:
        """配置终端模式。"""
        self._mode = "terminal"
        self._default_timeout = timeout
        logger.info("确认管理器: 终端模式已配置")

    def is_configured(self) -> bool:
        return self._mode != "unconfigured"

    # ──────────────────────────────────────────────
    # GUI 轮询（主线程）
    # ──────────────────────────────────────────────

    def _start_polling(self) -> None:
        """在主线程启动 after 轮询，处理待确认请求。"""
        if self._root is None:
            return
        try:
            self._poll_gui_requests()
        except Exception as e:
            logger.error(f"确认管理器轮询启动失败: {e}")

    def _poll_gui_requests(self) -> None:
        """主线程：取出请求 → 弹窗 → 回传结果。"""
        if self._gui_queue is None or self._root is None:
            return
        try:
            while True:
                try:
                    message, response_queue = self._gui_queue.get_nowait()
                except queue.Empty:
                    break
                # 在主线程弹出确认框
                approved = self._show_gui_dialog(message)
                response_queue.put(approved)
        except Exception as e:
            logger.error(f"GUI 确认轮询异常: {e}")
        finally:
            # 继续轮询（每 100ms）
            try:
                self._root.after(100, self._poll_gui_requests)
            except Exception:
                # root 可能已销毁
                pass

    def _show_gui_dialog(self, message: str) -> bool:
        """在主线程弹出 messagebox.askyesno。"""
        try:
            # 延迟导入，避免无 GUI 环境加载 tkinter 失败
            from tkinter import messagebox
            display = f'⚠ 高危操作确认\n\nAI 即将执行以下高危操作，是否允许？\n\n{message}\n\n点击「是」放行，点击「否」拒绝。'
            return bool(messagebox.askyesno("高危操作二次授权", display))
        except Exception as e:
            logger.error(f"GUI 确认弹窗失败: {e}")
            return False

    # ──────────────────────────────────────────────
    # 确认入口（任意线程调用）
    # ──────────────────────────────────────────────

    def confirm(self, message: str, timeout: Optional[int] = None) -> bool:
        """请求用户二次确认。返回 True=放行，False=拒绝。

        任何模式下，异常/超时/未配置 都返回 False（fail-safe）。
        """
        if not self.is_configured():
            logger.warning("确认管理器未配置，高危操作默认拒绝")
            return False

        if timeout is None:
            timeout = self._default_timeout

        if self._mode == "gui":
            return self._confirm_gui(message, timeout)
        else:
            return self._confirm_terminal(message, timeout)

    def _confirm_gui(self, message: str, timeout: int) -> bool:
        """GUI 模式：子线程入队 → 阻塞等待主线程弹窗结果。"""
        if self._gui_queue is None:
            return False
        response_queue: queue.Queue = queue.Queue()
        try:
            self._gui_queue.put((message, response_queue))
            # 阻塞等待主线程回传结果，超时拒绝
            return bool(response_queue.get(timeout=timeout))
        except queue.Empty:
            logger.warning(f"GUI 确认超时（{timeout}s），默认拒绝")
            return False
        except Exception as e:
            logger.error(f"GUI 确认异常: {e}")
            return False

    def _confirm_terminal(self, message: str, timeout: int) -> bool:
        """终端模式：直接 input 提示。"""
        try:
            prompt = (
                f"\n{'=' * 50}\n"
                f"⚠ [高危操作二次授权]\n{message}\n"
                f"{'=' * 50}\n"
                f"确认执行此高危操作？(yes/no): "
            )
            answer = input(prompt)
            return answer.strip().lower() in ("y", "yes", "是", "确认")
        except (EOFError, KeyboardInterrupt):
            print("\n（已取消，高危操作被拒绝）")
            return False
        except Exception as e:
            logger.error(f"终端确认异常: {e}")
            return False


__all__ = ["ConfirmationManager"]
