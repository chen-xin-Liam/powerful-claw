import os
import sys
import time
import threading
import importlib
import importlib.util
import json
import traceback
from typing import Dict, List, Optional, Callable, Any, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import hashlib
import ast

PLUGIN_API_VERSION = "1.0.0"

class PluginState(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    DISABLED = "disabled"

@dataclass
class PluginInfo:
    name: str
    version: str
    description: str
    author: str
    api_version: str
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict] = None

class PluginInterface(ABC):
    """插件接口基类"""
    
    @abstractmethod
    def on_load(self) -> bool:
        """插件加载时调用"""
        pass
    
    @abstractmethod
    def on_enable(self) -> bool:
        """插件启用时调用"""
        pass
    
    @abstractmethod
    def on_disable(self) -> None:
        """插件禁用时调用"""
        pass
    
    @abstractmethod
    def on_unload(self) -> None:
        """插件卸载时调用"""
        pass
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass

class BasePlugin(PluginInterface):
    """插件基类，提供默认实现"""
    
    def __init__(self):
        self._enabled = False
        self._config = {}
    
    def on_load(self) -> bool:
        return True
    
    def on_enable(self) -> bool:
        self._enabled = True
        return True
    
    def on_disable(self) -> None:
        self._enabled = False
    
    def on_unload(self) -> None:
        self._enabled = False
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name=self.__class__.__name__,
            version="1.0.0",
            description="",
            author="",
            api_version=PLUGIN_API_VERSION
        )
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config[key] = value
    
    def save_config(self, config_path: str) -> None:
        """保存配置到文件"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def load_config(self, config_path: str) -> None:
        """从文件加载配置"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)

@dataclass
class Plugin:
    name: str
    version: str
    description: str
    author: str
    module_path: str
    module: Optional[Any] = None
    instance: Optional[PluginInterface] = None
    state: PluginState = PluginState.UNLOADED
    file_path: str = ""
    file_hash: str = ""
    last_modified: float = 0
    error_message: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)

