import asyncio
import json
import subprocess
import sys
import os
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import importlib.util
import sys

class MCPConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    auto_reconnect: bool = True
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 3

@dataclass
class MCPServer:
    config: MCPServerConfig
    process: Optional[subprocess.Popen] = None
    state: MCPConnectionState = MCPConnectionState.DISCONNECTED
    last_error: Optional[str] = None
    reconnect_attempts: int = 0
    message_handlers: List[Callable] = field(default_factory=list)

class MCPServerManager:
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.global_handlers: List[Callable] = []
        self.is_running = False
        self._lock = threading.Lock()
        
    def register_server(self, config: MCPServerConfig) -> None:
        """注册一个MCP服务器"""
        with self._lock:
            if config.name in self.servers:
                print(f"[MCP] 服务器 '{config.name}' 已存在，将被替换")
            self.servers[config.name] = MCPServer(config=config)
            print(f"[MCP] 服务器 '{config.name}' 已注册")
    
    def unregister_server(self, name: str) -> bool:
        """取消注册一个MCP服务器"""
        with self._lock:
            if name not in self.servers:
                return False
            server = self.servers[name]
            if server.state == MCPConnectionState.CONNECTED:
                self._stop_server(name)
            del self.servers[name]
            print(f"[MCP] 服务器 '{name}' 已取消注册")
            return True
    
    def add_message_handler(self, handler: Callable[[str, Any], None]) -> None:
        """添加全局消息处理器"""
        if handler not in self.global_handlers:
            self.global_handlers.append(handler)
    
    def remove_message_handler(self, handler: Callable) -> None:
        """移除全局消息处理器"""
        if handler in self.global_handlers:
            self.global_handlers.remove(handler)
    
    def _start_server(self, name: str) -> bool:
        """启动单个MCP服务器"""
        with self._lock:
            if name not in self.servers:
                return False
            server = self.servers[name]
            
        if server.config.enabled is False:
            print(f"[MCP] 服务器 '{name}' 已禁用")
            return False
        
        try:
            env = os.environ.copy()
            env.update(server.config.env)
            
            cmd = [server.config.command] + server.config.args
            print(f"[MCP] 启动服务器 '{name}': {' '.join(cmd)}")
            
            server.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=False
            )
            
            server.state = MCPConnectionState.CONNECTED
            server.reconnect_attempts = 0
            server.last_error = None
            print(f"[MCP] 服务器 '{name}' 已启动")
            return True
            
        except Exception as e:
            server.state = MCPConnectionState.ERROR
            server.last_error = str(e)
            print(f"[MCP] 服务器 '{name}' 启动失败: {e}")
            return False
    
    def _stop_server(self, name: str) -> None:
        """停止单个MCP服务器"""
        with self._lock:
            if name not in self.servers:
                return
            server = self.servers[name]
        
        if server.process:
            try:
                server.process.terminate()
                server.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.process.kill()
            except Exception as e:
                print(f"[MCP] 停止服务器 '{name}' 时出错: {e}")
            server.process = None
        
        server.state = MCPConnectionState.DISCONNECTED
        print(f"[MCP] 服务器 '{name}' 已停止")
    
    def start_all(self) -> None:
        """启动所有已注册的MCP服务器"""
        self.is_running = True
        for name in list(self.servers.keys()):
            if self.servers[name].config.enabled:
                self._start_server(name)
    
    def stop_all(self) -> None:
        """停止所有MCP服务器"""
        self.is_running = False
        for name in list(self.servers.keys()):
            self._stop_server(name)
    
    def restart_server(self, name: str) -> bool:
        """重启单个MCP服务器"""
        self._stop_server(name)
        return self._start_server(name)
    
    def get_server_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取服务器状态"""
        with self._lock:
            if name not in self.servers:
                return None
            server = self.servers[name]
            return {
                "name": name,
                "state": server.state.value,
                "enabled": server.config.enabled,
                "last_error": server.last_error,
                "reconnect_attempts": server.reconnect_attempts,
                "process_running": server.process is not None and server.process.poll() is None
            }
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器状态"""
        return [self.get_server_status(name) for name in self.servers.keys()]
    
    def send_request(self, server_name: str, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """向服务器发送请求"""
        with self._lock:
            if server_name not in self.servers:
                return None
            server = self.servers[server_name]
        
        if server.state != MCPConnectionState.CONNECTED or not server.process:
            return None
        
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params or {}
        }
        
        try:
            request_json = json.dumps(request) + "\n"
            server.process.stdin.write(request_json.encode('utf-8'))
            server.process.stdin.flush()
            return request
        except Exception as e:
            print(f"[MCP] 发送请求到 '{server_name}' 失败: {e}")
            return None
    
    def notify(self, server_name: str, method: str, params: Optional[Dict] = None) -> bool:
        """发送通知（无响应）"""
        return self.send_request(server_name, method, params) is not None

mcp_manager = MCPServerManager()