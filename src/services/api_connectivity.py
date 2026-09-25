"""API 连通性测试

在 AI 提供方配置后、使用前，快速验证 API 是否可达、Key 是否有效。
支持 OpenAI 兼容端点、Ollama、本地模型；Copilot 返回提示信息。
"""
import time
import requests
from typing import Optional, Dict, Any

from src.config.ai_providers import AIProvider


def check_api_connectivity(provider: AIProvider, timeout: int = 10) -> Dict[str, Any]:
    """测试单个 AI 提供方的连通性

    返回字典：
        {
            "success": bool,           # 是否可用
            "status": str,             # "success" / "invalid_key" / "network_error" / "config_error" / "skip"
            "message": str,            # 人类可读描述
            "response_time_ms": float, # 网络往返耗时（仅网络请求成功时）
            "provider": str,           # 提供方名称
            "model": str,              # 测试用模型
        }
    """
    result = {
        "success": False,
        "status": "unknown",
        "message": "",
        "response_time_ms": None,
        "provider": provider.name,
        "model": provider.default_model or "",
    }

    # ── 本地模型（无需网络）──
    if provider.name.lower() == "local" or provider.base_url.lower() == "local":
        result["status"] = "skip"
        result["message"] = "本地模型无需网络测试，跳过"
        return result

    # ── Ollama ──
    base = (provider.base_url or "").lower()
    if "ollama" in provider.name.lower() or ":11434" in base:
        return _check_ollama(provider, timeout, result)

    # ── GitHub Copilot SDK ──
    if provider.name == "GitHubCopilot":
        result["status"] = "skip"
        result["message"] = "Copilot SDK 请通过专用诊断命令验证"
        return result

    # ── OpenAI 兼容端点（NVIDIA/OpenAI/Azure/Custom）──
    if not provider.base_url:
        result["status"] = "config_error"
        result["message"] = "Base URL 未配置"
        return result

    if not provider.api_key:
        result["status"] = "config_error"
        result["message"] = "API Key 未配置"
        return result

    return _check_openai_compatible(provider, timeout, result)


def _check_openai_compatible(provider: AIProvider, timeout: int, result: dict) -> dict:
    """向 OpenAI 兼容端点发送最小请求验证连通性"""
    url = provider.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": provider.default_model or "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }

    start = time.perf_counter()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        result["response_time_ms"] = (time.perf_counter() - start) * 1000
    except requests.exceptions.ConnectionError as e:
        result["status"] = "network_error"
        result["message"] = f"无法连接到服务器: {e}"
        return result
    except requests.exceptions.Timeout:
        result["status"] = "network_error"
        result["message"] = f"请求超时（{timeout}秒）"
        return result
    except requests.exceptions.RequestException as e:
        result["status"] = "network_error"
        result["message"] = f"网络错误: {e}"
        return result

    if resp.status_code == 200:
        result["success"] = True
        result["status"] = "success"
        result["message"] = "API 连通正常"
    elif resp.status_code in (401, 403):
        result["status"] = "invalid_key"
        result["message"] = f"API Key 无效或权限不足 (HTTP {resp.status_code})"
    elif resp.status_code == 404:
        # 可能是模型不存在，但端点可达
        result["success"] = True
        result["status"] = "success"
        result["message"] = f"端点可达，但模型可能不存在 (HTTP {resp.status_code})"
    else:
        result["status"] = "error"
        result["message"] = f"HTTP {resp.status_code}: {resp.text[:200]}"

    return result


def _check_ollama(provider: AIProvider, timeout: int, result: dict) -> dict:
    """测试 Ollama 服务连通性"""
    base = provider.base_url.rstrip("/") if provider.base_url else "http://localhost:11434"
    # 确保有 scheme（默认补 http://）
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    try:
        # 先检查服务是否运行
        start = time.perf_counter()
        resp = requests.get(f"{base}/api/tags", timeout=timeout)
        result["response_time_ms"] = (time.perf_counter() - start) * 1000

        if resp.status_code != 200:
            result["status"] = "error"
            result["message"] = f"Ollama 服务异常 (HTTP {resp.status_code})"
            return result

        # 检查指定模型是否存在
        models = resp.json().get("models", [])
        model_names = [m.get("name", "") for m in models]
        if provider.default_model and provider.default_model not in model_names:
            result["status"] = "config_error"
            result["message"] = f"模型 '{provider.default_model}' 未在 Ollama 中找到，可用: {', '.join(model_names[:3])}"
            return result

        result["success"] = True
        result["status"] = "success"
        result["message"] = f"Ollama 服务正常，已加载 {len(models)} 个模型"
        return result

    except requests.exceptions.ConnectionError:
        result["status"] = "network_error"
        result["message"] = "无法连接到 Ollama 服务，请确认已启动 (ollama serve)"
        return result
    except requests.exceptions.Timeout:
        result["status"] = "network_error"
        result["message"] = f"连接 Ollama 超时（{timeout}秒）"
        return result
    except requests.exceptions.RequestException as e:
        result["status"] = "network_error"
        result["message"] = f"网络错误: {e}"
        return result


def check_all_providers(timeout: int = 10) -> Dict[str, Dict[str, Any]]:
    """测试所有已配置的提供方，返回 {name: result}"""
    from src.config.ai_providers import provider_manager

    results = {}
    for name in provider_manager.list_providers():
        provider = provider_manager.get_provider(name)
        if provider is None:
            continue
        results[name] = check_api_connectivity(provider, timeout)
    return results


def format_report(results: Dict[str, Dict[str, Any]]) -> str:
    """将测试结果格式化为可读报告"""
    lines = ["API 连通性测试报告", "=" * 40]
    for name, r in results.items():
        icon = "✅" if r["success"] else ("⏭️" if r["status"] == "skip" else "❌")
        lines.append(f"{icon} {name}: {r['message']}")
        if r["response_time_ms"] is not None:
            lines.append(f"   耗时: {r['response_time_ms']:.0f}ms")
    return "\n".join(lines)


# ───────── 便捷入口 ─────────

def quick_check(provider_name: str, timeout: int = 10) -> bool:
    """快速检查指定提供方是否可用，返回 True/False"""
    from src.config.ai_providers import provider_manager

    provider = provider_manager.get_provider(provider_name)
    if provider is None:
        return False
    result = check_api_connectivity(provider, timeout)
    return result["success"]


if __name__ == "__main__":
    # 命令行直接运行：python -m src.services.api_connectivity
    print(format_report(check_all_providers()))
