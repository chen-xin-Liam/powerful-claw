"""
集群服务模块初始化
"""

from .gpu_detector import GPUDetector, GPUInfo
from .lan_node import LANNode, NodeInfo, NodeStatus
from .task_scheduler import TaskScheduler, TaskInfo, TaskStatus, TaskPriority
from .secure_transport import SecureTransport
from .cluster_monitor import ClusterMonitor, ClusterStats, ClusterStatus
from .cluster_api import ClusterAPIServer
from .distributed_inference import DistributedInferenceService, InferenceTask
from .system_monitor import SystemMonitor, CPUInfo, MemoryInfo, NPUInfo, SystemInfo

__all__ = [
    "GPUDetector",
    "GPUInfo",
    "LANNode",
    "NodeInfo",
    "NodeStatus",
    "TaskScheduler",
    "TaskInfo",
    "TaskStatus",
    "TaskPriority",
    "SecureTransport",
    "ClusterMonitor",
    "ClusterStats",
    "ClusterStatus",
    "ClusterAPIServer",
    "DistributedInferenceService",
    "InferenceTask",
    "ClusterManager",
    "SystemMonitor",
    "CPUInfo",
    "MemoryInfo",
    "NPUInfo",
    "SystemInfo"
]


class ClusterManager:
    """集群管理器（整合所有组件）"""
    
    def __init__(self):
        self.lan_node = LANNode()
        self.scheduler = TaskScheduler(self.lan_node)
        self.monitor = ClusterMonitor(self.lan_node, self.scheduler)
        self.secure_transport = SecureTransport()
        self.api_server = ClusterAPIServer()
        self.inference_service = DistributedInferenceService(self)
        
        # 设置API服务器的集群管理器引用
        self.api_server.set_cluster_manager(self)
        
        # 心跳定时任务
        self.heartbeat_thread = None
        self.is_running = False
    
    def start(self):
        """启动集群服务"""
        self.is_running = True
        
        # 启动各个组件
        self.lan_node.start()
        self.scheduler.start()
        self.monitor.start()
        self.api_server.start()
        self.inference_service.start()
        
        # 启动心跳定时任务
        import threading
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()
        
        print("[ClusterManager] 集群服务已启动")
    
    def stop(self):
        """停止集群服务"""
        self.is_running = False
        
        # 停止各个组件
        self.inference_service.stop()
        self.api_server.stop()
        self.monitor.stop()
        self.scheduler.stop()
        self.lan_node.stop()
        
        print("[ClusterManager] 集群服务已停止")
    
    def _heartbeat_loop(self):
        """心跳定时任务"""
        while self.is_running:
            try:
                self.lan_node.send_heartbeat()
                import time
                time.sleep(5)
            except Exception as e:
                if self.is_running:
                    print(f"[ClusterManager] 心跳发送失败: {e}")
    
    def submit_task(self, task_type: str, data: dict, priority: int = 2):
        """提交任务"""
        return self.scheduler.submit_task(task_type, data, priority)
    
    def get_task(self, task_id: str):
        """获取任务"""
        return self.scheduler.get_task(task_id)
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        return self.scheduler.cancel_task(task_id)
    
    def get_nodes(self):
        """获取节点列表"""
        return self.lan_node.get_nodes()
    
    def get_summary(self):
        """获取集群摘要"""
        summary = self.monitor.get_cluster_summary()
        summary["self_info"] = self.lan_node.get_self_info()
        return summary
    
    def get_gpu_info(self):
        """获取本机GPU信息"""
        detector = GPUDetector()
        detector.detect()
        return detector.to_dict()
    
    def get_system_info(self):
        """获取本机系统信息（CPU、内存、NPU）"""
        monitor = SystemMonitor()
        return monitor.to_dict(include_gpu=True)
    
    def set_local_model_service(self, service):
        """设置本地模型服务（用于分布式推理）"""
        self.inference_service.set_local_model_service(service)
    
    def chat(self, prompt: str, max_tokens: int = 512) -> str:
        """执行AI推理（自动选择本地或集群算力）"""
        return self.inference_service.submit_inference(
            model_name="default",
            prompt=prompt,
            max_tokens=max_tokens
        )
    
    def chat_stream(self, prompt: str, max_tokens: int = 512):
        """流式AI推理"""
        return self.inference_service.stream_inference(
            model_name="default",
            prompt=prompt,
            max_tokens=max_tokens
        )


# 测试
if __name__ == "__main__":
    cluster = ClusterManager()
    cluster.start()
    
    print("\n按 Ctrl+C 停止...")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        cluster.stop()
