"""
工具注册表 - ToolRegistry
单例模式管理所有 AI 可用的工具
"""

import json
from typing import List, Dict, Any, Callable, Optional


class ToolRegistry:
    """工具注册表（单例模式）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}  # name -> tool_info
            cls._instance._functions = {}  # name -> callable
            cls._instance._categories = {}  # category -> [names]
        return cls._instance
    
    def register_tool(self, func: Callable, name: str = None, description: str = "",
                      params: List[Dict] = None, category: str = "general"):
        """注册工具"""
        tool_name = name or func.__name__
        
        # 从函数签名提取参数信息
        import inspect
        sig = inspect.signature(func)
        parameters = params or []
        
        if not params:
            for param_name, param in sig.parameters.items():
                if param_name == 'self' or param_name == 'cls':
                    continue
                param_type = param.annotation.__name__ if param.annotation != inspect.Parameter.empty else 'str'
                required = param.default == inspect.Parameter.empty
                parameters.append({
                    "name": param_name,
                    "type": param_type,
                    "required": required,
                    "description": ""
                })
        
        self._tools[tool_name] = {
            "name": tool_name,
            "description": description or func.__doc__ or "",
            "parameters": parameters,
            "category": category
        }
        self._functions[tool_name] = func
        
        if category not in self._categories:
            self._categories[category] = []
        if tool_name not in self._categories[category]:
            self._categories[category].append(tool_name)
    
    def get_tool(self, name: str) -> Optional[Dict]:
        """获取工具定义"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[Dict]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_tools_by_category(self, category: str) -> List[Dict]:
        """按类别获取工具"""
        if category not in self._categories:
            return []
        return [self._tools[name] for name in self._categories[category]]
    
    def call_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """调用工具"""
        if name not in self._functions:
            return {"success": False, "error": f"工具不存在: {name}"}
        
        func = self._functions[name]
        tool_info = self._tools[name]
        
        # 检查必填参数
        for param in tool_info["parameters"]:
            if param.get("required", True) and param["name"] not in kwargs:
                return {"success": False, "error": f"缺少必填参数: {param['name']}"}
        
        try:
            result = func(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_prompt(self, format: str = "json") -> str:
        """生成工具提示词"""
        tools_info = []
        for name, tool_info in self._tools.items():
            tools_info.append({
                "name": name,
                "description": tool_info["description"],
                "parameters": tool_info["parameters"],
                "category": tool_info["category"]
            })
        
        if format == "json":
            return json.dumps({
                "role": "system",
                "content": f"你是一个AI助手，可以使用以下工具完成任务。\n工具列表:\n{json.dumps(tools_info, indent=2, ensure_ascii=False)}\n调用格式: {{\"tool\": \"工具名\", \"args\": {{\"参数\": \"值\"}}}}"
            }, ensure_ascii=False)
        else:
            prompt = "你是一个AI助手，可以使用以下工具：\n\n"
            for category, names in self._categories.items():
                prompt += f"【{category}】\n"
                for name in names:
                    tool = self._tools[name]
                    prompt += f"- {name}: {tool['description']}\n"
                    if tool['parameters']:
                        prompt += f"  参数: {', '.join(p['name'] for p in tool['parameters'])}\n"
                prompt += "\n"
            return prompt


# 全局工具注册表实例
tool_registry = ToolRegistry()


def tool(name: str = None, description: str = "", category: str = "general"):
    """装饰器：注册工具"""
    def decorator(func):
        tool_registry.register_tool(func, name, description, category=category)
        return func
    return decorator