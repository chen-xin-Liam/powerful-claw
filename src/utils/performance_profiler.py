import functools
import time
from typing import Callable, Any, Dict
from datetime import datetime


class PerformanceProfiler:
    """性能分析器 - 支持行级分析和内存分析"""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
    
    def profile_time(self, func: Callable) -> Callable:
        """装饰器：分析函数执行时间"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not self.enabled:
                return func(*args, **kwargs)
            
            start_time = time.time()
            start_cpu = time.process_time()
            
            try:
                result = func(*args, **kwargs)
            finally:
                elapsed_time = time.time() - start_time
                cpu_time = time.process_time() - start_cpu
                
                print(f"⏱️ [{func.__name__}] 执行时间: {elapsed_time:.4f}s (CPU: {cpu_time:.4f}s)")
            
            return result
        return wrapper
    
    def profile_memory(self, func: Callable) -> Callable:
        """装饰器：分析函数内存使用（需要memory_profiler）"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not self.enabled:
                return func(*args, **kwargs)
            
            try:
                from memory_profiler import memory_usage
                from memory_profiler import profile as mem_profile
                return mem_profile(func)(*args, **kwargs)
            except ImportError:
                print("⚠️ memory_profiler 未安装，跳过内存分析")
                return func(*args, **kwargs)
        return wrapper
    
    def profile_line(self, func: Callable) -> Callable:
        """装饰器：行级性能分析（需要line_profiler）"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not self.enabled:
                return func(*args, **kwargs)
            
            try:
                from line_profiler import LineProfiler
                lp = LineProfiler()
                lp_wrapper = lp(func)
                result = lp_wrapper(*args, **kwargs)
                lp.print_stats()
                return result
            except ImportError:
                print("⚠️ line_profiler 未安装，跳进行级分析")
                return func(*args, **kwargs)
        return wrapper
    
    def profile_all(self, func: Callable) -> Callable:
        """装饰器：综合性能分析"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not self.enabled:
                return func(*args, **kwargs)
            
            print(f"\n📊 开始分析: {func.__name__}")
            print("=" * 50)
            
            # 时间分析
            start_time = time.time()
            
            # 内存分析
            try:
                from memory_profiler import memory_usage
                mem_usage = memory_usage((func, args, kwargs))
                max_mem = max(mem_usage)
                avg_mem = sum(mem_usage) / len(mem_usage)
            except ImportError:
                max_mem = 0
                avg_mem = 0
            
            elapsed_time = time.time() - start_time
            
            print(f"\n📈 性能报告: {func.__name__}")
            print(f"  执行时间: {elapsed_time:.4f}s")
            print(f"  最大内存: {max_mem:.2f} MB")
            print(f"  平均内存: {avg_mem:.2f} MB")
            print("=" * 50)
            
            return func(*args, **kwargs)
        return wrapper


# 创建全局性能分析器实例
performance_profiler = PerformanceProfiler(enabled=False)


def get_execution_stats() -> Dict[str, Any]:
    """获取当前执行统计信息"""
    import psutil
    
    process = psutil.Process()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "pid": process.pid,
        "cpu_percent": process.cpu_percent(),
        "memory_percent": process.memory_percent(),
        "memory_rss_mb": process.memory_info().rss / (1024 * 1024),
        "threads_count": process.num_threads(),
        "open_files_count": len(process.open_files()) if hasattr(process, 'open_files') else 0
    }
