import os
import sys
import json
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.mcp_manager import mcp_manager, MCPServerConfig
from src.services.plugin_manager import plugin_manager

@dataclass
class ExtensionInfo:
    type: str
    name: str
    version: str
    description: str
    state: str
    enabled: bool
    config: Dict[str, Any] = field(default_factory=dict)

class ExtensionManager:
    """统一扩展管理器，整合MCP和插件系统"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.mcp = mcp_manager
        self.plugins = plugin_manager
        self.config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "extensions.json"
        )
        self._ensure_config_dir()
        self._load_config()
        self._web_handlers = {}
    
    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
    
    def _load_config(self) -> None:
        """加载扩展配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._mcp_configs = config.get('mcp_servers', [])
                    self._enabled_extensions = config.get('enabled_extensions', [])
            except Exception as e:
                print(f"[ExtensionManager] 加载配置失败: {e}")
                self._mcp_configs = []
                self._enabled_extensions = []
        else:
            self._mcp_configs = []
            self._enabled_extensions = []
            self._save_config()
    
    def _save_config(self) -> None:
        """保存扩展配置"""
        try:
            config = {
                'mcp_servers': self._mcp_configs,
                'enabled_extensions': self._enabled_extensions,
                'last_modified': time.time()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ExtensionManager] 保存配置失败: {e}")
    
    def register_web_handler(self, path: str, handler: Any) -> None:
        """注册Web请求处理器"""
        self._web_handlers[path] = handler
    
    def initialize(self) -> None:
        """初始化所有扩展"""
        print("[ExtensionManager] 初始化扩展...")
        
        self._register_mcp_servers()
        
        self.plugins.load_all_plugins()
        
        for ext_name in self._enabled_extensions:
            self.plugins.enable_plugin(ext_name)
        
        self.plugins.start_hot_reload(interval=3.0)
        
        print("[ExtensionManager] 扩展初始化完成")
    
    def shutdown(self) -> None:
        """关闭所有扩展"""
        print("[ExtensionManager] 关闭扩展...")
        
        self.plugins.stop_hot_reload()
        self.mcp.stop_all()
        
        for plugin_name in list(self.plugins.plugins.keys()):
            self.plugins.unload_plugin(plugin_name)
        
        self._save_config()
        
        print("[ExtensionManager] 扩展已关闭")
    
    def _register_mcp_servers(self) -> None:
        """注册MCP服务器"""
        for config in self._mcp_configs:
            try:
                mcp_config = MCPServerConfig(
                    name=config['name'],
                    command=config['command'],
                    args=config.get('args', []),
                    env=config.get('env', {}),
                    enabled=config.get('enabled', True),
                    auto_reconnect=config.get('auto_reconnect', True),
                    reconnect_interval=config.get('reconnect_interval', 5),
                    max_reconnect_attempts=config.get('max_reconnect_attempts', 3)
                )
                self.mcp.register_server(mcp_config)
            except Exception as e:
                print(f"[ExtensionManager] 注册MCP服务器 '{config.get('name', 'unknown')}' 失败: {e}")
    
    def add_mcp_server(self, name: str, command: str, args: List[str] = None,
                       env: Dict[str, str] = None, enabled: bool = True) -> bool:
        """添加MCP服务器"""
        try:
            config = MCPServerConfig(
                name=name,
                command=command,
                args=args or [],
                env=env or {},
                enabled=enabled
            )
            self.mcp.register_server(config)
            
            self._mcp_configs.append({
                'name': name,
                'command': command,
                'args': args or [],
                'env': env or {},
                'enabled': enabled
            })
            self._save_config()
            
            if enabled:
                self.mcp.start_all()
            
            return True
        except Exception as e:
            print(f"[ExtensionManager] 添加MCP服务器 '{name}' 失败: {e}")
            return False
    
    def remove_mcp_server(self, name: str) -> bool:
        """移除MCP服务器"""
        if self.mcp.unregister_server(name):
            self._mcp_configs = [c for c in self._mcp_configs if c['name'] != name]
            self._save_config()
            return True
        return False
    
    def add_plugin(self, plugin_path: str) -> bool:
        """添加插件"""
        return self.plugins.load_plugin(plugin_path)
    
    def remove_plugin(self, plugin_name: str) -> bool:
        """移除插件"""
        if self.plugins.unload_plugin(plugin_name):
            if plugin_name in self._enabled_extensions:
                self._enabled_extensions.remove(plugin_name)
                self._save_config()
            return True
        return False
    
    def enable_extension(self, name: str) -> bool:
        """启用扩展"""
        if self.plugins.enable_plugin(name):
            if name not in self._enabled_extensions:
                self._enabled_extensions.append(name)
                self._save_config()
            return True
        return False
    
    def disable_extension(self, name: str) -> bool:
        """禁用扩展"""
        if self.plugins.disable_plugin(name):
            if name in self._enabled_extensions:
                self._enabled_extensions.remove(name)
                self._save_config()
            return True
        return False
    
    def reload_extension(self, name: str) -> bool:
        """热重载扩展"""
        return self.plugins.reload_plugin(name)
    
    def get_all_extensions(self) -> List[ExtensionInfo]:
        """获取所有扩展信息"""
        extensions = []
        
        for server_info in self.mcp.list_servers():
            if server_info:
                extensions.append(ExtensionInfo(
                    type="mcp",
                    name=server_info['name'],
                    version="1.0.0",
                    description=f"MCP服务器: {server_info['name']}",
                    state=server_info['state'],
                    enabled=server_info['enabled'],
                    config=server_info
                ))
        
        for plugin_info in self.plugins.list_plugins():
            if plugin_info:
                extensions.append(ExtensionInfo(
                    type="plugin",
                    name=plugin_info['name'],
                    version=plugin_info['version'],
                    description=plugin_info['description'],
                    state=plugin_info['state'],
                    enabled=plugin_info['enabled'],
                    config=plugin_info
                ))
        
        return extensions
    
    def get_extension(self, name: str) -> Optional[ExtensionInfo]:
        """获取指定扩展信息"""
        for ext in self.get_all_extensions():
            if ext.name == name:
                return ext
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """获取扩展系统状态"""
        mcp_status = self.mcp.list_servers()
        plugin_list = self.plugins.list_plugins()
        
        return {
            'mcp': {
                'total': len(mcp_status),
                'connected': sum(1 for s in mcp_status if s and s['state'] == 'connected'),
                'servers': mcp_status
            },
            'plugins': {
                'total': len(plugin_list),
                'loaded': sum(1 for p in plugin_list if p and p['state'] == 'loaded'),
                'enabled': sum(1 for p in plugin_list if p and p['enabled']),
                'plugins': plugin_list
            },
            'hot_reload': {
                'enabled': self.plugins._hot_reload_enabled
            }
        }

extension_manager = ExtensionManager()