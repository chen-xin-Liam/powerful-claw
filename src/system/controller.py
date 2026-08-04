# -*- coding: utf-8 -*-
import pyautogui
import pyperclip
import keyboard
import subprocess
import requests
import time
import json
from PIL import ImageGrab
from typing import Optional, Tuple, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

from src.utils.image_processor import ImageProcessor
from src.utils.yolo_detector import YOLODetector
from src.utils.video_analyzer import VideoAnalyzer

class PermissionLevel(Enum):
    NONE = "none"
    VIEW = "view"
    LIMITED = "limited"
    FULL = "full"

@dataclass
class OperationPermission:
    mouse_move: bool = False
    mouse_click: bool = False
    mouse_drag: bool = False
    keyboard_input: bool = False
    keyboard_hotkey: bool = False
    execute_command: bool = False
    browser_access: bool = False
    screen_capture: bool = False
    window_control: bool = False
    system_control: bool = False

class SystemController:
    def __init__(self):
        self.permissions = OperationPermission()
        self.set_permission_level(PermissionLevel.NONE)
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.3
        self.image_processor = ImageProcessor()
        self._yolo_detector = None
        self._video_analyzer = None
    
    @property
    def yolo_detector(self):
        if self._yolo_detector is None:
            self._yolo_detector = YOLODetector()
        return self._yolo_detector
    
    @property
    def video_analyzer(self):
        if self._video_analyzer is None:
            self._video_analyzer = VideoAnalyzer()
        return self._video_analyzer

    def set_permission_level(self, level: PermissionLevel):
        if level == PermissionLevel.NONE:
            self.permissions = OperationPermission()
        elif level == PermissionLevel.VIEW:
            self.permissions = OperationPermission(
                mouse_move=False,
                mouse_click=False,
                mouse_drag=False,
                keyboard_input=False,
                keyboard_hotkey=False,
                execute_command=False,
                browser_access=False,
                screen_capture=True,
                window_control=False,
                system_control=False
            )
        elif level == PermissionLevel.LIMITED:
            self.permissions = OperationPermission(
                mouse_move=True,
                mouse_click=True,
                mouse_drag=False,
                keyboard_input=True,
                keyboard_hotkey=True,
                execute_command=False,
                browser_access=False,
                screen_capture=True,
                window_control=False,
                system_control=False
            )
        elif level == PermissionLevel.FULL:
            self.permissions = OperationPermission(
                mouse_move=True,
                mouse_click=True,
                mouse_drag=True,
                keyboard_input=True,
                keyboard_hotkey=True,
                execute_command=True,
                browser_access=True,
                screen_capture=True,
                window_control=True,
                system_control=True
            )

    def set_individual_permission(self, permission: str, value: bool):
        if hasattr(self.permissions, permission):
            setattr(self.permissions, permission, value)

    def mouse_move(self, x: int, y: int, duration: float = 0.3) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.mouse_move:
            result["message"] = "权限不足：鼠标移动"
            return result
        try:
            pyautogui.moveTo(x, y, duration=duration)
            result["success"] = True
            result["message"] = "鼠标移动成功"
            result["data"] = {"x": x, "y": y, "duration": duration}
            return result
        except Exception as e:
            result["message"] = f"鼠标移动失败: {str(e)}"
            return result

    def mouse_click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = 'left') -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.mouse_click:
            result["message"] = "权限不足：鼠标点击"
            return result
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
            else:
                pyautogui.click(button=button)
            result["success"] = True
            result["message"] = "鼠标点击成功"
            result["data"] = {"x": x, "y": y, "button": button}
            return result
        except Exception as e:
            result["message"] = f"鼠标点击失败: {str(e)}"
            return result

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.mouse_drag:
            result["message"] = "权限不足：鼠标拖拽"
            return result
        try:
            pyautogui.dragTo(end_x, end_y, duration=duration)
            result["success"] = True
            result["message"] = "鼠标拖拽成功"
            result["data"] = {"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y}
            return result
        except Exception as e:
            result["message"] = f"鼠标拖拽失败: {str(e)}"
            return result

    def mouse_scroll(self, clicks: int) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.mouse_click:
            result["message"] = "权限不足：鼠标滚动"
            return result
        try:
            pyautogui.scroll(clicks)
            result["success"] = True
            result["message"] = "鼠标滚动成功"
            result["data"] = {"clicks": clicks}
            return result
        except Exception as e:
            result["message"] = f"鼠标滚动失败: {str(e)}"
            return result

    def keyboard_type(self, text: str, interval: float = 0.05) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.keyboard_input:
            result["message"] = "权限不足：键盘输入"
            return result
        try:
            try:
                keyboard.write(text, delay=interval)
            except Exception:
                pyperclip.copy(text)
                keyboard.press_and_release('ctrl+v')
                time.sleep(0.3)
            result["success"] = True
            result["message"] = "文本输入成功"
            result["data"] = {"text": text, "length": len(text)}
            return result
        except Exception as e:
            result["message"] = f"键盘输入失败: {str(e)}"
            return result

    def keyboard_press(self, key: str) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.keyboard_hotkey:
            result["message"] = "权限不足：按键"
            return result
        try:
            keyboard.press_and_release(key)
            result["success"] = True
            result["message"] = f"按键成功: {key}"
            result["data"] = {"key": key}
            return result
        except Exception as e:
            result["message"] = f"按键失败: {str(e)}"
            return result

    def keyboard_hotkey(self, *keys: str) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.keyboard_hotkey:
            result["message"] = "权限不足：组合键"
            return result
        try:
            keyboard.press_and_release('+'.join(keys))
            result["success"] = True
            result["message"] = f"组合键成功: {'+'.join(keys)}"
            result["data"] = {"keys": list(keys)}
            return result
        except Exception as e:
            result["message"] = f"组合键失败: {str(e)}"
            return result

    def execute_command(self, cmd: str, timeout: int = 30) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.execute_command:
            result["message"] = "权限不足：执行命令"
            return result
        try:
            output = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            result["success"] = output.returncode == 0
            result["message"] = "命令执行成功" if result["success"] else "命令执行失败"
            result["data"] = {
                "command": cmd,
                "stdout": output.stdout,
                "stderr": output.stderr,
                "return_code": output.returncode
            }
            return result
        except subprocess.TimeoutExpired:
            result["message"] = "命令执行超时"
            result["data"] = {"command": cmd, "error": "timeout"}
            return result
        except Exception as e:
            result["message"] = f"命令执行异常: {str(e)}"
            result["data"] = {"command": cmd, "error": str(e)}
            return result

    def browser_request(self, url: str, method: str = "GET", headers: Dict = None,
                       params: Dict = None, data: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}
        if not self.permissions.browser_access:
            result["message"] = "权限不足：浏览器访问"
            return result
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers or {},
                params=params or {},
                data=data or {},
                timeout=timeout
            )
            result["success"] = response.status_code >= 200 and response.status_code < 300
            result["message"] = f"请求成功，状态码: {response.status_code}" if result["success"] else f"请求失败，状态码: {response.status_code}"
            result["data"] = {
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_length": len(response.content),
                "text": response.text[:2000] if len(response.text) > 2000 else response.text
            }
            return result
        except requests.RequestException as e:
            result["message"] = f"请求异常: {str(e)}"
            result["data"] = {"url": url, "error": str(e)}
            return result

    def get_screen_size(self) -> Tuple[int, int]:
        return pyautogui.size()

    def get_mouse_position(self) -> Tuple[int, int]:
        return pyautogui.position()

    def get_system_info(self) -> Dict[str, Any]:
        result = {}
        try:
            result["screen_size"] = self.get_screen_size()
            result["mouse_position"] = self.get_mouse_position()
            result["permissions"] = {k: v for k, v in vars(self.permissions).items() if not k.startswith('_')}
        except Exception as e:
            result["error"] = str(e)
        return result

    def capture_and_analyze_screen(self, region: Optional[Tuple[int, int, int, int]] = None,
                                   ascii_width: int = 60) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}

        if not self.permissions.screen_capture:
            result["message"] = "权限不足：屏幕截图"
            return result

        try:
            screenshot = ImageGrab.grab(bbox=region)

            width, height = screenshot.size
            analysis = self.image_processor.full_analysis(screenshot, ascii_width=ascii_width)

            result["success"] = True
            result["message"] = "屏幕截图分析完成"
            result["data"] = {
                "width": width,
                "height": height,
                "size": f"{width}x{height}",
                "analysis": analysis
            }

            return result
        except Exception as e:
            result["message"] = f"截图分析失败: {str(e)}"
            result["data"] = {"error": str(e)}
            return result

    def capture_ascii_art(self, region: Optional[Tuple[int, int, int, int]] = None,
                         width: int = 80) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}

        if not self.permissions.screen_capture:
            result["message"] = "权限不足：屏幕截图"
            return result

        try:
            screenshot = ImageGrab.grab(bbox=region)
            ascii_art = self.image_processor.image_to_ascii(screenshot, width=width)

            result["success"] = True
            result["message"] = "ASCII艺术生成完成"
            result["data"] = {
                "ascii_art": ascii_art,
                "width": width
            }

            return result
        except Exception as e:
            result["message"] = f"ASCII艺术生成失败: {str(e)}"
            result["data"] = {"error": str(e)}
            return result

    def capture_pixel_matrix(self, region: Optional[Tuple[int, int, int, int]] = None,
                             sample_size: int = 20) -> Dict[str, Any]:
        result = {"success": False, "message": "", "data": {}}

        if not self.permissions.screen_capture:
            result["message"] = "权限不足：屏幕截图"
            return result

        try:
            screenshot = ImageGrab.grab(bbox=region)
            pixel_matrix = self.image_processor.image_to_pixel_matrix(screenshot, sample_size=sample_size)

            result["success"] = True
            result["message"] = "像素矩阵生成完成"
            result["data"] = {
                "pixel_matrix": pixel_matrix,
                "sample_size": sample_size
            }

            return result
        except Exception as e:
            result["message"] = f"像素矩阵生成失败: {str(e)}"
            result["data"] = {"error": str(e)}
            return result

    def yolo_detect(self, region: Optional[Tuple[int, int, int, int]] = None, conf: float = 0.25) -> Dict[str, Any]:
        if not self.permissions.screen_capture:
            return {"success": False, "message": "权限不足：屏幕截图", "data": {}}

        try:
            screenshot = ImageGrab.grab(bbox=region)
            result = self.yolo_detector.detect_objects(screenshot, conf)
            result["formatted"] = self.yolo_detector.format_detection_for_ai(result)
            return result
        except Exception as e:
            return {"success": False, "message": f"YOLO检测失败: {str(e)}", "data": {"error": str(e)}}

    def yolo_find_object(self, class_name: str, conf: float = 0.25, region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        if not self.permissions.screen_capture:
            return {"success": False, "message": "权限不足：屏幕截图", "data": {}}

        if not class_name:
            return {"success": False, "message": "未指定要查找的对象名称", "data": {}}

        try:
            result = self.yolo_detector.find_object(class_name, conf, region)
            if result.get("success"):
                obj = result["data"]["object"]
                result["formatted"] = f"找到: {obj['class_name']} (置信度: {obj['confidence']:.2%})\n  位置: ({obj['center'][0]}, {obj['center'][1]})\n  边界框: {obj['bbox']}"
            return result
        except Exception as e:
            return {"success": False, "message": f"查找对象失败: {str(e)}", "data": {"error": str(e)}}

    def yolo_load_model(self, model_name: str = "yolov8n.pt") -> Dict[str, Any]:
        try:
            success = self.yolo_detector.load_model(model_name)
            if success:
                return {"success": True, "message": f"YOLO模型 '{model_name}' 加载成功", "data": {"model": model_name}}
            else:
                return {"success": False, "message": f"YOLO模型 '{model_name}' 加载失败", "data": {}}
        except Exception as e:
            return {"success": False, "message": f"加载YOLO模型失败: {str(e)}", "data": {"error": str(e)}}

    def analyze_video(self, video_path: str, frame_interval: int = 10) -> Dict[str, Any]:
        if not self.permissions.screen_capture:
            return {"success": False, "message": "权限不足：屏幕截图", "data": {}}

        try:
            result = self.video_analyzer.analyze_video_file(video_path, frame_interval)
            result["formatted"] = self.video_analyzer.format_result_for_ai(result)
            return result
        except Exception as e:
            return {"success": False, "message": f"视频分析失败: {str(e)}", "data": {"error": str(e)}}

    def analyze_camera(self, duration: int = 5) -> Dict[str, Any]:
        if not self.permissions.screen_capture:
            return {"success": False, "message": "权限不足：屏幕截图", "data": {}}

        try:
            result = self.video_analyzer.analyze_camera(duration)
            result["formatted"] = self.video_analyzer.format_result_for_ai(result)
            return result
        except Exception as e:
            return {"success": False, "message": f"摄像头分析失败: {str(e)}", "data": {"error": str(e)}}

    def execute_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "success": False,
            "operation": operation.get("type"),
            "message": "",
            "data": {}
        }

        op_type = operation.get("type")

        if op_type == "mouse_move":
            x = operation.get("x", 0)
            y = operation.get("y", 0)
            duration = operation.get("duration", 0.3)
            return self.mouse_move(x, y, duration)

        elif op_type == "mouse_click":
            x = operation.get("x")
            y = operation.get("y")
            button = operation.get("button", "left")
            return self.mouse_click(x, y, button)

        elif op_type == "mouse_drag":
            start_x = operation.get("start_x", 0)
            start_y = operation.get("start_y", 0)
            end_x = operation.get("end_x", 0)
            end_y = operation.get("end_y", 0)
            duration = operation.get("duration", 0.3)
            return self.mouse_drag(start_x, start_y, end_x, end_y, duration)

        elif op_type == "mouse_scroll":
            clicks = operation.get("clicks", 0)
            return self.mouse_scroll(clicks)

        elif op_type == "keyboard_type":
            text = operation.get("text", "")
            interval = operation.get("interval", 0.05)
            return self.keyboard_type(text, interval)

        elif op_type == "keyboard_press":
            key = operation.get("key", "")
            return self.keyboard_press(key)

        elif op_type == "keyboard_hotkey":
            keys = operation.get("keys", [])
            return self.keyboard_hotkey(*keys)

        elif op_type == "execute_command":
            cmd = operation.get("command", "")
            timeout = operation.get("timeout", 30)
            return self.execute_command(cmd, timeout)

        elif op_type == "browser_request":
            url = operation.get("url", "")
            method = operation.get("method", "GET")
            headers = operation.get("headers")
            params = operation.get("params")
            data = operation.get("data")
            timeout = operation.get("timeout", 30)
            return self.browser_request(url, method, headers, params, data, timeout)

        elif op_type == "get_system_info":
            result["success"] = True
            result["message"] = "获取系统信息成功"
            result["data"] = self.get_system_info()
            return result

        elif op_type == "capture_and_analyze":
            region = operation.get("region")
            ascii_width = operation.get("ascii_width", 60)
            return self.capture_and_analyze_screen(region, ascii_width)

        elif op_type == "capture_ascii":
            region = operation.get("region")
            width = operation.get("width", 80)
            return self.capture_ascii_art(region, width)

        elif op_type == "capture_pixel_matrix":
            region = operation.get("region")
            sample_size = operation.get("sample_size", 20)
            return self.capture_pixel_matrix(region, sample_size)

        elif op_type == "yolo_detect":
            region = operation.get("region")
            conf = operation.get("conf", 0.25)
            return self.yolo_detect(region, conf)

        elif op_type == "yolo_find":
            class_name = operation.get("class_name", "")
            conf = operation.get("conf", 0.25)
            region = operation.get("region")
            return self.yolo_find_object(class_name, conf, region)

        elif op_type == "yolo_load_model":
            model_name = operation.get("model_name", "yolov8n.pt")
            return self.yolo_load_model(model_name)

        elif op_type == "analyze_video":
            video_path = operation.get("video_path", "")
            frame_interval = operation.get("frame_interval", 10)
            return self.analyze_video(video_path, frame_interval)

        elif op_type == "analyze_camera":
            duration = operation.get("duration", 5)
            return self.analyze_camera(duration)

        elif op_type == "yolo_camera_stream":
            camera_id = operation.get("camera_id", 0)
            conf = operation.get("conf", 0.25)
            return self.yolo_detector.start_camera_stream(camera_id, conf)

        elif op_type == "yolo_stop_camera":
            return self.yolo_detector.stop_camera_stream()

        elif op_type == "yolo_camera_realtime":
            duration = operation.get("duration", 10)
            camera_id = operation.get("camera_id", 0)
            conf = operation.get("conf", 0.25)
            result_data = self.yolo_detector.analyze_camera_realtime(duration, camera_id, conf)
            if result_data.get("success") and "summary" in result_data.get("data", {}):
                result_data["formatted"] = result_data["data"]["summary"]
            return result_data

        else:
            result["message"] = f"未知操作类型: {op_type}"
            return result