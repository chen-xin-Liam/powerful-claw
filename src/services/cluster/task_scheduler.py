"""
任务调度器模块
实现算力任务分发与负载均衡系统
"""

import threading
import time
import json
import uuid
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class TaskInfo:
    """任务信息数据类"""
    task_id: str
    type: str
    data: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus
    assigned_node: Optional[str] = None
    progress: float = 0.0
    result: Any = None
    error: Optional[str] = None
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, lan_node):
        self.lan_node = lan_node
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_queue: List[TaskInfo] = []
        self.lock = threading.Lock()
        self.is_running = False
        self.scheduler_thread = None
        self.task_callbacks: Dict[str, List[Callable]] = {}
        
        # 注册消息处理器
        self.lan_node.register_handler("task_request", self._handle_task_request)
        self.lan_node.register_handler("task_result", self._handle_task_result)
        self.lan_node.register_handler("task_status", self._handle_task_status)
    
    def start(self):
        """启动调度器"""
        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self.scheduler_thread.start()
        print("[TaskScheduler] 任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("[TaskScheduler] 任务调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.is_running:
            try:
                self._process_queue()
                time.sleep(0.5)
            except Exception as e:
                print(f"[TaskScheduler] 调度器错误: {e}")
    
    def _process_queue(self):
        """处理任务队列"""
        with self.lock:
            # 按优先级排序
            self.task_queue.sort(key=lambda t: t.priority.value, reverse=True)
            
            # 获取可用节点
            available_nodes = self._get_available_nodes()
            
            for task in list(self.task_queue):
                if task.status != TaskStatus.PENDING:
                    self.task_queue.remove(task)
                    continue
                
                # 找到最合适的节点
                node = self._select_best_node(task, available_nodes)
                
                if node:
                    self._assign_task(task, node)
    
    def _get_available_nodes(self):
        """获取可用节点列表"""
        nodes = self.lan_node.get_nodes()
        return [n for n in nodes if n.status.value == "connected"]
    
    def _select_best_node(self, task: TaskInfo, nodes: List) -> Optional:
        """选择最合适的节点"""
        if not nodes:
            return None
        
        best_node = None
        best_score = -1
        
        for node in nodes:
            score = self._calculate_node_score(node, task)
            if score > best_score:
                best_score = score
                best_node = node
        
        return best_node
    
    def _calculate_node_score(self, node, task: TaskInfo) -> float:
        """计算节点得分"""
        score = 0.0
        
        # CPU权重
        if node.cpu_info:
            cpu_usage = node.cpu_info.get("usage_percent", 100)
            cpu_cores = node.cpu_info.get("logical_cores", 1)
            
            # CPU可用度（使用率越低越好）
            cpu_available = max(0, 100 - cpu_usage) / 100
            score += cpu_available * 20
            
            # CPU核心数
            score += min(cpu_cores, 32) * 2
        
        # 内存权重
        if node.memory_info:
            mem_available = node.memory_info.get("available_mb", 0)
            mem_total = node.memory_info.get("total_mb", 1)
            
            # 内存可用度
            mem_ratio = mem_available / mem_total
            score += mem_ratio * 20
        
        # GPU显存权重
        if node.gpu_info:
            gpu_count = node.gpu_info.get("gpu_count", 0)
            available_mem = node.gpu_info.get("available_memory_mb", 0)
            total_mem = node.gpu_info.get("total_memory_mb", 0)
            
            # 显存充足度
            if total_mem > 0:
                mem_ratio = available_mem / total_mem
                score += mem_ratio * 25
            
            # GPU数量
            score += gpu_count * 5
        
        # NPU权重
        if node.npu_info:
            npu_count = node.npu_info.get("npu_count", 0)
            score += npu_count * 10
        
        # 当前任务数权重（任务越少越好）
        load_ratio = (node.max_tasks - node.current_tasks) / node.max_tasks
        score += load_ratio * 15
        
        # 优先级加成
        if task.priority in [TaskPriority.HIGH, TaskPriority.URGENT]:
            score += 10
        
        return score
    
    def _assign_task(self, task: TaskInfo, node):
        """分配任务到节点"""
        with self.lock:
            task.status = TaskStatus.RUNNING
            task.assigned_node = node.node_id
            task.started_at = time.time()
        
        # 发送任务请求
        self._send_task_to_node(task, node)
        
        print(f"[TaskScheduler] 任务 {task.task_id[:8]} 已分配到节点 {node.node_id[:8]}")
    
    def _send_task_to_node(self, task: TaskInfo, node):
        """向节点发送任务"""
        try:
            import socket
            
            task_data = json.dumps({
                "type": "task_request",
                "task_id": task.task_id,
                "task_type": task.type,
                "data": task.data,
                "priority": task.priority.value,
                "timestamp": time.time()
            })
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((node.ip_address, self.lan_node.TASK_PORT))
            sock.sendall((task_data + "\n").encode('utf-8'))
            sock.close()
        except Exception as e:
            print(f"[TaskScheduler] 发送任务失败: {e}")
            with self.lock:
                task.status = TaskStatus.FAILED
                task.error = str(e)
    
    def submit_task(self, task_type: str, data: Dict[str, Any], 
                    priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """提交新任务"""
        task_id = str(uuid.uuid4())
        task = TaskInfo(
            task_id=task_id,
            type=task_type,
            data=data,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=time.time()
        )
        
        with self.lock:
            self.tasks[task_id] = task
            self.task_queue.append(task)
        
        print(f"[TaskScheduler] 任务 {task_id[:8]} 已提交")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_tasks(self) -> List[TaskInfo]:
        """获取所有任务"""
        with self.lock:
            return list(self.tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
                    task.status = TaskStatus.CANCELLED
                    self.task_queue.remove(task)
                    print(f"[TaskScheduler] 任务 {task_id[:8]} 已取消")
                    return True
        return False
    
    def _handle_task_request(self, message, addr):
        """处理任务请求（作为工作节点）"""
        try:
            task_id = message.get("task_id")
            task_type = message.get("task_type")
            data = message.get("data", {})
            
            print(f"[TaskScheduler] 收到任务请求: {task_id[:8]}")
            
            # 本地处理任务
            result = self._execute_task(task_type, data)
            
            # 发送结果
            self._send_task_result(task_id, result)
        except Exception as e:
            print(f"[TaskScheduler] 处理任务请求失败: {e}")
    
    def _execute_task(self, task_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务（占位方法，需子类实现）"""
        return {
            "success": True,
            "result": f"Task {task_type} executed successfully",
            "data": data
        }
    
    def _send_task_result(self, task_id: str, result: Dict[str, Any]):
        """发送任务结果"""
        try:
            result_data = json.dumps({
                "type": "task_result",
                "task_id": task_id,
                "result": result,
                "timestamp": time.time()
            })
            
            # 发送给所有节点（简化实现）
            for node in self.lan_node.get_nodes():
                if node.status.value == "connected":
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(3)
                        sock.connect((node.ip_address, self.lan_node.TASK_PORT))
                        sock.sendall((result_data + "\n").encode('utf-8'))
                        sock.close()
                    except:
                        pass
        except Exception as e:
            print(f"[TaskScheduler] 发送任务结果失败: {e}")
    
    def _handle_task_result(self, message, addr):
        """处理任务结果"""
        try:
            task_id = message.get("task_id")
            result = message.get("result", {})
            
            with self.lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.COMPLETED if result.get("success") else TaskStatus.FAILED
                    task.result = result
                    task.completed_at = time.time()
                    task.progress = 100.0
            
            print(f"[TaskScheduler] 任务 {task_id[:8]} 完成")
            self._notify_task_update(task_id)
        except Exception as e:
            print(f"[TaskScheduler] 处理任务结果失败: {e}")
    
    def _handle_task_status(self, message, addr):
        """处理任务状态更新"""
        try:
            task_id = message.get("task_id")
            progress = message.get("progress", 0)
            status = message.get("status")
            
            with self.lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.progress = progress
                    if status:
                        try:
                            task.status = TaskStatus(status)
                        except ValueError:
                            pass
        except Exception as e:
            print(f"[TaskScheduler] 处理任务状态失败: {e}")
    
    def _notify_task_update(self, task_id: str):
        """通知任务更新"""
        if task_id in self.task_callbacks:
            task = self.get_task(task_id)
            for callback in self.task_callbacks[task_id]:
                try:
                    callback(task)
                except Exception as e:
                    print(f"[TaskScheduler] 回调执行失败: {e}")
    
    def add_task_callback(self, task_id: str, callback: Callable):
        """添加任务回调"""
        with self.lock:
            if task_id not in self.task_callbacks:
                self.task_callbacks[task_id] = []
            self.task_callbacks[task_id].append(callback)
    
    def remove_task_callback(self, task_id: str, callback: Callable):
        """移除任务回调"""
        with self.lock:
            if task_id in self.task_callbacks and callback in self.task_callbacks[task_id]:
                self.task_callbacks[task_id].remove(callback)


# 测试
if __name__ == "__main__":
    from .lan_node import LANNode
    
    node = LANNode()
    scheduler = TaskScheduler(node)
    
    node.start()
    scheduler.start()
    
    print("\n按 Ctrl+C 停止...")
    try:
        while True:
            time.sleep(1)
            node.send_heartbeat()
    except KeyboardInterrupt:
        scheduler.stop()
        node.stop()
