"""
集群监控模块
实现节点状态监控和管理功能
"""

import time
import threading
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ClusterStatus(Enum):
    """集群状态枚举"""
    IDLE = "idle"
    ACTIVE = "active"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class ClusterStats:
    """集群统计信息"""
    total_nodes: int = 0
    active_nodes: int = 0
    total_gpu_count: int = 0
    total_npu_count: int = 0
    total_cpu_cores: int = 0
    total_memory_mb: int = 0
    available_memory_mb: int = 0
    total_gpu_memory_mb: int = 0
    available_gpu_memory_mb: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    status: ClusterStatus = ClusterStatus.IDLE


class ClusterMonitor:
    """集群监控器"""
    
    def __init__(self, lan_node, task_scheduler):
        self.lan_node = lan_node
        self.task_scheduler = task_scheduler
        self.is_running = False
        self.monitor_thread = None
        self.stats = ClusterStats()
        self.stats_callbacks: List[Callable] = []
        
        # 注册节点状态回调
        self.lan_node.set_status_callback(self._on_node_status_change)
    
    def start(self):
        """启动监控器"""
        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        print("[ClusterMonitor] 集群监控器已启动")
    
    def stop(self):
        """停止监控器"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("[ClusterMonitor] 集群监控器已停止")
    
    def _monitor_loop(self):
        """监控器主循环"""
        while self.is_running:
            try:
                self._update_stats()
                self._notify_stats_update()
                time.sleep(2)
            except Exception as e:
                print(f"[ClusterMonitor] 监控器错误: {e}")
    
    def _update_stats(self):
        """更新集群统计信息"""
        nodes = self.lan_node.get_nodes()
        tasks = self.task_scheduler.get_tasks() if self.task_scheduler else []
        
        self.stats.total_nodes = len(nodes)
        self.stats.active_nodes = sum(1 for n in nodes if n.status.value == "connected")
        
        # 重置统计
        self.stats.total_gpu_count = 0
        self.stats.total_npu_count = 0
        self.stats.total_cpu_cores = 0
        self.stats.total_memory_mb = 0
        self.stats.available_memory_mb = 0
        self.stats.total_gpu_memory_mb = 0
        self.stats.available_gpu_memory_mb = 0
        
        for node in nodes:
            # CPU统计
            if node.cpu_info:
                self.stats.total_cpu_cores += node.cpu_info.get("logical_cores", 0)
            
            # 内存统计
            if node.memory_info:
                self.stats.total_memory_mb += node.memory_info.get("total_mb", 0)
                self.stats.available_memory_mb += node.memory_info.get("available_mb", 0)
            
            # GPU统计
            if node.gpu_info:
                self.stats.total_gpu_count += node.gpu_info.get("gpu_count", 0)
                self.stats.total_gpu_memory_mb += node.gpu_info.get("total_memory_mb", 0)
                self.stats.available_gpu_memory_mb += node.gpu_info.get("available_memory_mb", 0)
            
            # NPU统计
            if node.npu_info:
                self.stats.total_npu_count += node.npu_info.get("npu_count", 0)
        
        # 任务统计
        self.stats.active_tasks = sum(1 for t in tasks if t.status.value == "running")
        self.stats.completed_tasks = sum(1 for t in tasks if t.status.value == "completed")
        self.stats.failed_tasks = sum(1 for t in tasks if t.status.value == "failed")
        
        # 更新集群状态
        if self.stats.active_nodes == 0:
            self.stats.status = ClusterStatus.IDLE
        elif self.stats.active_nodes < self.stats.total_nodes:
            self.stats.status = ClusterStatus.DEGRADED
        else:
            self.stats.status = ClusterStatus.ACTIVE
    
    def _on_node_status_change(self, nodes):
        """节点状态变化回调"""
        self._update_stats()
        self._notify_stats_update()
    
    def _notify_stats_update(self):
        """通知统计信息更新"""
        for callback in self.stats_callbacks:
            try:
                callback(self.stats)
            except Exception as e:
                print(f"[ClusterMonitor] 回调执行失败: {e}")
    
    def get_stats(self) -> ClusterStats:
        """获取集群统计信息"""
        return self.stats
    
    def get_nodes_info(self) -> List[Dict[str, Any]]:
        """获取所有节点信息"""
        nodes = self.lan_node.get_nodes()
        return [
            {
                "node_id": n.node_id,
                "hostname": n.hostname,
                "ip_address": n.ip_address,
                "status": n.status.value,
                "cpu_info": n.cpu_info,
                "memory_info": n.memory_info,
                "gpu_info": n.gpu_info,
                "npu_info": n.npu_info,
                "last_heartbeat": n.last_heartbeat,
                "current_tasks": n.current_tasks,
                "max_tasks": n.max_tasks
            } for n in nodes
        ]
    
    def get_tasks_info(self) -> List[Dict[str, Any]]:
        """获取所有任务信息"""
        if not self.task_scheduler:
            return []
        
        tasks = self.task_scheduler.get_tasks()
        return [
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
    
    def add_stats_callback(self, callback: Callable):
        """添加统计信息回调"""
        if callback not in self.stats_callbacks:
            self.stats_callbacks.append(callback)
    
    def remove_stats_callback(self, callback: Callable):
        """移除统计信息回调"""
        if callback in self.stats_callbacks:
            self.stats_callbacks.remove(callback)
    
    def get_cluster_summary(self) -> Dict[str, Any]:
        """获取集群摘要"""
        return {
            "status": self.stats.status.value,
            "total_nodes": self.stats.total_nodes,
            "active_nodes": self.stats.active_nodes,
            "total_cpu_cores": self.stats.total_cpu_cores,
            "total_gpus": self.stats.total_gpu_count,
            "total_npus": self.stats.total_npu_count,
            "total_ram_gb": round(self.stats.total_memory_mb / 1024, 2),
            "available_ram_gb": round(self.stats.available_memory_mb / 1024, 2),
            "total_gpu_memory_gb": round(self.stats.total_gpu_memory_mb / 1024, 2),
            "available_gpu_memory_gb": round(self.stats.available_gpu_memory_mb / 1024, 2),
            "active_tasks": self.stats.active_tasks,
            "completed_tasks": self.stats.completed_tasks,
            "failed_tasks": self.stats.failed_tasks
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps({
            "stats": self.get_cluster_summary(),
            "nodes": self.get_nodes_info(),
            "tasks": self.get_tasks_info()
        }, indent=2)


# 测试
if __name__ == "__main__":
    from .lan_node import LANNode
    from .task_scheduler import TaskScheduler
    
    node = LANNode()
    scheduler = TaskScheduler(node)
    monitor = ClusterMonitor(node, scheduler)
    
    def on_stats_update(stats):
        print(f"\n[ClusterMonitor] 集群状态: {stats.status.value}")
        print(f"  节点: {stats.active_nodes}/{stats.total_nodes}")
        print(f"  CPU核心: {stats.total_cpu_cores}")
        print(f"  GPU: {stats.total_gpu_count}")
        print(f"  NPU: {stats.total_npu_count}")
        print(f"  内存: {stats.available_memory_mb}/{stats.total_memory_mb} MB")
        print(f"  GPU显存: {stats.available_gpu_memory_mb}/{stats.total_gpu_memory_mb} MB")
        print(f"  任务: {stats.active_tasks} 活跃, {stats.completed_tasks} 完成")
    
    monitor.add_stats_callback(on_stats_update)
    
    node.start()
    scheduler.start()
    monitor.start()
    
    print("\n按 Ctrl+C 停止...")
    try:
        while True:
            time.sleep(1)
            node.send_heartbeat()
    except KeyboardInterrupt:
        monitor.stop()
        scheduler.stop()
        node.stop()
