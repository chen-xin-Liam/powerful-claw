import psutil
import platform
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel
import threading
import time


class SystemInfo(BaseModel):
    """系统信息模型"""
    cpu_count: int
    cpu_percent: float
    memory_total: float
    memory_available: float
    memory_percent: float
    disk_total: float
    disk_used: float
    disk_percent: float
    network_sent: float
    network_recv: float
    boot_time: datetime
    platform: str
    platform_version: str
    python_version: str


class ProcessInfo(BaseModel):
    """进程信息模型"""
    pid: int
    name: str
    cmdline: str
    cpu_percent: float
    memory_percent: float
    memory_rss: float
    status: str
    create_time: datetime
    username: Optional[str]


class SystemMonitor:
    """系统监控服务 - 使用psutil监控系统资源"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._last_net_io = psutil.net_io_counters()
        self._last_time = time.time()
        self._initialized = True
    
    def get_system_info(self) -> SystemInfo:
        """获取系统基本信息"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        return SystemInfo(
            cpu_count=psutil.cpu_count(logical=True) or 0,
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_total=self._bytes_to_gb(psutil.virtual_memory().total),
            memory_available=self._bytes_to_gb(psutil.virtual_memory().available),
            memory_percent=psutil.virtual_memory().percent,
            disk_total=self._bytes_to_gb(psutil.disk_usage('/').total),
            disk_used=self._bytes_to_gb(psutil.disk_usage('/').used),
            disk_percent=psutil.disk_usage('/').percent,
            network_sent=self._get_network_speed()[0],
            network_recv=self._get_network_speed()[1],
            boot_time=boot_time,
            platform=platform.system(),
            platform_version=platform.version(),
            python_version=platform.python_version()
        )
    
    def get_process_info(self, pid: Optional[int] = None) -> ProcessInfo:
        """获取进程信息"""
        if pid is None:
            pid = psutil.Process().pid
        
        try:
            process = psutil.Process(pid)
            create_time = datetime.fromtimestamp(process.create_time())
            
            return ProcessInfo(
                pid=process.pid,
                name=process.name(),
                cmdline=' '.join(process.cmdline())[:200],
                cpu_percent=process.cpu_percent(interval=0.1),
                memory_percent=process.memory_percent(),
                memory_rss=self._bytes_to_mb(process.memory_info().rss),
                status=process.status(),
                create_time=create_time,
                username=process.username() if platform.system() != 'Windows' else None
            )
        except psutil.NoSuchProcess:
            raise ValueError(f"Process with pid {pid} not found")
    
    def get_running_processes(self, limit: int = 20) -> list[ProcessInfo]:
        """获取运行中的进程列表"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(self.get_process_info(proc.info['pid']))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # 按内存使用排序
        processes.sort(key=lambda p: p.memory_percent, reverse=True)
        return processes[:limit]
    
    def get_gpu_info(self) -> list[Dict[str, Any]]:
        """获取GPU信息（如果可用）"""
        gpus = []
        try:
            # 尝试使用nvidia-smi（如果安装了）
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.strip().split(',')
                    if len(parts) == 4:
                        gpus.append({
                            'name': parts[0].strip(),
                            'memory_total': float(parts[1].strip()),
                            'memory_used': float(parts[2].strip()),
                            'memory_free': float(parts[3].strip()),
                            'memory_percent': (float(parts[2].strip()) / float(parts[1].strip())) * 100
                        })
        except:
            pass
        
        return gpus
    
    def kill_process(self, pid: int) -> bool:
        """终止进程"""
        try:
            process = psutil.Process(pid)
            process.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def optimize_memory(self) -> Dict[str, Any]:
        """尝试优化内存使用"""
        import gc
        before = psutil.Process().memory_info().rss
        
        # 强制垃圾回收
        gc.collect()
        
        after = psutil.Process().memory_info().rss
        freed = self._bytes_to_mb(before - after)
        
        return {
            'freed_mb': max(0, freed),
            'before_mb': self._bytes_to_mb(before),
            'after_mb': self._bytes_to_mb(after)
        }
    
    def _get_network_speed(self) -> tuple[float, float]:
        """获取网络速度（MB/s）"""
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        
        duration = current_time - self._last_time
        if duration < 0.1:
            return 0.0, 0.0
        
        sent = (current_net_io.bytes_sent - self._last_net_io.bytes_sent) / duration
        recv = (current_net_io.bytes_recv - self._last_net_io.bytes_recv) / duration
        
        self._last_net_io = current_net_io
        self._last_time = current_time
        
        return self._bytes_to_mb(sent), self._bytes_to_mb(recv)
    
    @staticmethod
    def _bytes_to_mb(bytes_val: int) -> float:
        """字节转换为MB"""
        return round(bytes_val / (1024 * 1024), 2)
    
    @staticmethod
    def _bytes_to_gb(bytes_val: int) -> float:
        """字节转换为GB"""
        return round(bytes_val / (1024 * 1024 * 1024), 2)


# 创建全局监控实例
system_monitor = SystemMonitor()
