"""
系统资源监控模块
用于检测系统中的CPU、内存、NPU等资源信息
"""

import platform
import psutil
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import subprocess
import os


@dataclass
class CPUInfo:
    """CPU信息数据类"""
    model: str
    cores: int
    logical_cores: int
    frequency: float  # MHz
    usage_percent: float  # %
    temperature: float  # 摄氏度


@dataclass
class MemoryInfo:
    """内存信息数据类"""
    total_mb: int
    used_mb: int
    free_mb: int
    available_mb: int
    usage_percent: float  # %


@dataclass
class NPUInfo:
    """NPU信息数据类"""
    id: int
    name: str
    vendor: str
    memory_total_mb: int
    memory_used_mb: int
    memory_free_mb: int
    utilization: int  # %
    temperature: int  # 摄氏度
    is_available: bool = True


@dataclass
class SystemInfo:
    """系统信息数据类"""
    platform: str
    hostname: str
    os_version: str
    cpu: CPUInfo
    memory: MemoryInfo
    npus: List[NPUInfo]
    gpu_info: Dict[str, Any] = None


class SystemMonitor:
    """系统资源监控器"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.hostname = platform.node()
    
    def get_cpu_info(self) -> CPUInfo:
        """获取CPU信息"""
        try:
            cpu_count = psutil.cpu_count(logical=False) or 0
            logical_count = psutil.cpu_count(logical=True) or 0
            
            # 获取CPU型号
            model = "Unknown"
            if self.platform == "windows":
                try:
                    result = subprocess.run(
                        ["wmic", "cpu", "get", "Name", "/value"],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.strip().split('\n'):
                        if line.startswith("Name="):
                            model = line.split('=', 1)[1].strip()
                            break
                except:
                    pass
            elif self.platform == "linux":
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        for line in f:
                            if line.startswith("model name"):
                                model = line.split(':', 1)[1].strip()
                                break
                except:
                    pass
            
            # 获取CPU频率
            freq = psutil.cpu_freq()
            frequency = freq.current if freq else 0.0
            
            # 获取CPU使用率
            usage = psutil.cpu_percent(interval=0.1)
            
            # 获取CPU温度
            temp = self._get_cpu_temperature()
            
            return CPUInfo(
                model=model,
                cores=cpu_count,
                logical_cores=logical_count,
                frequency=frequency,
                usage_percent=usage,
                temperature=temp
            )
        except Exception as e:
            print(f"[SystemMonitor] 获取CPU信息失败: {e}")
            return CPUInfo(
                model="Unknown",
                cores=0,
                logical_cores=0,
                frequency=0.0,
                usage_percent=0.0,
                temperature=0.0
            )
    
    def _get_cpu_temperature(self) -> float:
        """获取CPU温度"""
        try:
            if self.platform == "windows":
                try:
                    result = subprocess.run(
                        ["wmic", "cpu", "get", "CurrentTemperature", "/value"],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.strip().split('\n'):
                        if line.startswith("CurrentTemperature="):
                            temp = int(line.split('=', 1)[1].strip())
                            return temp / 10.0 if temp > 0 else 0.0
                except:
                    pass
            elif self.platform == "linux":
                # 尝试读取常见的温度文件
                temp_files = [
                    "/sys/class/thermal/thermal_zone0/temp",
                    "/sys/class/hwmon/hwmon0/temp1_input"
                ]
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        try:
                            with open(temp_file, "r") as f:
                                temp = int(f.read().strip())
                                return temp / 1000.0 if temp > 0 else 0.0
                        except:
                            pass
        except Exception:
            pass
        return 0.0
    
    def get_memory_info(self) -> MemoryInfo:
        """获取内存信息"""
        try:
            mem = psutil.virtual_memory()
            return MemoryInfo(
                total_mb=int(mem.total / (1024 * 1024)),
                used_mb=int(mem.used / (1024 * 1024)),
                free_mb=int(mem.free / (1024 * 1024)),
                available_mb=int(mem.available / (1024 * 1024)),
                usage_percent=mem.percent
            )
        except Exception as e:
            print(f"[SystemMonitor] 获取内存信息失败: {e}")
            return MemoryInfo(
                total_mb=0,
                used_mb=0,
                free_mb=0,
                available_mb=0,
                usage_percent=0.0
            )
    
    def get_npu_info(self) -> List[NPUInfo]:
        """获取NPU信息"""
        npus = []
        
        try:
            if self.platform == "windows":
                npus.extend(self._detect_npu_windows())
            elif self.platform == "linux":
                npus.extend(self._detect_npu_linux())
            
            # 尝试通过环境变量检测
            npus.extend(self._detect_npu_environment())
            
        except Exception as e:
            print(f"[SystemMonitor] 获取NPU信息失败: {e}")
        
        return npus
    
    def _detect_npu_windows(self) -> List[NPUInfo]:
        """Windows平台NPU检测"""
        npus = []
        
        try:
            # 检测Intel NPU
            result = subprocess.run(
                ["wmic", "path", "win32_pnpentity", "where", "name like '%NPU%'", "get", "Name,DeviceID", "/format:list"],
                capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore'
            )
            lines = result.stdout.strip().split('\n')
            npu_name = ""
            device_id = ""
            
            for line in lines:
                if line.startswith("Name="):
                    npu_name = line.split('=', 1)[1].strip()
                elif line.startswith("DeviceID="):
                    device_id = line.split('=', 1)[1].strip()
                
                if npu_name and device_id:
                    npus.append(NPUInfo(
                        id=len(npus),
                        name=npu_name,
                        vendor="Intel" if "Intel" in npu_name else "Unknown",
                        memory_total_mb=0,
                        memory_used_mb=0,
                        memory_free_mb=0,
                        utilization=0,
                        temperature=0
                    ))
                    npu_name = ""
                    device_id = ""
        except:
            pass
        
        return npus
    
    def _detect_npu_linux(self) -> List[NPUInfo]:
        """Linux平台NPU检测"""
        npus = []
        
        try:
            # 检查常见的NPU设备路径
            npu_paths = ["/dev/accel", "/dev/dri/renderD128"]
            for path in npu_paths:
                if os.path.exists(path):
                    npus.append(NPUInfo(
                        id=len(npus),
                        name="NPU Device",
                        vendor="Unknown",
                        memory_total_mb=0,
                        memory_used_mb=0,
                        memory_free_mb=0,
                        utilization=0,
                        temperature=0
                    ))
        except:
            pass
        
        return npus
    
    def _detect_npu_environment(self) -> List[NPUInfo]:
        """通过环境变量检测NPU"""
        npus = []
        
        # 检查Intel NPU环境变量
        if os.environ.get("NPU_VISIBLE_DEVICES"):
            npus.append(NPUInfo(
                id=len(npus),
                name="Intel NPU",
                vendor="Intel",
                memory_total_mb=0,
                memory_used_mb=0,
                memory_free_mb=0,
                utilization=0,
                temperature=0
            ))
        
        return npus
    
    def get_system_info(self, include_gpu: bool = False) -> SystemInfo:
        """获取完整的系统信息"""
        gpu_info = None
        
        if include_gpu:
            try:
                from .gpu_detector import GPUDetector
                detector = GPUDetector()
                detector.detect()
                gpu_info = detector.to_dict()
            except Exception as e:
                print(f"[SystemMonitor] 获取GPU信息失败: {e}")
        
        return SystemInfo(
            platform=self.platform,
            hostname=self.hostname,
            os_version=platform.version(),
            cpu=self.get_cpu_info(),
            memory=self.get_memory_info(),
            npus=self.get_npu_info(),
            gpu_info=gpu_info
        )
    
    def to_dict(self, include_gpu: bool = False) -> Dict[str, Any]:
        """转换为字典格式"""
        system_info = self.get_system_info(include_gpu)
        
        return {
            "platform": system_info.platform,
            "hostname": system_info.hostname,
            "os_version": system_info.os_version,
            "cpu": {
                "model": system_info.cpu.model,
                "cores": system_info.cpu.cores,
                "logical_cores": system_info.cpu.logical_cores,
                "frequency_mhz": system_info.cpu.frequency,
                "usage_percent": system_info.cpu.usage_percent,
                "temperature_c": system_info.cpu.temperature
            },
            "memory": {
                "total_mb": system_info.memory.total_mb,
                "used_mb": system_info.memory.used_mb,
                "free_mb": system_info.memory.free_mb,
                "available_mb": system_info.memory.available_mb,
                "usage_percent": system_info.memory.usage_percent
            },
            "npu_count": len(system_info.npus),
            "npus": [
                {
                    "id": n.id,
                    "name": n.name,
                    "vendor": n.vendor,
                    "memory_total_mb": n.memory_total_mb,
                    "memory_used_mb": n.memory_used_mb,
                    "memory_free_mb": n.memory_free_mb,
                    "utilization_percent": n.utilization,
                    "temperature_c": n.temperature,
                    "is_available": n.is_available
                } for n in system_info.npus
            ],
            "gpu_info": system_info.gpu_info
        }
    
    def to_json(self, include_gpu: bool = False) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(include_gpu), indent=2)


# 测试
if __name__ == "__main__":
    monitor = SystemMonitor()
    
    print("=== 系统资源信息 ===")
    print(monitor.to_json(include_gpu=True))