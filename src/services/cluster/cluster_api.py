"""
集群API服务模块
提供集群管理的RESTful API接口
"""

import json
import threading
import socket
import time
from typing import Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler


class ClusterAPIHandler(BaseHTTPRequestHandler):
    """集群API请求处理器"""
    
    def __init__(self, *args, cluster_manager=None, **kwargs):
        self.cluster_manager = cluster_manager
        super().__init__(*args, **kwargs)
    
    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error_response(self, status_code: int, message: str):
        """发送错误响应"""
        self._send_json_response(status_code, {"error": message})
    
    def do_GET(self):
        """处理GET请求"""
        try:
            if self.path == '/api/cluster/stats':
                self._handle_get_stats()
            elif self.path == '/api/cluster/nodes':
                self._handle_get_nodes()
            elif self.path == '/api/cluster/tasks':
                self._handle_get_tasks()
            elif self.path == '/api/cluster/summary':
                self._handle_get_summary()
            elif self.path == '/api/cluster/self':
                self._handle_get_self()
            else:
                self._send_error_response(404, "Not found")
        except Exception as e:
            self._send_error_response(500, str(e))
    
    def do_POST(self):
        """处理POST请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if content_length > 0 else {}
            
            if self.path == '/api/cluster/task':
                self._handle_post_task(data)
            elif self.path == '/api/cluster/task/cancel':
                self._handle_post_cancel_task(data)
            else:
                self._send_error_response(404, "Not found")
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            self._send_error_response(500, str(e))
    
    def _handle_get_stats(self):
        """获取集群统计信息"""
        if self.cluster_manager and self.cluster_manager.monitor:
            stats = self.cluster_manager.monitor.get_cluster_summary()
            self._send_json_response(200, stats)
        else:
            self._send_error_response(503, "Cluster manager not available")
    
    def _handle_get_nodes(self):
        """获取节点列表"""
        if self.cluster_manager and self.cluster_manager.lan_node:
            nodes = self.cluster_manager.lan_node.get_nodes()
            nodes_info = [
                {
                    "node_id": n.node_id,
                    "hostname": n.hostname,
                    "ip_address": n.ip_address,
                    "status": n.status.value,
                    "gpu_info": n.gpu_info,
                    "current_tasks": n.current_tasks,
                    "max_tasks": n.max_tasks,
                    "last_heartbeat": n.last_heartbeat
                } for n in nodes
            ]
            self._send_json_response(200, {"nodes": nodes_info})
        else:
            self._send_error_response(503, "Cluster manager not available")
    
    def _handle_get_tasks(self):
        """获取任务列表"""
        if self.cluster_manager and self.cluster_manager.scheduler:
            tasks = self.cluster_manager.scheduler.get_tasks()
            tasks_info = [
                {
                    "task_id": t.task_id,
                    "type": t.type,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "assigned_node": t.assigned_node,
                    "progress": t.progress,
                    "created_at": t.created_at,
                    "started_at": t.started_at,
                    "completed_at": t.completed_at
                } for t in tasks
            ]
            self._send_json_response(200, {"tasks": tasks_info})
        else:
            self._send_error_response(503, "Cluster manager not available")
    
    def _handle_get_summary(self):
        """获取集群摘要"""
        if self.cluster_manager:
            summary = self.cluster_manager.get_summary()
            self._send_json_response(200, summary)
        else:
            self._send_error_response(503, "Cluster manager not available")
    
    def _handle_get_self(self):
        """获取本节点信息"""
        if self.cluster_manager and self.cluster_manager.lan_node:
            self._send_json_response(200, self.cluster_manager.lan_node.get_self_info())
        else:
            self._send_error_response(503, "Cluster manager not available")
    
    def _handle_post_task(self, data: Dict[str, Any]):
        """提交任务"""
        if self.cluster_manager and self.cluster_manager.scheduler:
            task_type = data.get("type")
            task_data = data.get("data", {})
            priority = data.get("priority", 2)
            
            if not task_type:
                self._send_error_response(400, "Missing task type")
                return
            
            task_id = self.cluster_manager.scheduler.submit_task(
                task_type, task_data, priority
            )
            self._send_json_response(200, {"task_id": task_id})
        else:
            self._send_error_response(503, "Cluster manager not available")
    
    def _handle_post_cancel_task(self, data: Dict[str, Any]):
        """取消任务"""
        if self.cluster_manager and self.cluster_manager.scheduler:
            task_id = data.get("task_id")
            
            if not task_id:
                self._send_error_response(400, "Missing task ID")
                return
            
            success = self.cluster_manager.scheduler.cancel_task(task_id)
            self._send_json_response(200, {"success": success})
        else:
            self._send_error_response(503, "Cluster manager not available")
    
    def log_message(self, format, *args):
        """日志记录"""
        pass


class ClusterAPIServer:
    """集群API服务器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 15305):
        self.host = host
        self.port = port
        self.server = None
        self.is_running = False
        self.cluster_manager = None
    
    def set_cluster_manager(self, cluster_manager):
        """设置集群管理器"""
        self.cluster_manager = cluster_manager
    
    def start(self):
        """启动API服务器"""
        class HandlerFactory:
            def __init__(self, cluster_manager):
                self.cluster_manager = cluster_manager
            
            def __call__(self, *args, **kwargs):
                return ClusterAPIHandler(*args, cluster_manager=self.cluster_manager, **kwargs)
        
        handler_factory = HandlerFactory(self.cluster_manager)
        self.server = HTTPServer((self.host, self.port), handler_factory)
        self.is_running = True
        
        threading.Thread(target=self._server_loop, daemon=True).start()
        print(f"[ClusterAPI] API服务器已启动: http://{self.host}:{self.port}")
    
    def _server_loop(self):
        """服务器主循环"""
        while self.is_running:
            try:
                self.server.handle_request()
            except Exception as e:
                if self.is_running:
                    print(f"[ClusterAPI] 服务器错误: {e}")
    
    def stop(self):
        """停止API服务器"""
        self.is_running = False
        if self.server:
            self.server.server_close()
        logger.info("API服务器已停止")


# 测试
if __name__ == "__main__":
    api_server = ClusterAPIServer()
    api_server.start()
    
    print("按 Ctrl+C 停止...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        api_server.stop()
