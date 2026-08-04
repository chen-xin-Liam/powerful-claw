"""
Python 库调用工具 - 让 AI 可以使用所有已安装的库
"""

import sys
import importlib
import pkgutil
from typing import Dict, List, Any, Optional


class PythonLibraryTool:
    """Python 库调用工具"""
    
    @classmethod
    def list_installed_libraries(cls) -> Dict[str, str]:
        """列出所有已安装的库"""
        libraries = {}
        
        # 获取所有已安装的包
        for importer, modname, ispkg in pkgutil.iter_modules():
            try:
                module = importlib.import_module(modname)
                if hasattr(module, '__version__'):
                    libraries[modname] = module.__version__
                elif hasattr(module, 'VERSION'):
                    libraries[modname] = str(module.VERSION)
                else:
                    libraries[modname] = "unknown"
            except:
                pass
        
        return libraries
    
    @classmethod
    def get_library_info(cls, library_name: str) -> Dict[str, Any]:
        """获取库的详细信息"""
        try:
            module = importlib.import_module(library_name)
            
            info = {
                "name": library_name,
                "version": getattr(module, '__version__', 'unknown'),
                "file": getattr(module, '__file__', 'built-in'),
                "doc": module.__doc__[:500] if module.__doc__ else None,
                "attributes": []
            }
            
            # 获取公共属性和方法
            for attr in dir(module):
                if not attr.startswith('_'):
                    obj = getattr(module, attr)
                    if callable(obj):
                        info["attributes"].append({
                            "name": attr,
                            "type": "function",
                            "doc": obj.__doc__[:100] if obj.__doc__ else None
                        })
                    else:
                        info["attributes"].append({
                            "name": attr,
                            "type": "variable"
                        })
            
            # 限制返回的属性数量
            if len(info["attributes"]) > 50:
                info["attributes"] = info["attributes"][:50]
            
            return info
        except ImportError as e:
            return {"error": f"库未安装：{library_name}", "details": str(e)}
        except Exception as e:
            return {"error": f"获取信息失败：{str(e)}"}
    
    @classmethod
    def execute_with_library(cls, code: str, libraries: List[str] = None, timeout: int = 30) -> str:
        """
        执行 Python 代码，可以导入指定的库
        
        参数:
            code: 要执行的 Python 代码
            libraries: 需要导入的库列表
            timeout: 超时时间（秒）
        """
        import subprocess
        
        # 构建导入语句
        imports = ""
        if libraries:
            for lib in libraries:
                imports += f"import {lib}\n"
        
        full_code = imports + code
        
        try:
            result = subprocess.run(
                [sys.executable, '-c', full_code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=None
            )
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n\n"
            output += f"返回码：{result.returncode}"
            
            return output
        except subprocess.TimeoutExpired:
            return f"执行超时（{timeout}秒）"
        except Exception as e:
            return f"执行失败：{str(e)}"
    
    @classmethod
    def call_library_function(cls, library: str, function: str, args: List = None, kwargs: Dict = None) -> str:
        """
        调用库的函数
        
        参数:
            library: 库名
            function: 函数名
            args: 位置参数列表
            kwargs: 关键字参数字典
        """
        import importlib
        import json
        
        args = args or []
        kwargs = kwargs or {}
        
        try:
            # 导入库
            module = importlib.import_module(library)
            
            # 获取函数（支持嵌套属性，如 os.path.join）
            parts = function.split('.')
            obj = module
            for part in parts:
                obj = getattr(obj, part)
            
            # 调用函数
            result = obj(*args, **kwargs)
            
            # 尝试 JSON 序列化结果
            try:
                return json.dumps({"result": result}, default=str, ensure_ascii=False)
            except:
                return f"result: {result}"
        except ImportError:
            return f"错误：库 '{library}' 未安装"
        except AttributeError:
            return f"错误：库 '{library}' 中没有函数 '{function}'"
        except Exception as e:
            return f"调用失败：{str(e)}"
    
    @classmethod
    def get_project_libraries(cls) -> Dict[str, str]:
        """获取项目 requirements.txt 中定义的主要库"""
        # 项目中常用的库
        project_libs = {
            # AI 相关
            "openai": "OpenAI API 客户端",
            "ultralytics": "YOLO 目标检测",
            
            # 数据处理
            "numpy": "数值计算",
            "pandas": "数据分析",
            "scipy": "科学计算",
            
            # 图像处理
            "opencv-python": "计算机视觉",
            "pillow": "图像处理",
            
            # 音频处理
            "librosa": "音频分析",
            "pydub": "音频处理",
            "sounddevice": "音频设备",
            
            # 视频处理
            "moviepy": "视频编辑",
            "ffmpeg-python": "FFmpeg 绑定",
            "decord": "视频解码",
            
            # 文档处理
            "python-docx": "Word 文档",
            "openpyxl": "Excel 文档",
            "PyPDF2": "PDF 处理",
            "pdfplumber": "PDF 解析",
            
            # 可视化
            "matplotlib": "绘图库",
            "seaborn": "统计图表",
            "plotly": "交互式图表",
            
            # NLP
            "thulac": "中文分词",
            "snownlp": "中文 NLP",
            "gensim": "主题模型",
            
            # 深度学习
            "torch": "PyTorch",
            "transformers": "HuggingFace",
            
            # 网络请求
            "requests": "HTTP 客户端",
            "aiohttp": "异步 HTTP",
            
            # 工具库
            "pyautogui": "GUI 自动化",
            "keyboard": "键盘控制",
            "pyperclip": "剪贴板",
            "rich": "终端美化",
            "loguru": "日志库"
        }
        
        # 检查哪些已安装
        installed = {}
        for lib, desc in project_libs.items():
            try:
                module = importlib.import_module(lib.replace('-', '_'))
                version = getattr(module, '__version__', 'unknown')
                installed[lib] = {
                    "version": version,
                    "description": desc,
                    "status": "installed"
                }
            except ImportError:
                installed[lib] = {
                    "version": None,
                    "description": desc,
                    "status": "not_installed"
                }
        
        return installed


# 示例用法
if __name__ == "__main__":
    tool = PythonLibraryTool()
    
    print("=== 项目库状态 ===")
    libs = tool.get_project_libraries()
    for name, info in libs.items():
        status = "✅" if info["status"] == "installed" else "❌"
        version = f"v{info['version']}" if info['version'] else ""
        print(f"{status} {name} {version} - {info['description']}")
    
    print("\n=== 调用库函数示例 ===")
    # 调用 numpy 的函数
    result = tool.call_library_function("numpy", "array", [[1, 2, 3], [4, 5, 6]])
    print(f"numpy.array: {result}")
    
    # 调用 os 的函数
    result = tool.call_library_function("os", "getcwd")
    print(f"os.getcwd: {result}")
