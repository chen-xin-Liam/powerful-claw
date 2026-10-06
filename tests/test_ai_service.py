import os
import pytest
from unittest.mock import Mock, patch
from src.services.ai_service import AIService

class TestAIService:
    def test_initialization_with_env_key(self, monkeypatch):
        # provider 采用延迟注入：构造后通过 set_provider 设置并初始化客户端
        monkeypatch.setenv("NVIDIA_API_KEY", "test_key_123")
        service = AIService()
        service.set_provider(
            provider_name="NVIDIA",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ["NVIDIA_API_KEY"],
            model="test-model",
        )
        service._initialize_client()
        assert service.client is not None

    def test_initialization_without_key(self, monkeypatch):
        if "NVIDIA_API_KEY" in os.environ:
            monkeypatch.delenv("NVIDIA_API_KEY")

        # 无 provider 时允许构造（provider 延迟选择），但不能初始化客户端
        service = AIService()
        assert service.current_provider is None
        assert service.client is None
        with pytest.raises(ValueError):
            service._initialize_client()

    def test_format_reasoning(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "test_key_123")
        service = AIService()

        reasoning = "This is a test reasoning"
        formatted = service.format_reasoning(reasoning)

        assert reasoning in formatted

    def test_get_color_codes(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "test_key_123")
        service = AIService()

        codes = service.get_color_codes()
        assert "reasoning" in codes
        assert "reset" in codes
        assert "use_color" in codes
