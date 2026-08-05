import psutil
import platform
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
import threading
import time

from src.utils.logger import get_logger
from src.utils.errors import ValidationError
from src.utils.error_codes import ErrorCode

logger = get_logger(__name__)


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


def _default_disk_path() -> str:
    """按平台返回默认磁盘路径，避免 Windows 上 disk_usage('/') 抛 FileNotFoundError。"""
    return "C:\\" if platform.system() == "Windows" else "/"


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

        # psutil.net_io_counters() 在某些容器/沙箱环境可能抛异常，做兜底
        try:
            self._last_net_io = psutil.net_io_counters()
        except Exception as e:
            logger.warning(f"获取网络 IO 计数器失败，使用零值兜底: {e}")
            self._last_net_io = None
        self._last_time = time.time()
        self._initialized = True

    def get_system_info(self) -> SystemInfo:
        """获取系统基本信息。

        监控类采用软失败策略：逐字段保护，异常时降级为默认值，
        确保即使某项指标获取失败也能返回完整 SystemInfo。
        """
        # boot_time
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
        except (psutil.AccessDenied, OSError, RuntimeError) as e:
            logger.warning(f"无法获取 boot_time: {e}")
            boot_time = datetime.now()

        # CPU
        try:
            cpu_count = psutil.cpu_count(logical=True) or 0
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"无法获取 CPU 信息: {e}")
            cpu_count, cpu_percent = 0, 0.0

        # 内存
        try:
            vm = psutil.virtual_memory()
            memory_total = self._bytes_to_gb(vm.total)
            memory_available = self._bytes_to_gb(vm.available)
            memory_percent = vm.percent
        except Exception as e:
            logger.warning(f"无法获取内存信息: {e}")
            memory_total = memory_available = memory_percent = 0.0

        # 磁盘（Windows 上 '/' 不存在，必须按平台选路径）
        try:
            disk = psutil.disk_usage(_default_disk_path())
            disk_total = self._bytes_to_gb(disk.total)
            disk_used = self._bytes_to_gb(disk.used)
            disk_percent = disk.percent
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"无法获取磁盘使用率: {e}")
            disk_total = disk_used = disk_percent = 0.0

        # 网络
        try:
            net_sent, net_recv = self._get_network_speed()
        except Exception as e:
            logger.warning(f"无法获取网络速度: {e}")
            net_sent = net_recv = 0.0

        return SystemInfo(
            cpu_count=cpu_count,
            cpu_percent=cpu_percent,
            memory_total=memory_total,
            memory_available=memory_available,
            memory_percent=memory_percent,
            disk_total=disk_total,
            disk_used=disk_used,
            disk_percent=disk_percent,
            network_sent=net_sent,
            network_recv=net_recv,
            boot_time=boot_time,
            platform=platform.system(),
            platform_version=platform.version(),
            python_version=platform.python_version()
        )

    def get_process_info(self, pid: Optional[int] = None) -> ProcessInfo:
        """获取进程信息"""
        if pid is None:
            pid = psutil.Process().pid
        elif not isinstance(pid, int):
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"pid 必须是整数或 None，实际收到 {type(pid).__name__}",
                details={"arg": "pid", "value": pid},
            )
        elif pid <= 0:
            raise ValidationError(
                ErrorCode.E_VAL_OUT_OF_RANGE,
                f"pid 必须 > 0，实际收到 {pid}",
                details={"arg": "pid", "value": pid},
            )

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

    def get_running_processes(self, limit: int = 20) -> List[ProcessInfo]:
        """获取运行中的进程列表"""
        if not isinstance(limit, int) or limit <= 0:
            raise ValidationError(
                ErrorCode.E_VAL_OUT_OF_RANGE,
                f"limit 必须 > 0，实际收到 {limit}",
                details={"arg": "limit", "value": limit},
            )
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(self.get_process_info(proc.info['pid']))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                # 单个进程获取失败不影响整体
                logger.debug(f"跳过进程 {proc.info.get('pid')}: {e}")

        # 按内存使用排序
        processes.sort(key=lambda p: p.memory_percent, reverse=True)
        return processes[:limit]

    def get_gpu_info(self) -> List[Dict[str, Any]]:
        """获取GPU信息（如果可用）。

        软失败：nvidia-smi 不可用时返回空列表，不抛异常。
        """
        gpus = []
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.strip().split(',')
                    if len(parts) == 4:
                        try:
                            mem_total = float(parts[1].strip())
                            mem_used = float(parts[2].strip())
                            gpus.append({
                                'name': parts[0].strip(),
                                'memory_total': mem_total,
                                'memory_used': mem_used,
                                'memory_free': float(parts[3].strip()),
                                'memory_percent': (mem_used / mem_total) * 100 if mem_total else 0.0
                            })
                        except (ValueError, ZeroDivisionError) as e:
                            logger.debug(f"跳过无法解析的 nvidia-smi 输出行 '{line}': {e}")
        except FileNotFoundError:
            # 无 NVIDIA 驱动是常态，降级为空列表
            logger.debug("nvidia-smi 不可用，跳过 GPU 信息采集")
        except subprocess.TimeoutExpired as e:
            logger.warning(f"nvidia-smi 查询超时（10s）: {e}")
        except Exception as e:
            logger.warning(f"获取 GPU 信息失败: {e}")

        return gpus

    def kill_process(self, pid: int) -> bool:
        """终止进程"""
        if not isinstance(pid, int) or pid <= 0:
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"pid 必须是正整数，实际收到 {pid}",
                details={"arg": "pid", "value": pid},
            )
        try:
            process = psutil.Process(pid)
            process.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def optimize_memory(self) -> Dict[str, Any]:
        """尝试优化内存使用"""
        import gc
        try:
            before = psutil.Process().memory_info().rss
        except psutil.AccessDenied as e:
            logger.warning(f"无法获取内存信息，无法优化: {e}")
            return {'freed_mb': 0.0, 'before_mb': 0.0, 'after_mb': 0.0}

        # 强制垃圾回收
        gc.collect()

        try:
            after = psutil.Process().memory_info().rss
        except psutil.AccessDenied as e:
            logger.warning(f"无法获取优化后内存信息: {e}")
            return {'freed_mb': 0.0, 'before_mb': self._bytes_to_mb(before), 'after_mb': 0.0}

        freed = self._bytes_to_mb(before - after)

        return {
            'freed_mb': max(0, freed),
            'before_mb': self._bytes_to_mb(before),
            'after_mb': self._bytes_to_mb(after)
        }

    def _get_network_speed(self) -> Tuple[float, float]:
        """获取网络速度（MB/s）"""
        current_net_io = psutil.net_io_counters()
        current_time = time.time()

        if self._last_net_io is None:
            # 首次调用或之前初始化失败
            self._last_net_io = current_net_io
            self._last_time = current_time
            return 0.0, 0.0

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
