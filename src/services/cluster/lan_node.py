"""
局域网节点通信模块
实现节点发现、连接管理和消息通信功能
"""

import socket
import threading
import json
import time
import uuid
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import get_logger

logger = get_logger(__name__)


class NodeStatus(Enum):
    """节点状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    UNRESPONSIVE = "unresponsive"
    ERROR = "error"


@dataclass
class NodeInfo:
    """节点信息数据类"""
    node_id: str
    hostname: str
    ip_address: str
    port: int
    status: NodeStatus
    gpu_info: Dict[str, Any] = None
    cpu_info: Dict[str, Any] = None
    memory_info: Dict[str, Any] = None
    npu_info: Dict[str, Any] = None
    last_heartbeat: float = 0.0
    cpu_count: int = 0
    memory_total_mb: int = 0
    current_tasks: int = 0
    max_tasks: int = 10


class LANNode:
    """局域网节点"""

    # 端口分配
    DISCOVERY_PORT = 15300
    MAIN_PORT = 15301
    TASK_PORT = 15302
    DATA_PORT = 15303
    MONITOR_PORT = 15304

    def __init__(self):
        self.node_id = str(uuid.uuid4())
        self.hostname = socket.gethostname()
        self.ip_address = self._get_local_ip()
        self.nodes: Dict[str, NodeInfo] = {}
        self.is_running = False
        self.discovery_socket = None
        self.main_socket = None
        self.monitor_socket = None
        self.lock = threading.Lock()
        self.message_handlers: Dict[str, Callable] = {}
        self.status_callback: Optional[Callable] = None

        # 心跳间隔（秒）
        self.heartbeat_interval = 5
        self.heartbeat_timeout = 15

    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self):
        """启动节点服务"""
        self.is_running = True

        # 启动发现服务
        threading.Thread(target=self._start_discovery, daemon=True).start()

        # 启动主通信服务
        threading.Thread(target=self._start_main_server, daemon=True).start()

        # 启动监控服务
        threading.Thread(target=self._start_monitor_server, daemon=True).start()

        # 启动心跳监控
        threading.Thread(target=self._heartbeat_monitor, daemon=True).start()

        logger.info(f"节点 {self.node_id[:8]} 已启动，IP: {self.ip_address}")

    def stop(self):
        """停止节点服务"""
        self.is_running = False

        if self.discovery_socket:
            self.discovery_socket.close()
        if self.main_socket:
            self.main_socket.close()
        if self.monitor_socket:
            self.monitor_socket.close()

        logger.info(f"节点 {self.node_id[:8]} 已停止")

    def _start_discovery(self):
        """启动节点发现服务（UDP广播）"""
        try:
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.discovery_socket.bind(('', self.DISCOVERY_PORT))
            self.discovery_socket.settimeout(1.0)

            # 发送发现广播
            threading.Thread(target=self._send_discovery_broadcast, daemon=True).start()

            while self.is_running:
                try:
                    data, addr = self.discovery_socket.recvfrom(1024)
                    self._handle_discovery_packet(data, addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        logger.warning(f"发现服务错误: {e}")
        except Exception as e:
            logger.error(f"启动发现服务失败: {e}", exc_info=True)

    def _send_discovery_broadcast(self):
        """发送节点发现广播"""
        while self.is_running:
            try:
                message = json.dumps({
                    "type": "discover",
                    "node_id": self.node_id,
                    "hostname": self.hostname,
                    "ip": self.ip_address,
                    "timestamp": time.time()
                })

                self.discovery_socket.sendto(
                    message.encode('utf-8'),
                    ('255.255.255.255', self.DISCOVERY_PORT)
                )

                # 同时向局域网常用网段广播
                for subnet in self._get_local_subnets():
                    broadcast_ip = subnet.replace('.0/24', '.255')
                    try:
                        self.discovery_socket.sendto(
                            message.encode('utf-8'),
                            (broadcast_ip, self.DISCOVERY_PORT)
                        )
                    except Exception as e:
                        logger.debug(f"子网广播发送失败: {e}", exc_info=True)

                time.sleep(3)
            except Exception as e:
                if self.is_running:
                    logger.warning(f"发送广播失败: {e}")

    def _get_local_subnets(self) -> List[str]:
        """获取本地子网列表"""
        subnets = []
        ip_parts = self.ip_address.split('.')
        if len(ip_parts) == 4:
            subnets.append(f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24")
        return subnets

    def _handle_discovery_packet(self, data: bytes, addr: tuple):
        """处理发现数据包"""
        try:
            message = json.loads(data.decode('utf-8'))

            if message.get("type") == "discover":
                node_id = message.get("node_id")
                if node_id != self.node_id:
                    with self.lock:
                        if node_id not in self.nodes:
                            self.nodes[node_id] = NodeInfo(
                                node_id=node_id,
                                hostname=message.get("hostname", "unknown"),
                                ip_address=addr[0],
                                port=self.MAIN_PORT,
                                status=NodeStatus.CONNECTED,
                                last_heartbeat=time.time()
                            )
                            logger.info(f"发现新节点: {node_id[:8]} ({addr[0]})")
                            self._notify_status_change()
                        else:
                            self.nodes[node_id].last_heartbeat = time.time()
                            self.nodes[node_id].status = NodeStatus.CONNECTED

            elif message.get("type") == "heartbeat":
                        node_id = message.get("node_id")
                        with self.lock:
                            if node_id in self.nodes:
                                self.nodes[node_id].last_heartbeat = time.time()
                                self.nodes[node_id].status = NodeStatus.CONNECTED
                                if "gpu_info" in message:
                                    self.nodes[node_id].gpu_info = message["gpu_info"]
                                if "cpu_info" in message:
                                    self.nodes[node_id].cpu_info = message["cpu_info"]
                                    self.nodes[node_id].cpu_count = message["cpu_info"].get("logical_cores", 0)
                                if "memory_info" in message:
                                    self.nodes[node_id].memory_info = message["memory_info"]
                                    self.nodes[node_id].memory_total_mb = message["memory_info"].get("total_mb", 0)
                                if "npu_info" in message:
                                    self.nodes[node_id].npu_info = message["npu_info"]
                                if "cpu_count" in message:
                                    self.nodes[node_id].cpu_count = message["cpu_count"]
                                if "memory_total_mb" in message:
                                    self.nodes[node_id].memory_total_mb = message["memory_total_mb"]
        except Exception as e:
            logger.warning(f"处理发现包失败: {e}")

    def _start_main_server(self):
        """启动主通信服务（TCP）"""
        try:
            self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.main_socket.bind((self.ip_address, self.MAIN_PORT))
            self.main_socket.listen(10)
            self.main_socket.settimeout(1.0)

            logger.info(f"主通信服务已启动: {self.ip_address}:{self.MAIN_PORT}")

            while self.is_running:
                try:
                    conn, addr = self.main_socket.accept()
                    threading.Thread(
                        target=self._handle_main_connection,
                        args=(conn, addr),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        logger.warning(f"主服务错误: {e}")
        except Exception as e:
            logger.error(f"启动主服务失败: {e}", exc_info=True)

    def _handle_main_connection(self, conn: socket.socket, addr: tuple):
        """处理主连接"""
        try:
            conn.settimeout(30)
            buffer = ""

            while self.is_running:
                data = conn.recv(4096)
                if not data:
                    break

                buffer += data.decode('utf-8')

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self._handle_message(line, addr)

            conn.close()
        except Exception as e:
            logger.error(f"连接处理失败: {e}", exc_info=True)

    def _handle_message(self, message_str: str, addr: tuple):
        """处理收到的消息"""
        try:
            message = json.loads(message_str)
            msg_type = message.get("type")

            if msg_type in self.message_handlers:
                self.message_handlers[msg_type](message, addr)
            else:
                logger.warning(f"未知消息类型: {msg_type}")
        except Exception as e:
            logger.warning(f"消息处理失败: {e}")

    def _start_monitor_server(self):
        """启动监控服务（UDP）"""
        try:
            self.monitor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.monitor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.monitor_socket.bind(('', self.MONITOR_PORT))
            self.monitor_socket.settimeout(1.0)

            logger.info(f"监控服务已启动: {self.MONITOR_PORT}")

            while self.is_running:
                try:
                    data, addr = self.monitor_socket.recvfrom(4096)
                    self._handle_monitor_packet(data, addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        logger.warning(f"监控服务错误: {e}")
        except Exception as e:
            logger.error(f"启动监控服务失败: {e}", exc_info=True)

    def _handle_monitor_packet(self, data: bytes, addr: tuple):
        """处理监控数据包"""
        try:
            message = json.loads(data.decode('utf-8'))

            if message.get("type") == "status_request":
                response = json.dumps({
                    "type": "status_response",
                    "node_id": self.node_id,
                    "hostname": self.hostname,
                    "ip": self.ip_address,
                    "timestamp": time.time(),
                    "status": "online"
                })
                self.monitor_socket.sendto(response.encode('utf-8'), addr)
        except Exception as e:
            logger.warning(f"处理监控包失败: {e}")

    def _heartbeat_monitor(self):
        """心跳监控线程"""
        while self.is_running:
            time.sleep(1)

            now = time.time()
            with self.lock:
                to_remove = []

                for node_id, node in self.nodes.items():
                    if now - node.last_heartbeat > self.heartbeat_timeout:
                        if node.status == NodeStatus.CONNECTED:
                            node.status = NodeStatus.UNRESPONSIVE
                            logger.warning(f"节点 {node_id[:8]} 心跳超时")
                            self._notify_status_change()

                        if now - node.last_heartbeat > self.heartbeat_timeout * 2:
                            to_remove.append(node_id)

                for node_id in to_remove:
                    logger.info(f"移除节点: {node_id[:8]}")
                    del self.nodes[node_id]
                    self._notify_status_change()

    def _notify_status_change(self):
        """通知节点状态变化"""
        if self.status_callback:
            self.status_callback(self.get_nodes())

    def send_heartbeat(self):
        """发送心跳包"""
        from .gpu_detector import GPUDetector
        from .system_monitor import SystemMonitor

        try:
            detector = GPUDetector()
            detector.detect()

            monitor = SystemMonitor()
            system_data = monitor.to_dict(include_gpu=False)

            heartbeat = json.dumps({
                "type": "heartbeat",
                "node_id": self.node_id,
                "hostname": self.hostname,
                "ip": self.ip_address,
                "timestamp": time.time(),
                "gpu_info": detector.to_dict(),
                "cpu_info": system_data.get("cpu", {}),
                "memory_info": system_data.get("memory", {}),
                "npu_info": {
                    "npu_count": system_data.get("npu_count", 0),
                    "npus": system_data.get("npus", [])
                },
                "cpu_count": system_data.get("cpu", {}).get("logical_cores", 0),
                "memory_total_mb": system_data.get("memory", {}).get("total_mb", 0)
            })

            # 向所有已知节点发送心跳
            with self.lock:
                for node in self.nodes.values():
                    if node.status == NodeStatus.CONNECTED:
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            sock.sendto(heartbeat.encode('utf-8'), (node.ip_address, self.DISCOVERY_PORT))
                            sock.close()
                        except Exception as e:
                            logger.debug(f"向节点发送心跳失败: {e}", exc_info=True)
        except Exception as e:
            logger.warning(f"发送心跳失败: {e}")

    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler

    def unregister_handler(self, message_type: str):
        """取消注册消息处理器"""
        if message_type in self.message_handlers:
            del self.message_handlers[message_type]

    def set_status_callback(self, callback: Callable):
        """设置状态回调"""
        self.status_callback = callback

    def get_nodes(self) -> List[NodeInfo]:
        """获取所有节点列表"""
        with self.lock:
            return list(self.nodes.values())

    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """获取单个节点信息"""
        with self.lock:
            return self.nodes.get(node_id)

    def get_self_info(self) -> Dict[str, Any]:
        """获取本节点信息"""
        return {
            "node_id": self.node_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "ports": {
                "discovery": self.DISCOVERY_PORT,
                "main": self.MAIN_PORT,
                "task": self.TASK_PORT,
                "data": self.DATA_PORT,
                "monitor": self.MONITOR_PORT
            }
        }


# 测试
if __name__ == "__main__":
    node = LANNode()

    def on_status_change(nodes):
        print(f"\n[LANNode] 节点列表更新 ({len(nodes)} 个节点):")
        for n in nodes:
            print(f"  - {n.node_id[:8]}: {n.hostname} ({n.ip_address}) - {n.status.value}")

    node.set_status_callback(on_status_change)
    node.start()

    print("\n按 Ctrl+C 停止...")
    try:
        while True:
            time.sleep(1)
            node.send_heartbeat()
    except KeyboardInterrupt:
        node.stop()
