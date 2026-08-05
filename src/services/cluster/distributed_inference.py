"""
分布式推理服务模块
实现跨节点的AI模型推理算力共享
"""

import json
import time
import threading
from typing import Dict, Any, Optional, Generator
from dataclasses import dataclass
import socket

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class InferenceTask:
    """推理任务数据类"""
    task_id: str
    model_name: str
    prompt: str
    max_tokens: int
    temperature: float
    status: str = "pending"
    result: str = ""
    error: str = ""
    progress: float = 0.0
    created_at: float = 0.0
    completed_at: Optional[float] = None


class DistributedInferenceService:
    """分布式推理服务"""
    
    def __init__(self, cluster_manager):
        self.cluster_manager = cluster_manager
        self.local_model_service = None
        self.is_running = False
        self.inference_tasks: Dict[str, InferenceTask] = {}
        
        # 注册消息处理器
        if cluster_manager and cluster_manager.lan_node:
            cluster_manager.lan_node.register_handler("inference_request", self._handle_inference_request)
            cluster_manager.lan_node.register_handler("inference_result", self._handle_inference_result)
    
    def set_local_model_service(self, service):
        """设置本地模型服务"""
        self.local_model_service = service
    
    def start(self):
        """启动推理服务"""
        self.is_running = True
        logger.info("分布式推理服务已启动")
    
    def stop(self):
        """停止推理服务"""
        self.is_running = False
        logger.info("分布式推理服务已停止")
    
    def _handle_inference_request(self, message, addr):
        """处理推理请求（作为工作节点）"""
        try:
            task_id = message.get("task_id")
            model_name = message.get("model_name")
            prompt = message.get("prompt")
            max_tokens = message.get("max_tokens", 512)
            temperature = message.get("temperature", 0.7)
            
            logger.info(f"收到推理请求: {task_id[:8]}")
            
            # 使用本地模型服务执行推理
            if self.local_model_service and self.local_model_service.is_loaded:
                result = self.local_model_service.chat(prompt, max_tokens)
                
                # 发送结果
                self._send_inference_result(task_id, {"success": True, "result": result})
            else:
                self._send_inference_result(task_id, {"success": False, "error": "本地模型未加载"})
        except Exception as e:
            logger.error(f"处理推理请求失败: {e}", exc_info=True)
            self._send_inference_result(task_id, {"success": False, "error": str(e)})
    
    def _send_inference_result(self, task_id: str, result: Dict[str, Any]):
        """发送推理结果"""
        try:
            result_data = json.dumps({
                "type": "inference_result",
                "task_id": task_id,
                "result": result,
                "timestamp": time.time()
            })
            
            if self.cluster_manager and self.cluster_manager.lan_node:
                for node in self.cluster_manager.lan_node.get_nodes():
                    if node.status.value == "connected":
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(3)
                            sock.connect((node.ip_address, self.cluster_manager.lan_node.DATA_PORT))
                            sock.sendall((result_data + "\n").encode('utf-8'))
                            sock.close()
                        except (socket.error, OSError) as e:
                            logger.debug(f"节点连接失败: {e}")
        except Exception as e:
            logger.error(f"发送推理结果失败: {e}", exc_info=True)
    
    def _handle_inference_result(self, message, addr):
        """处理推理结果"""
        try:
            task_id = message.get("task_id")
            result = message.get("result", {})
            
            if task_id in self.inference_tasks:
                task = self.inference_tasks[task_id]
                if result.get("success"):
                    task.status = "completed"
                    task.result = result.get("result", "")
                else:
                    task.status = "failed"
                    task.error = result.get("error", "Unknown error")
                task.completed_at = time.time()
                task.progress = 100.0
                
                logger.info(f"推理任务 {task_id[:8]} 完成")
        except Exception as e:
            logger.error(f"处理推理结果失败: {e}", exc_info=True)
    
    def submit_inference(self, model_name: str, prompt: str, 
                        max_tokens: int = 512, temperature: float = 0.7) -> str:
        """提交推理任务"""
        import uuid
        
        task_id = str(uuid.uuid4())
        task = InferenceTask(
            task_id=task_id,
            model_name=model_name,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            status="pending",
            created_at=time.time()
        )
        
        self.inference_tasks[task_id] = task
        
        # 尝试使用本地模型或分配到集群
        result = self._execute_inference(task)
        return result
    
    def _execute_inference(self, task: InferenceTask) -> str:
        """执行推理（本地或分布式）"""
        # 首先检查本地模型是否可用
        if self.local_model_service and self.local_model_service.is_loaded:
            try:
                result = self.local_model_service.chat(task.prompt, task.max_tokens)
                task.status = "completed"
                task.result = result
                task.progress = 100.0
                task.completed_at = time.time()
                return result
            except Exception as e:
                logger.error(f"本地推理失败: {e}", exc_info=True)
        
        # 如果本地不可用，尝试分布式推理
        if self.cluster_manager:
            nodes = self.cluster_manager.get_nodes()
            available_nodes = [n for n in nodes if n.status.value == "connected" and n.gpu_info]
            
            if available_nodes:
                # 选择显存最多的节点
                best_node = max(available_nodes, key=lambda n: n.gpu_info.get("available_memory_mb", 0))
                return self._send_task_to_node(task, best_node)
        
        return "无法找到可用的推理节点"
    
    def _send_task_to_node(self, task: InferenceTask, node) -> str:
        """发送推理任务到指定节点"""
        try:
            task_data = json.dumps({
                "type": "inference_request",
                "task_id": task.task_id,
                "model_name": task.model_name,
                "prompt": task.prompt,
                "max_tokens": task.max_tokens,
                "temperature": task.temperature,
                "timestamp": time.time()
            })
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(60)
            sock.connect((node.ip_address, self.cluster_manager.lan_node.DATA_PORT))
            sock.sendall((task_data + "\n").encode('utf-8'))
            
            # 等待响应
            buffer = ""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                if '\n' in buffer:
                    line, _ = buffer.split('\n', 1)
                    response = json.loads(line)
                    sock.close()
                    
                    if response.get("type") == "inference_result":
                        result = response.get("result", {})
                        if result.get("success"):
                            return result.get("result", "")
                        else:
                            return f"远程推理失败: {result.get('error')}"
            
            sock.close()
            return "远程推理超时"
        except Exception as e:
            return f"发送任务失败: {str(e)}"
    
    def stream_inference(self, model_name: str, prompt: str, 
                        max_tokens: int = 512) -> Generator[str, None, None]:
        """流式推理"""
        # 优先使用本地模型
        if self.local_model_service and self.local_model_service.is_loaded:
            for chunk in self.local_model_service.chat_stream(prompt, max_tokens):
                yield chunk
            return
        
        # 分布式流式推理（简化实现）
        result = self.submit_inference(model_name, prompt, max_tokens)
        yield result
    
    def get_task(self, task_id: str) -> Optional[InferenceTask]:
        """获取任务信息"""
        return self.inference_tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.inference_tasks:
            del self.inference_tasks[task_id]
            return True
        return False


# 测试
if __name__ == "__main__":
    from . import ClusterManager
    
    cluster = ClusterManager()
    inference = DistributedInferenceService(cluster)
    
    cluster.start()
    inference.start()
    
    print("\n按 Ctrl+C 停止...")
    try:
        while True:
            time.sleep(1)
            cluster.lan_node.send_heartbeat()
    except KeyboardInterrupt:
        inference.stop()
        cluster.stop()
