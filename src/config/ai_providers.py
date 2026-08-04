from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json
import os

@dataclass
class AIProvider:
    name: str
    base_url: str
    api_key: str
    default_model: str
    description: str = ""

class AIProviderManager:
    _CONFIG_FILE = os.path.join(os.path.dirname(__file__), "providers_config.json")
    
    def __init__(self):
        self.providers: Dict[str, AIProvider] = {}
        self._load_default_providers()
        self._load_config()
    
    def _load_default_providers(self):
        self.add_provider(
            AIProvider(
                name="NVIDIA",
                base_url="https://integrate.api.nvidia.com/v1",
                api_key="",
                default_model="z-ai/glm4.7",
                description="NVIDIA AI API"
            )
        )
        self.add_provider(
            AIProvider(
                name="OpenAI",
                base_url="https://api.openai.com/v1",
                api_key="",
                default_model="gpt-4o",
                description="OpenAI API"
            )
        )
        self.add_provider(
            AIProvider(
                name="Ollama",
                base_url="http://localhost:11434",
                api_key="",
                default_model="",
                description="Ollama Local AI"
            )
        )
        self.add_provider(
            AIProvider(
                name="Custom",
                base_url="",
                api_key="",
                default_model="",
                description="Custom AI API"
            )
        )
        self.add_provider(
            AIProvider(
                name="Local",
                base_url="local",
                api_key="",
                default_model="Qwen2-0.5B",
                description="本地模型"
            )
        )
    
    def add_provider(self, provider: AIProvider):
        self.providers[provider.name] = provider
    
    def get_provider(self, name: str) -> Optional[AIProvider]:
        return self.providers.get(name)
    
    def list_providers(self) -> List[str]:
        return list(self.providers.keys())
    
    def update_provider(self, name: str, **kwargs):
        if name in self.providers:
            provider = self.providers[name]
            for key, value in kwargs.items():
                if hasattr(provider, key):
                    setattr(provider, key, value)
            self.save_config()
    
    def delete_provider(self, name: str):
        if name in self.providers:
            del self.providers[name]
            self.save_config()
    
    def save_config(self):
        try:
            config_data = {}
            for name, provider in self.providers.items():
                config_data[name] = {
                    "base_url": provider.base_url,
                    "api_key": provider.api_key,
                    "default_model": provider.default_model,
                    "description": provider.description
                }
            
            os.makedirs(os.path.dirname(self._CONFIG_FILE), exist_ok=True)
            
            with open(self._CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"Failed to save provider config: {e}")
    
    def _load_config(self):
        if not os.path.exists(self._CONFIG_FILE):
            return
        
        try:
            with open(self._CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for name, config in config_data.items():
                if name in self.providers:
                    if 'base_url' in config:
                        self.providers[name].base_url = config['base_url']
                    if 'api_key' in config:
                        self.providers[name].api_key = config['api_key']
                    if 'default_model' in config:
                        self.providers[name].default_model = config['default_model']
                    if 'description' in config:
                        self.providers[name].description = config['description']
        
        except Exception as e:
            print(f"Failed to load provider config: {e}")

provider_manager = AIProviderManager()