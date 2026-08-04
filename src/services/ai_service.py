from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Generator, Tuple, Optional, Dict, Any, List
import os
import sys
import json
import time
import requests
from src.config import settings
from src.config.ai_providers import AIProvider
from src.system.controller import SystemController, PermissionLevel
from src.services.local_model_service import LocalModelService
from src.services.tool_registry import tool_registry
_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
_REASONING_COLOR = "\033[90m" if _USE_COLOR else ""
_RESET_COLOR = "\033[0m" if _USE_COLOR else ""

def _get_tool_prompt() -> str:
    """动态生成工具提示词"""
    return tool_registry.generate_prompt()

_SYSTEM_PROMPT = """

## 语言要求
- 默认使用中文输出，除非用户明确指定其他语言
- 保持回答简洁、清晰、友好
你是一个AI电脑控制助手，可以通过执行系统命令来控制用户的电脑。
## 核心能力
### 🧠 任务分解能力
你具有强大的任务分解能力。当收到复杂任务时，请：
1. **分析任务**：理解用户的目标和需求
2. **分解步骤**：将复杂任务拆分成多个简单的子任务
3. **制定计划**：按照逻辑顺序安排执行步骤
4. **执行操作**：逐步执行每个子任务
5. **检查结果**：验证每步执行结果，必要时调整计划
### 🎯 可用控制功能（MCP - Model Context Protocol）
**鼠标控制**：
- mouse_move(x, y, duration): 移动鼠标到指定坐标
- mouse_click(x, y, button): 点击鼠标，button可选值: left, right, middle
- mouse_drag(start_x, start_y, end_x, end_y, duration): 拖拽鼠标
- mouse_scroll(clicks): 鼠标滚轮滚动
**键盘控制**：
- keyboard_type(text, interval): 输入文本
- keyboard_press(key): 按单个按键
- keyboard_hotkey(key1, key2, ...): 组合键操作
**命令执行**：
- execute_command(command, timeout): 执行系统命令，返回输出结果
- browser_request(url, method, headers, params, data): 发起HTTP请求
**屏幕识别（重要！）**：
- capture_and_analyze(region, ascii_width): 截取屏幕并进行完整分析，包含ASCII艺术、像素矩阵和统计信息
- capture_ascii(region, width): 截取屏幕并转换为ASCII字符画
- capture_pixel_matrix(region, sample_size): 截取屏幕并生成像素矩阵描述
**YOLO对象检测（重要！）**：
- yolo_detect(region, conf): 使用YOLO检测屏幕上所有对象，返回类别、位置、置信度
- yolo_find(class_name, conf, region): 查找特定对象，返回位置和置信度
- yolo_load_model(model_name): 加载YOLO模型，默认yolov8n.pt

**视频分析（Video2Text）**：
- analyze_video(video_path, frame_interval): 分析视频文件，识别对象并生成描述
- analyze_camera(duration): 分析摄像头实时画面，持续指定秒数

**YOLO实时摄像头理解**：
- yolo_camera_stream(camera_id, conf): 启动摄像头实时检测，显示带标注的视频窗口，按Q退出
- yolo_stop_camera(): 停止摄像头实时检测
- yolo_camera_realtime(duration, conf): 分析摄像头实时画面，返回检测摘要

**系统信息**：
- get_system_info(): 获取系统信息（屏幕尺寸、鼠标位置、权限级别）
### 屏幕识别说明
当需要了解屏幕内容时，请先使用 `capture_and_analyze` 截取分析屏幕，返回结果包含：
1. **图片统计信息**：尺寸、平均颜色、主色调、亮度、对比度
2. **ASCII字符画**：将屏幕转换为ASCII字符图形
3. **像素矩阵**：用不同密度的方块表示屏幕内容，配合RGB采样点
当需要精确识别屏幕上的对象（如按钮、图标、窗口等）时，使用 `yolo_detect` 进行对象检测，它会返回：
- 检测到的所有对象类别
- 每个对象的位置（边界框和中心点）
- 识别置信度
**YOLO可识别对象类别包括**：
person, bicycle, car, motorcycle, airplane, bus, train, truck, boat, traffic light, fire hydrant, stop sign, parking meter, bench, bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe, backpack, umbrella, handbag, tie, suitcase, frisbee, skis, snowboard, sports ball, kite, baseball bat, baseball glove, skateboard, surfboard, tennis racket, bottle, wine glass, cup, fork, knife, spoon, bowl, banana, apple, sandwich, orange, broccoli, carrot, hot dog, pizza, donut, cake, chair, couch, potted plant, bed, dining table, toilet, tv, laptop, mouse, remote, keyboard, cell phone, microwave, oven, toaster, sink, refrigerator, book, clock, vase, scissors, teddy bear, hair drier, toothbrush
### 使用方式
在你的响应中，使用<control>标签包裹JSON格式的命令。例如：
<control>{"type": "mouse_move", "x": 100, "y": 200}</control>
<control>{"type": "capture_and_analyze", "ascii_width": 60}</control>
<control>{"type": "yolo_detect", "conf": 0.5}</control>
<control>{"type": "yolo_find", "class_name": "person"}</control>
<control>{"type": "analyze_video", "video_path": "video.mp4", "frame_interval": 10}</control>
<control>{"type": "analyze_camera", "duration": 5}</control>
<control>{"type": "yolo_camera_stream", "camera_id": 0, "conf": 0.5}</control>
<control>{"type": "yolo_camera_realtime", "duration": 10, "conf": 0.5}</control>

### 可用的按键名称
基本键: a, b, c, ..., z, 0-9
功能键: f1, f2, ..., f12
方向键: up, down, left, right
特殊键: enter, tab, space, backspace, delete, esc
修饰键: shift, ctrl, alt, win
### 任务执行策略
1. **复杂任务分解**：将大任务分解为多个小步骤
2. **逐步执行**：一次执行一个或少量相关操作
3. **验证结果**：每步执行后检查结果
4. **自动轮回**：执行结果会自动返回给你，你可以继续下一步
5. **错误处理**：如果失败，分析原因并尝试其他方法
### 权限说明
- 权限级别决定了你可以执行哪些操作
- 如果没有足够权限，操作会被拒绝
- 可以使用 get_system_info() 查看当前权限
### 注意事项
- 执行操作前请确认坐标在屏幕范围内
- 组合键使用数组格式：{"type": "keyboard_hotkey", "keys": ["ctrl", "c"]}
- 执行命令后，系统会自动将结果返回给你，你可以根据结果继续执行
- 需要了解屏幕内容时，优先使用 capture_and_analyze 获取完整分析
请用中文回复，先描述你的计划，然后使用<control>标签执行操作。
"""
class AIService:
    def __init__(self, provider: Optional[AIProvider] = None):
        self.client = None
        self.current_provider = provider
        self.system_controller = SystemController()
        self.conversation_history = []
        self.max_history_length = 20
        if provider:
            self._initialize_client(provider)
    
    def _initialize_client(self, provider: Optional[AIProvider] = None):
        if provider:
            self.current_provider = provider
        
        if not self.current_provider:
            raise ValueError("No AI provider configured")
        
        api_key = self.current_provider.api_key
        base_url = self.current_provider.base_url
        
        # Handle Local provider
        if self.is_local_provider():
            self.local_model_service = LocalModelService()
            self.client = None
            return
        
        # Handle Ollama provider - use native Ollama API
        if self.is_ollama_provider():
            self.ollama_base_url = base_url.rstrip("/")
            self.client = None  # Ollama uses native API, not OpenAI client
            return
        
        if not base_url:
            raise ValueError("Base URL is not set for the selected provider")
        
        if not api_key:
            raise ValueError("API key is not set for the selected provider")
        
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
    
    def set_provider(self, provider: Optional[AIProvider] = None, **kwargs):
        if provider:
            self.current_provider = provider
        elif kwargs:
            self.current_provider = AIProvider(
                name=kwargs.get('provider_name', kwargs.get('name', 'Custom')),
                base_url=kwargs.get('base_url', ''),
                api_key=kwargs.get('api_key', ''),
                default_model=kwargs.get('model', kwargs.get('default_model', ''))
            )
        self.client = None

    def set_local_model_service(self, service):
        """设置本地模型服务实例（用于共享UI中已加载的模型）"""
        self.local_model_service = service

    def get_current_provider(self) -> Optional[AIProvider]:
        return self.current_provider
    
    def generate_title(self, prompt: str) -> str:
        # Initialize client for all providers
        if not self.client and not hasattr(self, 'ollama_base_url') and not hasattr(self, 'local_model_service'):
            self._initialize_client()
        
        if not self.current_provider:
            raise ValueError("No AI provider configured")
        
        # Handle local model
        if self.is_local_provider():
            if not hasattr(self, 'local_model_service'):
                self.local_model_service = LocalModelService()
            
            model_name = self.current_provider.default_model or "Qwen-0.5B"
            response = self.local_model_service.chat(prompt, max_new_tokens=50)
            return response.strip()
        
        # Handle Ollama with native API
        if self.is_ollama_provider():
            import json
            
            model_name = self.current_provider.default_model
            if not model_name:
                raise ValueError("No model selected for Ollama provider")
            
            try:
                response = requests.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "max_tokens": 50
                    },
                    timeout=60
                )
                
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama API error: HTTP {response.status_code}")
                
                data = response.json()
                if 'response' in data:
                    return data['response'].strip()
                raise RuntimeError("Ollama response missing 'response' field")
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"Ollama request failed: {e}")
            except json.JSONDecodeError:
                raise RuntimeError("Invalid JSON response from Ollama")
            except Exception as e:
                raise RuntimeError(f"Failed to generate title with Ollama: {str(e)}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.current_provider.default_model or settings.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to generate title: {str(e)}")
    
    def is_ollama_provider(self) -> bool:
        if not self.current_provider:
            return False
        base_url = self.current_provider.base_url.lower() if self.current_provider.base_url else ""
        return "ollama" in self.current_provider.name.lower() or ":11434" in base_url
    
    def is_local_provider(self) -> bool:
        if not self.current_provider:
            return False
        return self.current_provider.name.lower() == "local" or                (self.current_provider.base_url and self.current_provider.base_url.lower() == "local")
    
    def list_ollama_models(self) -> List[str]:
        if not self.current_provider:
            return []
        
        try:
            base_url = self.current_provider.base_url.rstrip("/")
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            
            if response.status_code != 200:
                raise RuntimeError(f"Failed to fetch Ollama models: HTTP {response.status_code}")
            data = response.json()
            
            # Ollama API returns {"models": [{"name": "...", ...}, ...]}
            if isinstance(data, dict) and "models" in data and isinstance(data["models"], list):
                models = []
                for item in data["models"]:
                    if isinstance(item, dict):
                        if "name" in item:
                            models.append(str(item["name"]))
                        elif "model" in item:
                            models.append(str(item["model"]))
                return models
            # Fallback for other formats
            if isinstance(data, dict):
                if "names" in data and isinstance(data["names"], list):
                    return [str(name) for name in data["names"]]
                if "tags" in data and isinstance(data["tags"], list):
                    return [str(tag) for tag in data["tags"]]
                return [str(value) for value in data.values() if isinstance(value, (str, int, float))]
            if isinstance(data, list):
                models = []
                for item in data:
                    if isinstance(item, dict):
                        if "name" in item:
                            models.append(str(item["name"]))
                        elif "model" in item:
                            models.append(str(item["model"]))
                        else:
                            models.append(json.dumps(item, ensure_ascii=False))
                    else:
                        models.append(str(item))
                return models
            return []
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Unable to reach Ollama service: {e}")
        except ValueError as e:
            raise RuntimeError(f"Invalid JSON response from Ollama service: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during Ollama request: {e}")
    
    def chat_completion_stream(self, messages: List[Dict[str, str]]) -> Generator[Tuple[str, str], None, None]:
        # Initialize client for all providers
        if not self.client and not hasattr(self, 'ollama_base_url') and not hasattr(self, 'local_model_service'):
            self._initialize_client()
        
        if not self.current_provider:
            raise ValueError("No AI provider configured")
        
        # Handle local model
        if self.is_local_provider():
            if not hasattr(self, 'local_model_service'):
                self.local_model_service = LocalModelService()
            
            model_name = self.current_provider.default_model or "Qwen-0.5B"
            
            # Extract user message content
            user_message = ""
            for msg in messages:
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
            
            for chunk in self.local_model_service.chat_stream(user_message):
                yield "", chunk
            return
        
        # Handle Ollama with native API
        if self.is_ollama_provider():
            import json
            
            model_name = self.current_provider.default_model
            if not model_name:
                raise ValueError("No model selected for Ollama provider")
            
            # Extract user message content
            user_message = ""
            for msg in messages:
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
            
            try:
                response = requests.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": user_message,
                        "stream": True,
                        "options": {
                            "temperature": 0.7,
                            "max_tokens": 2048
                        }
                    },
                    stream=True,
                    timeout=120
                )
                
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama API error: HTTP {response.status_code}")
                
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'response' in data:
                                yield "", data['response']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"Ollama request failed: {e}")
            except Exception as e:
                raise RuntimeError(f"Failed Ollama chat completion: {e}")
            return
        
        try:
            # Try streaming first
            stream = self.client.chat.completions.create(
                model=self.current_provider.default_model or settings.model_name,
                messages=messages,
                temperature=0.7,
                stream=True
            )
            
            for chunk in stream:
                if not hasattr(chunk, "choices") or not chunk.choices:
                    continue
                choice = chunk.choices[0]
                reasoning_content = ""
                content = ""
                
                if hasattr(choice, 'reasoning') and choice.reasoning:
                    reasoning_content = choice.reasoning
                if hasattr(choice, 'delta') and getattr(choice.delta, 'content', None):
                    content = choice.delta.content
                elif hasattr(choice, 'message') and getattr(choice.message, 'content', None):
                    content = choice.message.content
                
                if reasoning_content or content:
                    yield reasoning_content, content
        except Exception as e:
            # Fallback to non-streaming if streaming fails (e.g., 405 method not allowed)
            if "405" in str(e) or "method not allowed" in str(e).lower():
                try:
                    response = self.client.chat.completions.create(
                        model=self.current_provider.default_model or settings.model_name,
                        messages=messages,
                        temperature=0.7,
                        stream=False
                    )
                    if hasattr(response, 'choices') and response.choices:
                        choice = response.choices[0]
                        if hasattr(choice, 'message') and getattr(choice.message, 'content', None):
                            yield "", choice.message.content
                except Exception as fallback_e:
                    raise RuntimeError(f"Failed chat completion (both streaming and non-streaming): {fallback_e}")
            else:
                raise RuntimeError(f"Failed streaming chat completion: {e}")
    
    def format_reasoning(self, reasoning: str) -> str:
        if not reasoning:
            return ""
        return f"{_REASONING_COLOR}{reasoning}{_RESET_COLOR}"
    
    def stream_chat(self, message: str, include_system_prompt: bool = False) -> Generator[Dict[str, str], None, None]:
        messages = []
        
        if include_system_prompt:
            messages.append({"role": "system", "content": _SYSTEM_PROMPT})
        
        messages.extend(self.conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        # Debug 模式：打印用户消息
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            print("\n" + "="*80)
            print(f"\033[92m[DEBUG] 👤 用户消息:\033[0m")
            print(f"\033[92m{message}\033[0m")
            print("="*80)
        
        full_response = ""
        for reasoning_content, content in self.chat_completion_stream(messages):
            result = {}
            if reasoning_content:
                result["reasoning_content"] = reasoning_content
                # Debug 模式：打印推理内容
                if os.getenv("DEBUG_MODE", "false").lower() == "true":
                    print(f"\033[90m[DEBUG] 🧠 AI 推理：{reasoning_content}\033[0m")
            if content:
                result["content"] = content
                full_response += content
                # Debug 模式：实时打印 AI 回答
                if os.getenv("DEBUG_MODE", "false").lower() == "true":
                    print(f"\033[94m[DEBUG] 🤖 AI: {content}\033[0m", end="", flush=True)
            if result:
                yield result
        
        # Debug 模式：打印完整回答
        if os.getenv("DEBUG_MODE", "false").lower() == "true" and full_response:
            print("\n\033[90m[DEBUG] ✅ AI 完整回答已接收\033[0m")
            print("="*80 + "\n")
        
        if full_response:
            self._add_to_history({"role": "user", "content": message})
            self._add_to_history({"role": "assistant", "content": full_response})
    
    def _add_to_history(self, message: Dict[str, str]):
        self.conversation_history.append(message)
        
        while len(self.conversation_history) > self.max_history_length:
            self.conversation_history.pop(0)
    
    def clear_history(self):
        self.conversation_history = []
    
    def get_history_length(self) -> int:
        return len(self.conversation_history)
    
    def set_max_history_length(self, length: int):
        self.max_history_length = length
        while len(self.conversation_history) > self.max_history_length:
            self.conversation_history.pop(0)
    
    def get_color_codes(self) -> Dict[str, str]:
        return {
            "reasoning": _REASONING_COLOR,
            "reset": _RESET_COLOR,
            "use_color": _USE_COLOR
        }
    
    def set_permission_level(self, level: str):
        permission_map = {
            "none": PermissionLevel.NONE,
            "view": PermissionLevel.VIEW,
            "limited": PermissionLevel.LIMITED,
            "full": PermissionLevel.FULL,
            "无": PermissionLevel.NONE,
            "查看": PermissionLevel.VIEW,
            "受限": PermissionLevel.LIMITED,
            "完整": PermissionLevel.FULL
        }
        level_enum = permission_map.get(level.lower(), PermissionLevel.NONE)
        self.system_controller.set_permission_level(level_enum)
    
    def parse_and_execute_commands(self, response_text: str) -> Dict[str, Any]:
        control_marker_start = "<control>"
        control_marker_end = "</control>"
        
        if control_marker_start not in response_text:
            return {"has_commands": False, "results": [], "summary": ""}
        
        results = []
        executed_commands = []
        
        start_idx = 0
        while True:
            start_pos = response_text.find(control_marker_start, start_idx)
            if start_pos == -1:
                break
            
            end_pos = response_text.find(control_marker_end, start_pos)
            if end_pos == -1:
                break
            
            command_json = response_text[start_pos + len(control_marker_start):end_pos].strip()
            
            try:
                command = json.loads(command_json)
                
                op_type = command.get("type", "")
                if op_type in ["keyboard_hotkey", "keyboard_press"]:
                    time.sleep(1.0)
                elif op_type == "keyboard_type":
                    text_length = len(command.get("text", ""))
                    estimated_time = max(0.5, text_length * 0.05)
                    time.sleep(estimated_time)
                elif op_type in ["execute_command", "browser_request"]:
                    time.sleep(0.5)
                
                result = self.system_controller.execute_operation(command)
                executed_commands.append(command)
                
                if result["success"]:
                    results.append({
                        "success": True,
                        "operation": result.get("operation", op_type),
                        "message": result.get("message", ""),
                        "data": result.get("data", {})
                    })
                else:
                    results.append({
                        "success": False,
                        "operation": result.get("operation", op_type),
                        "message": result.get("message", "Unknown error"),
                        "data": result.get("data", {})
                    })
            
            except json.JSONDecodeError:
                results.append({
                    "success": False,
                    "operation": "parse_error",
                    "message": f"命令格式错误: {command_json[:50]}..."
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "operation": "execution_error",
                    "message": f"执行错误: {str(e)}"
                })
            
            start_idx = end_pos + len(control_marker_end)
        
        success_count = sum(1 for r in results if r["success"])
        summary = f"执行了 {len(results)} 个命令，成功 {success_count} 个，失败 {len(results) - success_count} 个"
        
        return {
            "has_commands": True,
            "results": results,
            "executed_commands": executed_commands,
            "summary": summary
        }
    
    def format_command_results(self, command_results: Dict[str, Any]) -> str:
        if not command_results.get("has_commands"):
            return ""
        
        lines = []
        for result in command_results["results"]:
            if result["success"]:
                lines.append(f"✓ 执行成功: {result['operation']}")
                if result.get("data"):
                    data_str = json.dumps(result["data"], ensure_ascii=False, indent=2)
                    if len(data_str) > 200:
                        data_str = data_str[:200] + "..."
                    lines.append(f"  结果: {data_str}")
            else:
                lines.append(f"✗ 执行失败: {result['operation']} - {result['message']}")
        
        lines.append(f"\n{command_results['summary']}")
        return "\n".join(lines)
    
    def stream_chat_with_control(self, message: str, enable_loop: bool = False, max_loops: int = 5) -> Generator[Dict[str, str], None, None]:
        current_message = message
        loop_count = 0
        
        # Debug 模式：打印循环信息
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            print(f"\n\033[93m[DEBUG] 🔄 开始对话循环，最大循环次数：{max_loops}\033[0m")
        
        while True:
            full_response = ""
            
            # Debug 模式：打印当前循环次数
            if os.getenv("DEBUG_MODE", "false").lower() == "true":
                print(f"\n\033[93m[DEBUG] 📍 第 {loop_count + 1} 轮对话\033[0m")
            
            for chunk in self.stream_chat(current_message, include_system_prompt=True):
                if "content" in chunk:
                    full_response += chunk["content"]
                yield chunk
            
            # Debug 模式：打印命令解析信息
            if os.getenv("DEBUG_MODE", "false").lower() == "true":
                print(f"\n\033[93m[DEBUG] 🔍 解析并执行命令...\033[0m")
            
            command_results = self.parse_and_execute_commands(full_response)
            result_text = self.format_command_results(command_results)
            
            if result_text:
                # Debug 模式：打印命令执行结果
                if os.getenv("DEBUG_MODE", "false").lower() == "true":
                    print(f"\n\033[93m[DEBUG] 📋 命令执行结果:\033[0m")
                    print(f"\033[93m{result_text}\033[0m\n")
                
                yield {"content": "\n" + result_text}
                
                self._add_to_history({"role": "assistant", "content": full_response})
                self._add_to_history({"role": "system", "content": f"命令执行结果:\n{result_text}"})
            
            if not enable_loop or loop_count >= max_loops:
                # Debug 模式：打印循环结束信息
                if os.getenv("DEBUG_MODE", "false").lower() == "true":
                    if loop_count >= max_loops:
                        print(f"\n\033[93m[DEBUG] ⚠️ 已达到最大循环次数 {max_loops}，停止\033[0m")
                    else:
                        print(f"\n\033[93m[DEBUG] ✅ 对话循环结束\033[0m")
                break
            
            if command_results.get("has_commands"):
                failed_count = sum(1 for r in command_results["results"] if not r["success"])
                if failed_count > 0:
                    current_message = f"以下命令执行失败，请分析原因并尝试解决：\n{result_text}"
                    # Debug 模式：打印重试信息
                    if os.getenv("DEBUG_MODE", "false").lower() == "true":
                        print(f"\n\033[93m[DEBUG] ⚠️ 有 {failed_count} 个命令失败，准备重试...\033[0m")
                else:
                    break
            else:
                break
            
            loop_count += 1
            