import pytest
from unittest.mock import Mock, patch
from src.services import AIService

class TestAIService:
    def test_initialization_with_env_key(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "test_key_123")
        service = AIService()
        assert service.client is not None
    
    def test_initialization_without_key(self, monkeypatch):
        if "NVIDIA_API_KEY" in os.environ:
            monkeypatch.delenv("NVIDIA_API_KEY")
        
        with pytest.raises(ValueError):
            AIService()
    
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

import os
