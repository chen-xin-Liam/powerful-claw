"""
GPU资源检测与评估模块
用于检测系统中的GPU资源，包括型号、显存、计算能力等
"""

import platform
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import subprocess
import json

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GPUInfo:
    """GPU信息数据类"""
    id: int
    name: str
    vendor: str
    memory_total: int  # MB
    memory_used: int   # MB
    memory_free: int   # MB
    utilization: int   # %
    temperature: int   # 摄氏度
    compute_capability: str
    is_available: bool = True


class GPUDetector:
    """GPU资源检测器"""

    def __init__(self):
        self.gpus: List[GPUInfo] = []
        self.platform = platform.system().lower()

    def detect(self) -> List[GPUInfo]:
        """检测所有可用的GPU"""
        self.gpus = []

        if self.platform == "windows":
            self._detect_windows()
        elif self.platform == "linux":
            self._detect_linux()
        else:
            self._detect_fallback()

        return self.gpus

    def _detect_windows(self):
        """Windows平台GPU检测"""
        try:
            # 使用nvidia-smi获取GPU信息
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 7:
                        try:
                            gpu = GPUInfo(
                                id=int(parts[0]),
                                name=parts[1],
                                vendor="NVIDIA",
                                memory_total=int(parts[2]),
                                memory_used=int(parts[3]),
                                memory_free=int(parts[4]),
                                utilization=int(parts[5]),
                                temperature=int(parts[6]),
                                compute_capability=self._get_compute_capability(int(parts[0]))
                            )
                            self.gpus.append(gpu)
                        except ValueError as e:
                            logger.debug(f"跳过无法解析的 nvidia-smi 行 '{line}': {e}")
            else:
                logger.debug(f"nvidia-smi 返回非零退出码 {result.returncode}，尝试 fallback")
                self._detect_fallback()
        except FileNotFoundError:
            # Windows 上无 NVIDIA 驱动是常态，不报错
            logger.debug("nvidia-smi 不可用，尝试 fallback 检测")
            self._detect_fallback()
        except subprocess.TimeoutExpired as e:
            logger.warning(f"nvidia-smi 检测超时（30s）: {e}")
            self._detect_fallback()
        except Exception as e:
            logger.warning(f"Windows GPU 检测失败，尝试 fallback: {e}")
            self._detect_fallback()

    def _detect_linux(self):
        """Linux平台GPU检测"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 7:
                        try:
                            gpu = GPUInfo(
                                id=int(parts[0]),
                                name=parts[1],
                                vendor="NVIDIA",
                                memory_total=int(parts[2]),
                                memory_used=int(parts[3]),
                                memory_free=int(parts[4]),
                                utilization=int(parts[5]),
                                temperature=int(parts[6]),
                                compute_capability=self._get_compute_capability(int(parts[0]))
                            )
                            self.gpus.append(gpu)
                        except ValueError as e:
                            logger.debug(f"跳过无法解析的 nvidia-smi 行 '{line}': {e}")
            else:
                logger.debug(f"nvidia-smi 返回非零退出码 {result.returncode}，尝试 fallback")
                self._detect_fallback()
        except FileNotFoundError:
            logger.debug("nvidia-smi 不可用，尝试 fallback 检测")
            self._detect_fallback()
        except subprocess.TimeoutExpired as e:
            logger.warning(f"nvidia-smi 检测超时（30s）: {e}")
            self._detect_fallback()
        except Exception as e:
            logger.warning(f"Linux GPU 检测失败，尝试 fallback: {e}")
            self._detect_fallback()

    def _detect_fallback(self):
        """备用检测方法（使用torch）"""
        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    gpu = GPUInfo(
                        id=i,
                        name=props.name,
                        vendor="NVIDIA",
                        memory_total=int(props.total_memory / (1024 * 1024)),
                        memory_used=0,
                        memory_free=int(props.total_memory / (1024 * 1024)),
                        utilization=0,
                        temperature=0,
                        compute_capability=f"{props.major}.{props.minor}"
                    )
                    self.gpus.append(gpu)
        except ImportError:
            # torch 未安装属于常态，不报错
            logger.debug("torch 不可用，跳过 GPU fallback 检测")
        except Exception as e:
            logger.warning(f"torch GPU fallback 检测失败: {e}")

    def _get_compute_capability(self, gpu_id: int) -> str:
        """获取GPU计算能力"""
        try:
            result = subprocess.run(
                ["nvidia-smi", f"--query-gpu=compute_cap", f"--id={gpu_id}", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            logger.debug("nvidia-smi 不可用，无法获取 compute_capability")
        except subprocess.TimeoutExpired as e:
            logger.warning(f"获取 compute_capability 超时（10s）: {e}")
        except Exception as e:
            logger.debug(f"获取 compute_capability 失败: {e}")
        return "unknown"

    def get_total_gpu_memory(self) -> int:
        """获取总GPU显存（MB）"""
        return sum(gpu.memory_total for gpu in self.gpus)

    def get_total_available_memory(self) -> int:
        """获取可用显存（MB）"""
        return sum(gpu.memory_free for gpu in self.gpus)

    def get_average_utilization(self) -> float:
        """获取平均GPU使用率"""
        if not self.gpus:
            return 0.0
        return sum(gpu.utilization for gpu in self.gpus) / len(self.gpus)

    def get_strongest_gpu(self) -> Optional[GPUInfo]:
        """获取性能最强的GPU（按显存排序）"""
        if not self.gpus:
            return None
        return max(self.gpus, key=lambda g: g.memory_total)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "platform": self.platform,
            "gpu_count": len(self.gpus),
            "total_memory_mb": self.get_total_gpu_memory(),
            "available_memory_mb": self.get_total_available_memory(),
            "average_utilization": self.get_average_utilization(),
            "gpus": [
                {
                    "id": g.id,
                    "name": g.name,
                    "vendor": g.vendor,
                    "memory_total_mb": g.memory_total,
                    "memory_used_mb": g.memory_used,
                    "memory_free_mb": g.memory_free,
                    "utilization_percent": g.utilization,
                    "temperature_c": g.temperature,
                    "compute_capability": g.compute_capability,
                    "is_available": g.is_available
                } for g in self.gpus
            ]
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2)


# 测试
if __name__ == "__main__":
    detector = GPUDetector()
    gpus = detector.detect()

    print("GPU检测结果:")
    print(detector.to_json())
