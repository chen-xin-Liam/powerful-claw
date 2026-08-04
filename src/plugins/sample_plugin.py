"""
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
