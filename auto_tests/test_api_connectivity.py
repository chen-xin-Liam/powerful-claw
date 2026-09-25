"""API 连通性测试（自动化）

- 各状态码的正确识别
- 网络错误 / 超时 / 无效 Key 的区分
- 本地模型与 Copilot 的跳过逻辑
"""
import pytest
from unittest.mock import patch, MagicMock

from src.config.ai_providers import AIProvider
from src.services.api_connectivity import (
    check_api_connectivity,
    check_all_providers,
    quick_check,
    format_report,
)


class TestCheckApiConnectivity:
    def test_missing_api_key(self):
        p = AIProvider(name="Test", base_url="https://api.test.com/v1", api_key="", default_model="gpt-4")
        r = check_api_connectivity(p)
        assert r["success"] is False
        assert r["status"] == "config_error"
        assert "API Key" in r["message"]

    def test_missing_base_url(self):
        p = AIProvider(name="Test", base_url="", api_key="sk-test", default_model="gpt-4")
        r = check_api_connectivity(p)
        assert r["success"] is False
        assert r["status"] == "config_error"
        assert "Base URL" in r["message"]

    def test_local_provider_skipped(self):
        p = AIProvider(name="Local", base_url="local", api_key="", default_model="Qwen")
        r = check_api_connectivity(p)
        assert r["status"] == "skip"
        assert "本地模型" in r["message"]

    def test_copilot_provider_skipped(self):
        p = AIProvider(name="GitHubCopilot", base_url="copilot://github", api_key="", default_model="auto")
        r = check_api_connectivity(p)
        assert r["status"] == "skip"
        assert "Copilot" in r["message"]

    @patch("src.services.api_connectivity.requests.post")
    def test_successful_openai_compatible(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        p = AIProvider(name="Test", base_url="https://api.test.com/v1", api_key="sk-test", default_model="gpt-4")
        r = check_api_connectivity(p)
        assert r["success"] is True
        assert r["status"] == "success"
        assert r["response_time_ms"] is not None

    @patch("src.services.api_connectivity.requests.post")
    def test_invalid_key_401(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        p = AIProvider(name="Test", base_url="https://api.test.com/v1", api_key="bad-key", default_model="gpt-4")
        r = check_api_connectivity(p)
        assert r["success"] is False
        assert r["status"] == "invalid_key"

    @patch("src.services.api_connectivity.requests.post")
    def test_network_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        p = AIProvider(name="Test", base_url="https://unreachable.com/v1", api_key="sk-test", default_model="gpt-4")
        r = check_api_connectivity(p)
        assert r["success"] is False
        assert r["status"] == "network_error"

    @patch("src.services.api_connectivity.requests.post")
    def test_timeout(self, mock_post):
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("timed out")

        p = AIProvider(name="Test", base_url="https://slow.com/v1", api_key="sk-test", default_model="gpt-4")
        r = check_api_connectivity(p)
        assert r["success"] is False
        assert r["status"] == "network_error"
        assert "超时" in r["message"]


class TestOllama:
    @patch("src.services.api_connectivity.requests.get")
    def test_ollama_not_running(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")

        p = AIProvider(name="Ollama", base_url="http://localhost:11434", api_key="", default_model="llama3")
        r = check_api_connectivity(p)
        assert r["success"] is False
        assert r["status"] == "network_error"
        assert "ollama serve" in r["message"]

    @patch("src.services.api_connectivity.requests.get")
    def test_ollama_model_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "llama2"}]}
        mock_get.return_value = mock_resp

        p = AIProvider(name="Ollama", base_url="http://localhost:11434", api_key="", default_model="llama3")
        r = check_api_connectivity(p)
        assert r["success"] is False
        assert r["status"] == "config_error"
        assert "llama3" in r["message"]

    @patch("src.services.api_connectivity.requests.get")
    def test_ollama_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "llama3"}, {"name": "mistral"}]}
        mock_get.return_value = mock_resp

        p = AIProvider(name="Ollama", base_url="http://localhost:11434", api_key="", default_model="llama3")
        r = check_api_connectivity(p)
        assert r["success"] is True
        assert r["status"] == "success"


class TestHelpers:
    def test_quick_check_invalid_provider(self):
        assert quick_check("NonExistentProvider") is False

    def test_format_report_structure(self):
        results = {
            "Test": {"success": True, "status": "success", "message": "OK", "response_time_ms": 123.4}
        }
        report = format_report(results)
        assert "API 连通性测试报告" in report
        assert "Test" in report
        assert "✅" in report

    @patch("src.services.api_connectivity.check_api_connectivity")
    def test_check_all_providers(self, mock_check):
        mock_check.return_value = {"success": True, "status": "success", "message": "OK"}
        results = check_all_providers()
        assert len(results) > 0
        # 每个结果都包含 provider 名称
        for name, r in results.items():
            assert isinstance(name, str)
            assert "success" in r
