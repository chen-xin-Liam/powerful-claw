import os
import pytest
from src.config import settings

def test_settings_defaults():
    assert settings.nvidia_base_url == "https://integrate.api.nvidia.com/v1"
    assert settings.model_name == "z-ai/glm4.7"
    assert settings.temperature == 1.0
    assert settings.top_p == 1.0
    assert settings.max_tokens == 16384
    assert settings.enable_thinking is True
    assert settings.clear_thinking is False

def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test_key_123")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    
    from src.config.settings import Settings
    new_settings = Settings()
    
    assert new_settings.nvidia_api_key == "test_key_123"
    assert new_settings.model_name == "test-model"