class PluginManager:
    """插件管理器，支持热加载"""
    
    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[Callable]] = {}
        self.enabled_plugins: List[str] = []
        self._lock = threading.RLock()
        self._hot_reload_enabled = False
        self._hot_reload_thread: Optional[threading.Thread] = None
        self._stop_hot_reload = threading.Event()
        
        if plugins_dir:
            self.plugins_dir = plugins_dir
        else:
            self.plugins_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "plugins"
            )
        
        self._ensure_plugins_dir()
    
    def _ensure_plugins_dir(self) -> None:
        """确保插件目录存在"""
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
            self._create_sample_plugins()
    
    def _create_sample_plugins(self) -> None:
        """创建示例插件"""
        sample_plugin = '''"""
示例插件 - 演示插件系统
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.plugin_manager import BasePlugin, PluginInfo

class SamplePlugin(BasePlugin):
    """示例插件类"""
    
    PLUGIN_INFO = PluginInfo(
        name="sample",
        version="1.0.0",
        description="这是一个示例插件",
        author="系统",
        api_version="1.0.0"
    )
    
    def on_load(self) -> bool:
        print("[SamplePlugin] 插件已加载")
        return True
    
    def on_enable(self) -> bool:
        print("[SamplePlugin] 插件已启用")
        return True
    
    def on_disable(self) -> None:
        print("[SamplePlugin] 插件已禁用")
    
    def on_unload(self) -> None:
        print("[SamplePlugin] 插件已卸载")
    
    def get_info(self) -> PluginInfo:
        return self.PLUGIN_INFO

def get_plugin_class():
    return SamplePlugin
'''
        
        sample_path = os.path.join(self.plugins_dir, "sample_plugin.py")
        with open(sample_path, 'w', encoding='utf-8') as f:
            f.write(sample_plugin)
        
        init_path = os.path.join(self.plugins_dir, "__init__.py")
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write("# Plugins package\n")
    
    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """注册钩子"""
        with self._lock:
            if hook_name not in self.hooks:
                self.hooks[hook_name] = []
            if callback not in self.hooks[hook_name]:
                self.hooks[hook_name].append(callback)
    
    def unregister_hook(self, hook_name: str, callback: Callable) -> None:
        """取消注册钩子"""
        with self._lock:
            if hook_name in self.hooks and callback in self.hooks[hook_name]:
                self.hooks[hook_name].remove(callback)
    
    def call_hooks(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """调用所有钩子"""
        with self._lock:
            results = []
            if hook_name in self.hooks:
                for callback in self.hooks[hook_name]:
                    try:
                        result = callback(*args, **kwargs)
                        results.append(result)
                    except Exception as e:
                        print(f"[PluginManager] 钩子 '{hook_name}' 执行失败: {e}")
            return results
    
    def _scan_plugins(self) -> List[str]:
        """扫描插件目录"""
        plugin_files = []
        for filename in os.listdir(self.plugins_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                plugin_files.append(os.path.join(self.plugins_dir, filename))
        return plugin_files
    
    def _get_file_hash(self, file_path: str) -> str:
        """获取文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def _load_plugin_from_file(self, file_path: str) -> Optional[Plugin]:
        """从文件加载插件"""
        try:
            filename = os.path.basename(file_path)
            plugin_name = os.path.splitext(filename)[0]
            
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            if spec is None or spec.loader is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)
            
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr != BasePlugin:
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and attr_name.lower().endswith('plugin'):
                        potential_class = attr()
                        if isinstance(potential_class, BasePlugin):
                            plugin_class = attr
                            break
            
            if plugin_class is None:
                return None
            
            instance = plugin_class()
            info = instance.get_info()
            
            plugin = Plugin(
                name=info.name,
                version=info.version,
                description=info.description,
                author=info.author,
                module_path=plugin_name,
                module=module,
                instance=instance,
                file_path=file_path,
                file_hash=self._get_file_hash(file_path),
                last_modified=os.path.getmtime(file_path),
                dependencies=info.dependencies
            )
            
            return plugin
            
        except Exception as e:
            print(f"[PluginManager] 加载插件 '{file_path}' 失败: {e}")
            traceback.print_exc()
            return None
    
    def discover_plugins(self) -> List[Plugin]:
        """发现所有插件"""
        discovered = []
        plugin_files = self._scan_plugins()
        
        for file_path in plugin_files:
            plugin = self._load_plugin_from_file(file_path)
            if plugin:
                discovered.append(plugin)
        
        return discovered
    
    def load_plugin(self, plugin_name: str) -> bool:
        """加载插件"""
        with self._lock:
            if plugin_name in self.plugins:
                print(f"[PluginManager] 插件 '{plugin_name}' 已加载")
                return True
            
            plugin_files = self._scan_plugins()
            for file_path in plugin_files:
                plugin = self._load_plugin_from_file(file_path)
                if plugin and plugin.name == plugin_name:
                    try:
                        plugin.state = PluginState.LOADING
                        if plugin.instance.on_load():
                            self.plugins[plugin_name] = plugin
                            plugin.state = PluginState.LOADED
                            print(f"[PluginManager] 插件 '{plugin_name}' 加载成功")
                            self.call_hooks('plugin_loaded', plugin_name)
                            return True
                        else:
                            plugin.state = PluginState.FAILED
                            plugin.error_message = "on_load() 返回 False"
                            return False
                    except Exception as e:
                        plugin.state = PluginState.FAILED
                        plugin.error_message = str(e)
                        print(f"[PluginManager] 插件 '{plugin_name}' 加载失败: {e}")
                        return False
            
            print(f"[PluginManager] 未找到插件 '{plugin_name}'")
            return False
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        with self._lock:
            if plugin_name not in self.plugins:
                return self.load_plugin(plugin_name)
            
            plugin = self.plugins[plugin_name]
            
            if plugin.state == PluginState.DISABLED:
                try:
                    if plugin.instance.on_enable():
                        plugin.state = PluginState.LOADED
                        if plugin_name not in self.enabled_plugins:
                            self.enabled_plugins.append(plugin_name)
                        print(f"[PluginManager] 插件 '{plugin_name}' 已启用")
                        self.call_hooks('plugin_enabled', plugin_name)
                        return True
                except Exception as e:
                    print(f"[PluginManager] 启用插件 '{plugin_name}' 失败: {e}")
            
            return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        with self._lock:
            if plugin_name not in self.plugins:
                return False
            
            plugin = self.plugins[plugin_name]
            
            try:
                plugin.instance.on_disable()
                plugin.state = PluginState.DISABLED
                if plugin_name in self.enabled_plugins:
                    self.enabled_plugins.remove(plugin_name)
                print(f"[PluginManager] 插件 '{plugin_name}' 已禁用")
                self.call_hooks('plugin_disabled', plugin_name)
                return True
            except Exception as e:
                print(f"[PluginManager] 禁用插件 '{plugin_name}' 失败: {e}")
                return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        with self._lock:
            if plugin_name not in self.plugins:
                return False
            
            plugin = self.plugins[plugin_name]
            
            if plugin_name in self.enabled_plugins:
                self.disable_plugin(plugin_name)
            
            try:
                plugin.instance.on_unload()
                plugin.state = PluginState.UNLOADED
                del self.plugins[plugin_name]
                print(f"[PluginManager] 插件 '{plugin_name}' 已卸载")
                self.call_hooks('plugin_unloaded', plugin_name)
                return True
            except Exception as e:
                print(f"[PluginManager] 卸载插件 '{plugin_name}' 失败: {e}")
                return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """热重载插件"""
        with self._lock:
            if plugin_name in self.plugins:
                self.unload_plugin(plugin_name)
            
            return self.load_plugin(plugin_name)
    
    def start_hot_reload(self, interval: float = 2.0) -> None:
        """启动热重载监控"""
        if self._hot_reload_enabled:
            print("[PluginManager] 热重载已在运行")
            return
        
        self._hot_reload_enabled = True
        self._stop_hot_reload.clear()
        
        def hot_reload_worker():
            while not self._stop_hot_reload.is_set():
                try:
                    self._check_for_changes()
                except Exception as e:
                    print(f"[PluginManager] 热重载检查失败: {e}")
                self._stop_hot_reload.wait(interval)
        
        self._hot_reload_thread = threading.Thread(
            target=hot_reload_worker,
            daemon=True,
            name="HotReloadWorker"
        )
        self._hot_reload_thread.start()
        print(f"[PluginManager] 热重载已启动 (间隔: {interval}秒)")
    
    def stop_hot_reload(self) -> None:
        """停止热重载监控"""
        if not self._hot_reload_enabled:
            return
        
        self._stop_hot_reload.set()
        self._hot_reload_enabled = False
        
        if self._hot_reload_thread:
            self._hot_reload_thread.join(timeout=5)
            self._hot_reload_thread = None
        
        print("[PluginManager] 热重载已停止")
    
    def _check_for_changes(self) -> None:
        """检查文件变化"""
        with self._lock:
            for plugin_name, plugin in list(self.plugins.items()):
                if not plugin.file_path or not os.path.exists(plugin.file_path):
                    continue
                
                current_mtime = os.path.getmtime(plugin.file_path)
                current_hash = self._get_file_hash(plugin.file_path)
                
                if current_mtime != plugin.last_modified or current_hash != plugin.file_hash:
                    print(f"[PluginManager] 检测到插件 '{plugin_name}' 发生变化，开始热重载...")
                    plugin.last_modified = current_mtime
                    plugin.file_hash = current_hash
                    self.reload_plugin(plugin_name)
    
    def load_all_plugins(self) -> None:
        """加载所有已发现的插件"""
        plugins = self.discover_plugins()
        for plugin in plugins:
            if plugin.name not in self.plugins:
                self.plugins[plugin.name] = plugin
                try:
                    if plugin.instance.on_load():
                        plugin.state = PluginState.LOADED
                        print(f"[PluginManager] 自动加载插件 '{plugin.name}'")
                except Exception as e:
                    plugin.state = PluginState.FAILED
                    plugin.error_message = str(e)
                    print(f"[PluginManager] 自动加载插件 '{plugin.name}' 失败: {e}")
    
    def enable_all_plugins(self) -> None:
        """启用所有插件"""
        with self._lock:
            for plugin_name in list(self.plugins.keys()):
                self.enable_plugin(plugin_name)
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """获取插件信息"""
        with self._lock:
            if plugin_name not in self.plugins:
                return None
            
            plugin = self.plugins[plugin_name]
            return {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "author": plugin.author,
                "state": plugin.state.value,
                "enabled": plugin_name in self.enabled_plugins,
                "dependencies": plugin.dependencies,
                "error_message": plugin.error_message
            }
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有插件"""
        return [self.get_plugin_info(name) for name in self.plugins.keys()]

plugin_manager = PluginManager()