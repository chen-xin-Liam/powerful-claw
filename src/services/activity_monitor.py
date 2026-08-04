import asyncio
import websockets
import json
import threading
import time
import os
import sys
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MonitorEvent(Enum):
    USER_CONNECT = "user_connect"
    USER_DISCONNECT = "user_disconnect"
    MESSAGE_SEND = "message_send"
    MESSAGE_RECEIVE = "message_receive"
    SETTINGS_CHANGE = "settings_change"
    EXTENSION_ACTION = "extension_action"
    API_REQUEST = "api_request"

@dataclass
class UserAction:
    timestamp: float
    event_type: str
    user_id: str
    username: str = ""
    ip_address: str = ""
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

class ActivityMonitor:
    """用户活动监控器"""
    
    def __init__(self):
        self.is_enabled = True
        self.clients: List[websockets.WebSocketServerProtocol] = []
        self.recent_actions: List[UserAction] = []
        self.max_history = 100
        self._lock = threading.RLock()
        self._server = None
        self._server_thread = None
        self.is_running = False
        self.port = 15004
        
    def enable(self):
        """启用监控"""
        with self._lock:
            self.is_enabled = True
            print("[Monitor] 监控已启用")
    
    def disable(self):
        """禁用监控"""
        with self._lock:
            self.is_enabled = False
            print("[Monitor] 监控已禁用")
    
    def toggle(self):
        """切换监控状态"""
        with self._lock:
            self.is_enabled = not self.is_enabled
            print(f"[Monitor] 监控状态已切换为: {'启用' if self.is_enabled else '禁用'}")
        return self.is_enabled
    
    def record_action(self, event_type: str, user_id: str, action: str, 
                     details: Dict[str, Any] = None, username: str = "", ip_address: str = "") -> None:
        """记录用户操作"""
        if not self.is_enabled:
            return
        
        action_data = UserAction(
            timestamp=time.time(),
            event_type=event_type,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            action=action,
            details=details or {}
        )
        
        with self._lock:
            self.recent_actions.append(action_data)
            if len(self.recent_actions) > self.max_history:
                self.recent_actions.pop(0)
        
        self._broadcast_action(action_data)
    
    def _broadcast_action(self, action: UserAction):
        """广播操作事件到所有监控客户端"""
        if not self.is_enabled:
            return
        
        try:
            message = json.dumps({
                'type': 'activity',
                'data': {
                    'timestamp': action.timestamp,
                    'event_type': action.event_type,
                    'user_id': action.user_id,
                    'username': action.username,
                    'ip_address': action.ip_address,
                    'action': action.action,
                    'details': action.details
                }
            })
            
            asyncio.create_task(self._send_to_all_clients(message))
        except Exception as e:
            print(f"[Monitor] 广播失败: {e}")
    
    async def _send_to_all_clients(self, message: str):
        """发送消息给所有客户端"""
        with self._lock:
            for client in list(self.clients):
                try:
                    await client.send(message)
                except Exception:
                    self.clients.remove(client)
    
    async def _handle_client(self, websocket):
        """处理监控客户端连接"""
        with self._lock:
            self.clients.append(websocket)
            print(f"[Monitor] 监控客户端已连接: {websocket.remote_address}")
        
        try:
            # 发送历史记录
            with self._lock:
                history = [
                    {
                        'timestamp': action.timestamp,
                        'event_type': action.event_type,
                        'user_id': action.user_id,
                        'username': action.username,
                        'ip_address': action.ip_address,
                        'action': action.action,
                        'details': action.details
                    } for action in self.recent_actions
                ]
            
            await websocket.send(json.dumps({
                'type': 'history',
                'data': history,
                'enabled': self.is_enabled
            }))
            
            async for message in websocket:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            with self._lock:
                if websocket in self.clients:
                    self.clients.remove(websocket)
                print(f"[Monitor] 监控客户端已断开: {websocket.remote_address}")
    
    async def _run_server(self):
        """运行监控服务器"""
        self._server = await websockets.serve(
            self._handle_client,
            '0.0.0.0',
            self.port
        )
        print(f"[Monitor] 监控服务器已启动: ws://0.0.0.0:{self.port}")
        
        await self._server.wait_closed()
    
    def _server_thread_func(self):
        """服务器线程函数"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run_server())
    
    def start(self):
        """启动监控服务器"""
        if self.is_running:
            return
        
        self.is_running = True
        self._server_thread = threading.Thread(
            target=self._server_thread_func,
            daemon=True,
            name="MonitorServer"
        )
        self._server_thread.start()
    
    def stop(self):
        """停止监控服务器"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self._server:
            self._server.close()
        print("[Monitor] 监控服务器已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        with self._lock:
            return {
                'enabled': self.is_enabled,
                'running': self.is_running,
                'client_count': len(self.clients),
                'history_count': len(self.recent_actions),
                'port': self.port
            }
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取操作历史"""
        with self._lock:
            history = self.recent_actions[-limit:]
            return [
                {
                    'timestamp': action.timestamp,
                    'event_type': action.event_type,
                    'user_id': action.user_id,
                    'username': action.username,
                    'ip_address': action.ip_address,
                    'action': action.action,
                    'details': action.details,
                    'formatted_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(action.timestamp))
                } for action in history
            ]

activity_monitor = ActivityMonitor()