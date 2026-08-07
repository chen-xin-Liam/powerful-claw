#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
GitHub Copilot SDK 封装服务。

将 ``github-copilot-sdk`` 的 async API 包装成与 ``AIService`` 一致的同步接口，
使其可与 OpenAI-compatible 路径透明互换：
  - ``chat_completion_stream(messages) -> Generator[(reasoning, content), ...]``
  - ``chat_sync(messages) -> str``
  - ``generate_title(prompt) -> str``

核心难点：Copilot SDK 的 ``CopilotClient`` / ``session`` 是 stateful 的，
一旦 ``start()`` 即绑定到创建它的事件循环。若用 ``asyncio.run`` 每次新建循环，
调用结束后循环被销毁，client 也会失效。

解决方案：
  - 启动一个 daemon 线程跑 ``loop.run_forever()`` 持久化事件循环
  - 主线程通过 ``asyncio.run_coroutine_threadsafe`` 把协程提交到后台循环
  - 流式 chunk 通过 ``queue.Queue`` 跨线程传回主线程的 generator

依赖：
  - pip install github-copilot-sdk
  - GITHUB_TOKEN 环境变量（或构造时传入 ``github_token``）
"""

import os
import sys
import asyncio
import threading
import queue as _queue
from typing import Dict, Generator, List, Optional, Tuple

# 项目根加入 sys.path，确保 ``import src.xxx`` 可解析
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.utils.errors import AppError, ExternalDependencyError
from src.utils.error_codes import ErrorCode
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CopilotService:
    """GitHub Copilot SDK 封装，提供与 AIService 一致的同步接口。

    通过 ``asyncio.run`` 在独立事件循环中执行 Copilot 的异步调用，
    对外暴露同步的 ``chat_completion_stream(messages) -> Generator`` 方法，
    与 OpenAI-compatible 路径完全透明互换。

    线程模型：
      - 一个后台 daemon 线程持有持久 ``asyncio`` 事件循环（``self._loop``）
      - ``self._client`` / ``self._session`` 在该循环上创建并复用
      - 主线程通过 ``run_coroutine_threadsafe`` 提交任务，``queue.Queue`` 回传流式 chunk
    """

    # 模块级缓存：避免每次实例化都触发 import。None 表示尚未探测过；
    # True/False 表示 copilot 是否可用。
    _copilot_module = None  # type: ignore[assignment]

    def __init__(
        self,
        model: str = "auto",
        github_token: Optional[str] = None,
        auto_approve_permissions: bool = True,
        system_prompt: Optional[str] = None,
    ):
        """初始化 Copilot 服务（懒加载，不在此处启动 client）。

        Args:
            model: Copilot 模型名，默认 ``"auto"`` 让 SDK 自动选择。
            github_token: GitHub OAuth token；不传则依赖 ``GITHUB_TOKEN`` 环境变量。
            auto_approve_permissions: 是否自动批准 SDK 的权限请求。
            system_prompt: 系统提示词；Copilot 无独立 system role API，
                会作为 ``[system]`` 标记的前置上下文注入到首轮 prompt。

        Raises:
            ExternalDependencyError: ``github-copilot-sdk`` 未安装时抛出，
                携带 ``E_EXT_DEPENDENCY_MISSING`` 错误码与 ``pip install`` 建议。
        """
        # 1) try import copilot，失败 → ExternalDependencyError
        #    缓存到类变量，后续实例化直接复用，避免重复 import 开销
        #    注意：缓存为 False（之前探测过 SDK 缺失）时仍必须抛错，
        #    否则 fail-safe 失效——后续实例化会静默成功，直到真正调用时才崩溃。
        if CopilotService._copilot_module is None:
            try:
                import copilot  # noqa: F401
                from copilot import CopilotClient  # noqa: F401
                from copilot.session import PermissionHandler  # noqa: F401
                CopilotService._copilot_module = copilot
            except ImportError as e:
                CopilotService._copilot_module = False
                raise ExternalDependencyError(
                    code=ErrorCode.E_EXT_DEPENDENCY_MISSING,
                    message="github-copilot-sdk 未安装，Copilot 服务不可用（pip install github-copilot-sdk）",
                    details={
                        "package": "github-copilot-sdk",
                        "import_name": "copilot",
                        "suggestion": "pip install github-copilot-sdk",
                    },
                    cause=e,
                ) from e
        elif CopilotService._copilot_module is False:
            # 之前已探测到 github-copilot-sdk 缺失，fail-safe：仍然抛错
            # （不重新 import 以避免副作用，但必须保持“未安装即不可用”的语义）
            raise ExternalDependencyError(
                code=ErrorCode.E_EXT_DEPENDENCY_MISSING,
                message="github-copilot-sdk 未安装，Copilot 服务不可用（pip install github-copilot-sdk）",
                details={
                    "package": "github-copilot-sdk",
                    "import_name": "copilot",
                    "suggestion": "pip install github-copilot-sdk",
                },
            )

        # 2) 保存配置
        self.model: str = model or "auto"
        self.github_token: Optional[str] = github_token
        self.auto_approve_permissions: bool = auto_approve_permissions
        self.system_prompt: Optional[str] = system_prompt

        # 3) 懒加载 client/session —— __init__ 不应有副作用（不启动网络连接）
        self._client = None
        self._session = None
        self._client_started: bool = False

        # 4) 设置 GITHUB_TOKEN 环境变量（如显式传入）
        #    SDK 内部会读取该变量；不传则不动，依赖既有环境
        if github_token:
            os.environ["GITHUB_TOKEN"] = github_token

        # 5) 并发保护：Copilot 单 session 不支持并发流，简单标记位即可
        self._busy: bool = False

        # 后台事件循环（懒启动）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

        logger.debug(
            "CopilotService 初始化完成（懒加载，尚未启动 client）model=%s auto_approve=%s",
            self.model,
            self.auto_approve_permissions,
        )

    # ──────────────────────────────────────────────────────────────
    # 客户端生命周期
    # ──────────────────────────────────────────────────────────────

    def _ensure_event_loop(self) -> asyncio.AbstractEventLoop:
        """启动后台线程运行 asyncio 事件循环，供 ``run_coroutine_threadsafe`` 使用。

        幂等：若已有运行中的循环则直接返回。循环生命周期与 service 实例一致，
        在 ``stop()`` 中显式关闭。
        """
        if self._loop is not None and self._loop.is_running():
            return self._loop

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_loop, name="CopilotServiceLoop", daemon=True
        )
        self._loop_thread.start()
        logger.debug("后台 asyncio 事件循环已启动 thread=%s", self._loop_thread.name)
        return self._loop

    def _run_loop(self) -> None:
        """后台线程入口：绑定事件循环并 ``run_forever``。"""
        assert self._loop is not None
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _ensure_client(self) -> None:
        """首次调用时启动 ``CopilotClient`` + 创建 session。后续复用。

        Note:
            规范草案中曾考虑用 ``asyncio.run(self._async_start())`` 启动，
            但 ``asyncio.run`` 会创建并销毁循环，导致绑定到该循环的 stateful client
            失效，无法被后续 ``send_streaming`` 复用。
            故此处改为：先 ``_ensure_event_loop()``，再 ``run_coroutine_threadsafe``
            在同一持久循环上执行 ``_async_start``。
        """
        if self._client_started:
            return

        loop = self._ensure_event_loop()
        fut = asyncio.run_coroutine_threadsafe(self._async_start(), loop)
        try:
            fut.result(timeout=30)  # 启动一般 < 5s，给 30s 余量
        except Exception as e:
            # 保留原始 traceback：raise ... from e 让上层能追溯
            logger.exception("CopilotClient 启动失败")
            raise RuntimeError(f"CopilotClient 启动失败: {e}") from e

        self._client_started = True
        logger.info("CopilotClient 已启动并创建 session model=%s", self.model)

    async def _async_start(self) -> None:
        """异步启动 client + session（在后台循环中执行）。"""
        from copilot import CopilotClient
        from copilot.session import PermissionHandler

        self._client = CopilotClient()
        await self._client.start()

        handler = (
            PermissionHandler.approve_all
            if self.auto_approve_permissions
            else getattr(PermissionHandler, "deny_all", PermissionHandler.approve_all)
        )
        self._session = await self._client.create_session(
            model=self.model,
            on_permission_request=handler,
        )

    # ──────────────────────────────────────────────────────────────
    # 对外接口（与 AIService 一致）
    # ──────────────────────────────────────────────────────────────

    def chat_completion_stream(
        self, messages: List[Dict[str, str]]
    ) -> Generator[Tuple[str, str], None, None]:
        """流式对话接口，与 ``AIService.chat_completion_stream`` 签名一致。

        Args:
            messages: OpenAI 格式消息列表，``[{"role": "system|user|assistant", "content": ...}]``。

        Yields:
            ``(reasoning_content, content)`` 元组。Copilot 不暴露推理过程，
            故 ``reasoning_content`` 始终为空字符串，``content`` 为增量文本。

        Raises:
            RuntimeError: 后台流式任务异常（SDK 抛出的非 ``AppError``）。
            AppError: 配置/依赖类异常向上传播。
        """
        # 1) 懒启动 client
        self._ensure_client()

        # 2) 并发保护：Copilot 单 session 不能同时跑两个流
        if self._busy:
            raise RuntimeError(
                "CopilotService 当前已有进行中的流式请求，请等待完成或调用 stop() 后重试"
            )
        self._busy = True

        # 3) 拼接 prompt：Copilot 不区分 role，按顺序追加 [role] 标记
        prompt = self._build_prompt(messages)

        # 4) 提交到后台循环，queue 桥接流式 chunk
        q: "_queue.Queue[object]" = _queue.Queue()
        fut = asyncio.run_coroutine_threadsafe(
            self._async_send_stream(prompt, q), self._loop
        )

        try:
            # 5) 主线程消费 queue，逐块 yield
            while True:
                item = q.get()
                if item is None:
                    # 完成标记
                    break
                if isinstance(item, BaseException):
                    # 后台协程抛出的异常（非 AppError），转 RuntimeError
                    raise RuntimeError(f"Copilot stream error: {item}") from item
                # reasoning_content="" content=chunk
                yield "", item  # type: ignore[misc]

            # 6) 检查后台任务本身的异常（如协程 try/except 未捕获到的）
            try:
                fut.result(timeout=1)  # 已完成，不阻塞
            except Exception as e:
                # fut 异常已经在 queue 路径里 raise 过；这里兜底防漏
                if not isinstance(e, RuntimeError):
                    raise RuntimeError(f"Copilot 后台任务异常: {e}") from e
        finally:
            self._busy = False

    async def _async_send_stream(self, prompt: str, q: "_queue.Queue[object]") -> None:
        """在后台 asyncio 循环中执行 ``session.send_streaming``。

        把每个 chunk 的 ``data.content`` 放入 queue；任何异常放入 queue；
        无论成功失败最后放入 ``None`` 作为完成标记。
        """
        try:
            assert self._session is not None, "Copilot session 未初始化"
            async for chunk in self._session.send_streaming(prompt):
                content = ""
                data = getattr(chunk, "data", None)
                if data is not None:
                    # 优先用属性访问，回退到 dict 取值，兼容不同 SDK 版本
                    if hasattr(data, "content") and getattr(data, "content", None):
                        content = data.content
                    elif isinstance(data, dict) and data.get("content"):
                        content = data["content"]
                if content:
                    q.put(content)
        except Exception as e:
            # 把异常对象放入队列，主线程取到后包装为 RuntimeError
            logger.exception("Copilot 流式接收异常")
            q.put(e)
        finally:
            q.put(None)  # 完成标记

    def _build_prompt(self, messages: List[Dict[str, str]]) -> str:
        """把 OpenAI 消息列表合成 Copilot 单一 prompt 字符串。

        - 若构造时传了 ``system_prompt``，前置为 ``[system]`` 标记段
        - 每条消息前加 ``[role]`` 标记，Copilot 会当作上下文理解
        - 空消息列表返回空串，由 SDK 自行处理
        """
        parts: List[str] = []

        # 显式 system_prompt 注入（与 messages 中的 system 互补）
        if self.system_prompt:
            parts.append(f"[system] {self.system_prompt}")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue
            parts.append(f"[{role}] {content}")

        return "\n\n".join(parts)

    def chat_sync(self, messages: List[Dict[str, str]]) -> str:
        """非流式：发送并等待完整响应。

        复用 ``chat_completion_stream``，把所有 content chunk 拼接返回。
        """
        chunks: List[str] = []
        for _reasoning, content in self.chat_completion_stream(messages):
            if content:
                chunks.append(content)
        return "".join(chunks)

    def generate_title(self, prompt: str) -> str:
        """生成对话标题，与 ``AIService.generate_title`` 接口一致。

        截断到 500 字以内请求，结果裁剪到 20 字以内。
        """
        title_prompt = (
            "请为以下内容生成一个简短标题（10字以内，无标点）：\n"
            f"{prompt[:500]}"
        )
        result = self.chat_sync([{"role": "user", "content": title_prompt}])
        return result.strip()[:20]

    # ──────────────────────────────────────────────────────────────
    # 资源释放
    # ──────────────────────────────────────────────────────────────

    def stop(self) -> None:
        """停止 client 并释放后台循环资源。幂等。"""
        # 1) 在后台循环里调用 client.stop()
        if self._loop is not None and self._loop.is_running():
            if self._client is not None:
                try:
                    fut = asyncio.run_coroutine_threadsafe(
                        self._client.stop(), self._loop
                    )
                    fut.result(timeout=5)
                except Exception as e:
                    logger.warning("Copilot client.stop() 异常: %s", e)

            # 2) 停止事件循环并 join 线程
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except RuntimeError:
                # 循环可能已关闭
                pass
            if self._loop_thread is not None:
                self._loop_thread.join(timeout=2)

        self._client = None
        self._session = None
        self._client_started = False
        self._loop = None
        self._loop_thread = None
        self._busy = False
        logger.debug("CopilotService 已停止")

    def __del__(self):
        # 析构时尽力释放资源，吞掉所有异常（解释器关闭时模块可能已卸载）
        try:
            self.stop()
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────
# 自测：不实际启动 Copilot（需订阅+网络），仅验证 import 与错误路径
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import unittest.mock as _mock

    def _test_class_definition() -> None:
        print("[1] 验证 CopilotService 类可定义 ...", end=" ")
        assert CopilotService is not None
        assert hasattr(CopilotService, "chat_completion_stream")
        assert hasattr(CopilotService, "chat_sync")
        assert hasattr(CopilotService, "generate_title")
        assert hasattr(CopilotService, "stop")
        print("OK")

    def _test_missing_dependency_raises() -> None:
        print("[2] 验证未安装 github-copilot-sdk 时抛 ExternalDependencyError ...", end=" ")
        # 通过 sys.modules 注入 None 模拟 SDK 缺失：
        # `import copilot` 检测到 sys.modules['copilot'] is None 时抛 ImportError
        saved_copilot = sys.modules.get("copilot")
        saved_session = sys.modules.get("copilot.session")
        # 同时清空类级缓存，强制走 import 探测路径
        saved_module_cache = CopilotService._copilot_module
        CopilotService._copilot_module = None
        try:
            with _mock.patch.dict(
                sys.modules,
                {"copilot": None, "copilot.session": None},
            ):
                raised = False
                try:
                    CopilotService()
                except ExternalDependencyError as e:
                    raised = True
                    assert e.code == ErrorCode.E_EXT_DEPENDENCY_MISSING, (
                        f"错误码不匹配: {e.code}"
                    )
                    assert "github-copilot-sdk" in str(e), f"消息缺少包名: {e}"
                assert raised, "期望抛出 ExternalDependencyError，但未抛出"
            print("OK")
        finally:
            # 还原 sys.modules 与类级缓存
            for _k, _v in (("copilot", saved_copilot), ("copilot.session", saved_session)):
                if _v is None:
                    sys.modules.pop(_k, None)
                else:
                    sys.modules[_k] = _v
            CopilotService._copilot_module = saved_module_cache

    def _test_prompt_assembly() -> None:
        print("[3] 验证 _build_prompt 拼接 ...", end=" ")
        # 不实例化（避免触发 import），用 object.__new__ 绕过 __init__
        svc = object.__new__(CopilotService)
        svc.system_prompt = "你是助手"
        prompt = svc._build_prompt([
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": ""},
        ])
        assert "[system] 你是助手" in prompt
        assert "[system] sys" in prompt
        assert "[user] hello" in prompt
        assert "[assistant] hi" in prompt
        print("OK")

    _test_class_definition()
    _test_missing_dependency_raises()
    _test_prompt_assembly()
    print("\n所有自测通过。")
