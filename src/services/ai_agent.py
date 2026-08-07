"""
AIAgent - AI 代理系统
让 AI 知道自己能使用什么工具，并智能选择调用
"""

import json
import inspect
from typing import List, Dict, Any, Callable, Optional, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from src.services.python_library_tool import PythonLibraryTool

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: Type
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    parameters: List[ToolParameter]
    return_type: Type
    func: Callable
    category: str = "general"


class BaseTool(ABC):
    """工具基类"""
    
    @classmethod
    def get_tool_info(cls) -> ToolInfo:
        """获取工具信息"""
        signature = inspect.signature(cls.execute)
        parameters = []
        
        for name, param in signature.parameters.items():
            if name == 'cls' or name == 'self':
                continue
            
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            required = param.default == inspect.Parameter.empty
            default_value = param.default if not required else None
            
            parameters.append(ToolParameter(
                name=name,
                type=param_type,
                description="",
                required=required,
                default=default_value
            ))
        
        return ToolInfo(
            name=cls.__name__,
            description=cls.__doc__ or "",
            parameters=parameters,
            return_type=str,
            func=cls.execute,
            category=getattr(cls, "category", "general")
        )
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行工具"""
        pass


class AIAgent:
    """AI 代理系统"""
    
    def __init__(self):
        self.tools: Dict[str, ToolInfo] = {}
        self.tool_categories: Dict[str, List[str]] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        # 系统信息工具
        self.register_tool(SystemInfoTool)
        # 文件操作工具
        self.register_tool(FileReadTool)
        self.register_tool(FileWriteTool)
        # 命令执行工具
        self.register_tool(CommandTool)
        # 提权执行工具（管理员/root，双重授权）
        self.register_tool(PrivilegeTool)
        # 节点化数学计算器（evaluate 表达式 + build_graph 节点图）
        from src.services.math_calculator_tool import MathCalculatorTool
        self.register_tool(MathCalculatorTool)
        # 搜索工具
        self.register_tool(SearchTool)
        # Python 执行工具
        self.register_tool(PythonExecutorTool)
        self.register_tool(PythonEvalTool)
        # CMD 命令工具
        self.register_tool(CMDTool)
        # Python 包管理工具
        self.register_tool(PipTool)
        # Python 帮助工具
        self.register_tool(PythonHelpTool)
        # 库调用工具
        self.register_tool(LibraryListTool)
        self.register_tool(LibraryCallTool)
        self.register_tool(LibraryExecuteTool)
    
    def register_tool(self, tool_class: Type[BaseTool]):
        """注册工具"""
        tool_info = tool_class.get_tool_info()
        self.tools[tool_info.name] = tool_info
        
        if tool_info.category not in self.tool_categories:
            self.tool_categories[tool_info.category] = []
        self.tool_categories[tool_info.category].append(tool_info.name)
    
    def get_available_tools(self) -> List[ToolInfo]:
        """获取所有可用工具"""
        return list(self.tools.values())
    
    def get_tools_by_category(self, category: str) -> List[ToolInfo]:
        """按类别获取工具"""
        if category not in self.tool_categories:
            return []
        return [self.tools[name] for name in self.tool_categories[category]]
    
    def get_tool_descriptions(self, format: str = "json") -> str:
        """获取工具描述（用于 AI 提示词）"""
        tools_info = []
        
        for tool_info in self.tools.values():
            params = []
            for param in tool_info.parameters:
                params.append({
                    "name": param.name,
                    "type": param.type.__name__,
                    "description": param.description,
                    "required": param.required,
                    "default": param.default
                })
            
            tools_info.append({
                "name": tool_info.name,
                "description": tool_info.description,
                "parameters": params,
                "return_type": tool_info.return_type.__name__,
                "category": tool_info.category
            })
        
        if format == "json":
            return json.dumps(tools_info, indent=2, ensure_ascii=False)
        elif format == "markdown":
            return self._format_tools_markdown(tools_info)
        else:
            return str(tools_info)
    
    def _format_tools_markdown(self, tools_info: List[Dict]) -> str:
        """格式化工具为 Markdown 格式"""
        result = "# 可用工具列表\n\n"
        
        for category, tool_names in self.tool_categories.items():
            result += f"## {category}\n\n"
            
            for tool_name in tool_names:
                tool_info = self.tools[tool_name]
                result += f"### {tool_name}\n\n"
                result += f"**描述**: {tool_info.description}\n\n"
                result += "**参数**:\n"
                result += "| 参数名 | 类型 | 必填 | 默认值 |\n"
                result += "|--------|------|------|--------|\n"
                
                for param in tool_info.parameters:
                    result += f"| {param.name} | {param.type.__name__} | {param.required} | {param.default} |\n"
                
                result += "\n"
        
        return result
    
    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """调用工具"""
        if tool_name not in self.tools:
            raise ValueError(f"未知工具: {tool_name}")
        
        tool_info = self.tools[tool_name]
        
        # 检查必填参数
        for param in tool_info.parameters:
            if param.required and param.name not in kwargs:
                raise ValueError(f"缺少必填参数: {param.name}")
        
        # 设置默认值
        for param in tool_info.parameters:
            if param.name not in kwargs and param.default is not None:
                kwargs[param.name] = param.default
        
        try:
            result = tool_info.func(**kwargs)
            return {
                "success": True,
                "tool_name": tool_name,
                "result": result,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "tool_name": tool_name,
                "result": None,
                "error": str(e)
            }
    
    def think_and_act(self, task: str) -> Dict[str, Any]:
        """思考并执行任务（简化版推理）"""
        logger.info(f"收到任务: {task}")
        
        # 简单的工具选择逻辑
        if "读取" in task or "查看" in task or "内容" in task:
            return self.call_tool("FileReadTool", file_path="")
        elif "写入" in task or "创建" in task or "保存" in task:
            return self.call_tool("FileWriteTool", file_path="", content="")
        elif "命令" in task or "执行" in task or "运行" in task:
            return self.call_tool("CommandTool", command="")
        elif "搜索" in task or "查找" in task:
            return self.call_tool("SearchTool", query="")
        elif "系统" in task or "信息" in task:
            return self.call_tool("SystemInfoTool")
        else:
            return {
                "success": False,
                "tool_name": None,
                "result": None,
                "error": "无法识别任务类型，请明确指定要使用的工具"
            }


# ============ 内置工具实现 ============

class SystemInfoTool(BaseTool):
    """获取系统信息"""
    
    @classmethod
    def execute(cls) -> str:
        import platform
        import os
        
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "current_directory": os.getcwd()
        }
        return json.dumps(info, indent=2)


class FileReadTool(BaseTool):
    """读取文件内容
    
    参数:
        file_path: 文件路径
    """
    
    @classmethod
    def execute(cls, file_path: str) -> str:
        if not file_path:
            return "错误：请提供文件路径"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"读取失败: {str(e)}"


class FileWriteTool(BaseTool):
    """写入文件内容
    
    参数:
        file_path: 文件路径
        content: 要写入的内容
        append: 是否追加模式（默认False）
    """
    
    @classmethod
    def execute(cls, file_path: str, content: str, append: bool = False) -> str:
        if not file_path:
            return "错误：请提供文件路径"
        
        mode = 'a' if append else 'w'
        try:
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            return f"文件写入成功: {file_path}"
        except Exception as e:
            return f"写入失败: {str(e)}"


class CommandTool(BaseTool):
    """执行系统命令
    
    参数:
        command: 要执行的命令
        cwd: 工作目录（可选）
    """
    
    @classmethod
    def execute(cls, command: str, cwd: str = None) -> str:
        import subprocess
        
        if not command:
            return "错误：请提供命令"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60
            )
            return f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n\n返回码: {result.returncode}"
        except subprocess.TimeoutExpired:
            return "命令执行超时"
        except Exception as e:
            return f"执行失败: {str(e)}"


class PrivilegeTool(BaseTool):
    """以管理员/root 权限执行命令（提权执行）

    执行前需双重授权：① 项目二次授权（弹窗/input）② OS 系统授权（UAC/sudo）。
    适用于安装系统服务、修改系统配置等需要特权的操作。

    参数:
        command: 要以特权执行的命令
        reason: 提权原因（用于二次授权提示，建议填写）
    """
    category = "system"

    @classmethod
    def execute(cls, command: str, reason: str = "") -> str:
        if not command:
            return "错误：请提供命令"
        from src.system.privilege_manager import PrivilegeManager
        result = PrivilegeManager().execute_privileged(command, reason=reason)
        parts = [f"成功: {result.get('success', False)}",
                 f"消息: {result.get('message', '')}"]
        if result.get('output'):
            parts.append(f"输出:\n{result['output']}")
        if result.get('error'):
            parts.append(f"错误:\n{result['error']}")
        if 'returncode' in result:
            parts.append(f"返回码: {result['returncode']}")
        return "\n".join(parts)


class SearchTool(BaseTool):
    """搜索文件内容
    
    参数:
        query: 搜索关键词
        path: 搜索路径（默认当前目录）
    """
    
    @classmethod
    def execute(cls, query: str, path: str = None) -> str:
        import os
        
        if not query:
            return "错误：请提供搜索关键词"
        
        search_path = path or os.getcwd()
        results = []
        
        try:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if query.lower() in content.lower():
                                    results.append(file_path)
                        except Exception as e:
                            logger.debug(f"跳过无法读取的文件: {file_path}")
            
            if results:
                return "\n".join(results)
            else:
                return "未找到匹配的文件"
        except Exception as e:
            return f"搜索失败: {str(e)}"


class PythonExecutorTool(BaseTool):
    """执行 Python 代码
    
    参数:
        code: 要执行的 Python 代码
        timeout: 执行超时时间（默认30秒）
    """
    
    @classmethod
    def execute(cls, code: str, timeout: int = 30) -> str:
        if not code:
            return "错误：请提供要执行的 Python 代码"
        
        try:
            import subprocess
            import sys
            
            # 使用 subprocess 执行 Python 代码，避免安全风险
            result = subprocess.run(
                [sys.executable, '-c', code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n\n"
            output += f"返回码: {result.returncode}"
            
            return output
        except subprocess.TimeoutExpired:
            return f"执行超时（{timeout}秒）"
        except Exception as e:
            return f"执行失败: {str(e)}"


class PythonEvalTool(BaseTool):
    """计算 Python 表达式
    
    参数:
        expression: 要计算的 Python 表达式
    """
    
    @classmethod
    def execute(cls, expression: str) -> str:
        if not expression:
            return "错误：请提供要计算的表达式"
        
        try:
            # 使用 eval 计算表达式（限制在安全范围内）
            result = eval(expression, {}, {})
            return f"结果: {result}"
        except Exception as e:
            return f"计算失败: {str(e)}"


class CMDTool(BaseTool):
    """执行 CMD/Shell 命令
    
    参数:
        command: 要执行的命令
        cwd: 工作目录（可选）
        timeout: 超时时间（默认60秒）
    """
    
    @classmethod
    def execute(cls, command: str, cwd: str = None, timeout: int = 60) -> str:
        import subprocess
        
        if not command:
            return "错误：请提供命令"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n\n"
            output += f"返回码: {result.returncode}"
            
            return output
        except subprocess.TimeoutExpired:
            return f"命令执行超时（{timeout}秒）"
        except Exception as e:
            return f"执行失败: {str(e)}"


class PipTool(BaseTool):
    """Python 包管理工具
    
    参数:
        action: 操作（install, uninstall, list, show, search）
        package: 包名（install/uninstall/show/search时需要）
        options: 额外选项（如 -i 镜像地址）
    """
    
    @classmethod
    def execute(cls, action: str, package: str = None, options: str = "") -> str:
        import subprocess
        import sys
        
        actions = ['install', 'uninstall', 'list', 'show', 'search']
        
        if action not in actions:
            return f"错误：不支持的操作。支持的操作: {', '.join(actions)}"
        
        try:
            cmd = [sys.executable, '-m', 'pip', action]
            
            if action in ['install', 'uninstall', 'show', 'search'] and package:
                cmd.append(package)
            
            if options:
                cmd.extend(options.split())
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n\n"
            output += f"返回码: {result.returncode}"
            
            return output
        except subprocess.TimeoutExpired:
            return "命令执行超时（120秒）"
        except Exception as e:
            return f"执行失败: {str(e)}"


class PythonHelpTool(BaseTool):
    """获取 Python 模块/函数帮助
    
    参数:
        module: 模块名或函数名
    """
    
    @classmethod
    def execute(cls, module: str) -> str:
        if not module:
            return "错误：请提供模块名或函数名"
        
        try:
            import importlib
            import io
            import pydoc
            
            # 尝试导入模块
            try:
                obj = importlib.import_module(module)
            except ImportError:
                # 尝试作为对象查找
                parts = module.split('.')
                obj = __import__(parts[0])
                for part in parts[1:]:
                    obj = getattr(obj, part)
            
            # 获取帮助文档
            buffer = io.StringIO()
            pydoc.doc(obj, output=buffer)
            help_text = buffer.getvalue()
            
            # 限制长度
            if len(help_text) > 2000:
                help_text = help_text[:2000] + "\n\n（帮助文档过长，已截断）"
            
            return help_text
        except Exception as e:
            return f"获取帮助失败：{str(e)}"


class LibraryListTool(BaseTool):
    """列出项目已安装的库"""
    
    @classmethod
    def execute(cls, category: str = "all") -> str:
        try:
            tool = PythonLibraryTool()
            libs = tool.get_project_libraries()
            
            result = []
            for name, info in libs.items():
                if info["status"] == "installed":
                    result.append(f"✅ {name} v{info['version']} - {info['description']}")
            return "\n".join(result)
        except Exception as e:
            return f"获取库列表失败：{str(e)}"


class LibraryCallTool(BaseTool):
    """调用已安装库的函数
    
    参数:
        library: 库名
        function: 函数名
        args_json: 位置参数 JSON 数组
        kwargs_json: 关键字参数 JSON 对象
    """
    
    @classmethod
    def execute(cls, library: str, function: str, args_json: str = "[]", kwargs_json: str = "{}") -> str:
        import json
        
        try:
            args = json.loads(args_json)
            kwargs = json.loads(kwargs_json)
            
            tool = PythonLibraryTool()
            result = tool.call_library_function(library, function, args, kwargs)
            return result
        except json.JSONDecodeError as e:
            return f"JSON 解析失败：{str(e)}"
        except Exception as e:
            return f"调用失败：{str(e)}"


class LibraryExecuteTool(BaseTool):
    """使用指定库执行 Python 代码
    
    参数:
        code: Python 代码
        libraries: 需要导入的库列表（JSON 数组）
        timeout: 超时时间（秒）
    """
    
    @classmethod
    def execute(cls, code: str, libraries: str = "[]", timeout: int = 30) -> str:
        import json
        
        try:
            libs = json.loads(libraries)
            tool = PythonLibraryTool()
            result = tool.execute_with_library(code, libs, timeout)
            return result
        except json.JSONDecodeError as e:
            return f"JSON 解析失败：{str(e)}"
        except Exception as e:
            return f"执行失败：{str(e)}"


# ============ 示例用法 ============
if __name__ == "__main__":
    agent = AIAgent()
    
    # 获取工具描述
    print("=== 可用工具 ===")
    print(agent.get_tool_descriptions("markdown"))
    
    # 调用工具
    print("\n=== 调用系统信息工具 ===")
    result = agent.call_tool("SystemInfoTool")
    print(json.dumps(result, indent=2, ensure_ascii=False))