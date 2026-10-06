# -*- coding: utf-8 -*-
import pyautogui
import pyperclip
import keyboard
import subprocess
import sys
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
from src.system.high_risk_detector import HighRiskDetector
from src.system.confirmation import ConfirmationManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

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
        # 高危操作二次授权
        self.high_risk_detector = HighRiskDetector()
        self.confirmation_manager: Optional[ConfirmationManager] = None
        self.high_risk_enabled: bool = True
    
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
                # LIMITED 仅允许文本输入；热键可触发系统级快捷操作
                # （Alt+F4/Win+R 等），故不予放行
                keyboard_hotkey=False,
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

    def set_confirmation_manager(self, mgr: ConfirmationManager) -> None:
        """注入确认管理器（由 AIService 在启动时注入，GUI/终端模式由启动方式决定）。"""
        self.confirmation_manager = mgr

    def set_high_risk_enabled(self, enabled: bool) -> None:
        """开关高危操作二次授权。"""
        self.high_risk_enabled = enabled

    def _check_high_risk(self, op_type: str, operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """高危检查：若操作高危且被拒绝，返回拒绝结果字典；否则返回 None（放行）。

        若二次授权总开关关闭（high_risk_enabled=False），高危操作直接拒绝（fail-safe）。
        若未注入 confirmation_manager，高危操作直接拒绝。
        """
        if not self.high_risk_enabled:
            # 总开关关闭：按 fail-safe 拒绝所有高危操作
            is_high, reason = self.high_risk_detector.is_high_risk_operation(op_type, operation)
            if is_high:
                logger.warning(f"高危操作被拒绝（二次授权已关闭）: {reason}")
                return {
                    "success": False,
                    "operation": op_type,
                    "message": "高危操作已被禁用（二次授权总开关关闭）",
                    "data": {"reason": reason, "denied": True, "high_risk_disabled": True},
                }
            return None

        if self.confirmation_manager is None:
            is_high, reason = self.high_risk_detector.is_high_risk_operation(op_type, operation)
            if is_high:
                logger.warning(f"高危操作被拒绝（未注入确认管理器）: {reason}")
                return {
                    "success": False,
                    "operation": op_type,
                    "message": "高危操作无法确认（确认管理器未初始化）",
                    "data": {"reason": reason, "denied": True},
                }
            return None

        is_high, reason = self.high_risk_detector.is_high_risk_operation(op_type, operation)
        if not is_high:
            return None

        # 高危：请求二次授权
        desc = (f"{reason}\n操作类型: {op_type}\n"
                f"内容: {json.dumps(operation, ensure_ascii=False)[:200]}")
        logger.info(f"高危操作触发二次授权: {reason}")
        approved = self.confirmation_manager.confirm(desc)
        if approved:
            logger.info("用户已授权高危操作，继续执行")
            return None
        logger.warning("用户拒绝高危操作")
        return {
            "success": False,
            "operation": op_type,
            "message": "用户未授权此高危操作（已拒绝）",
            "data": {"reason": reason, "denied": True},
        }

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
                # Linux 非 root 无 /dev/uinput：退到 X 层 pyautogui
                try:
                    pyautogui.typewrite(text, interval=interval)
                except Exception:
                    pyperclip.copy(text)
                    pyautogui.hotkey('ctrl', 'v')
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
            try:
                keyboard.press_and_release(key)
            except Exception:
                pyautogui.press(key)
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
            try:
                keyboard.press_and_release('+'.join(keys))
            except Exception:
                pyautogui.hotkey(*keys)
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
        # 高危操作二次授权检查（直接调用入口也受保护）
        denied = self._check_high_risk("execute_command", {"command": cmd})
        if denied is not None:
            return denied
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

    # ================= 窗口 / 系统 / 扩展操作 =================

    _WINDOW_HOTKEYS = {
        "win32": {"minimize": ("win", "down"), "maximize": ("win", "up"),
                  "restore": ("win", "up"), "close": ("alt", "f4")},
        "darwin": {"minimize": ("command", "m"),
                   "maximize": ("command", "ctrl", "f"),
                   "restore": ("command", "ctrl", "f"),
                   "close": ("command", "w")},
        "linux": {"minimize": ("super", "h"), "maximize": ("super", "up"),
                  "restore": ("super", "down"), "close": ("alt", "f4")},
    }

    _POWER_COMMANDS = {
        "win32": {
            "shutdown": ["shutdown", "/s", "/t", "0"],
            "restart": ["shutdown", "/r", "/t", "0"],
            "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
            "sleep": ["shutdown", "/h"],
        },
        "linux": {
            "shutdown": ["systemctl", "poweroff"],
            "restart": ["systemctl", "reboot"],
            "lock": ["loginctl", "lock-session"],
            "sleep": ["systemctl", "suspend"],
        },
        "darwin": {
            "shutdown": ["osascript", "-e",
                         'tell application "System Events" to shut down'],
            "restart": ["osascript", "-e",
                        'tell application "System Events" to restart'],
            "lock": ["osascript", "-e",
                     'tell application "System Events" to keystroke "q" '
                     'using {control down, command down}'],
            "sleep": ["pmset", "sleepnow"],
        },
    }

    def mouse_move_relative(self, dx: int, dy: int,
                            duration: float = 0.1) -> Dict[str, Any]:
        """相对当前位置移动鼠标。"""
        if not self.permissions.mouse_move:
            return {"success": False, "message": "权限不足：鼠标移动", "data": {}}
        try:
            pyautogui.moveRel(int(dx), int(dy), duration=float(duration))
            return {"success": True,
                    "message": f"鼠标相对移动 ({dx}, {dy})", "data": {}}
        except Exception as e:
            return {"success": False, "message": f"鼠标移动失败: {e}",
                    "data": {"error": str(e)}}

    def mouse_drag_start(self, button: str = "left") -> Dict[str, Any]:
        if not self.permissions.mouse_drag:
            return {"success": False, "message": "权限不足：鼠标拖拽", "data": {}}
        try:
            pyautogui.mouseDown(button=button)
            return {"success": True, "message": "拖拽开始", "data": {}}
        except Exception as e:
            return {"success": False, "message": f"拖拽开始失败: {e}",
                    "data": {"error": str(e)}}

    def mouse_drag_stop(self, button: str = "left") -> Dict[str, Any]:
        if not self.permissions.mouse_drag:
            return {"success": False, "message": "权限不足：鼠标拖拽", "data": {}}
        try:
            pyautogui.mouseUp(button=button)
            return {"success": True, "message": "拖拽结束", "data": {}}
        except Exception as e:
            return {"success": False, "message": f"拖拽结束失败: {e}",
                    "data": {"error": str(e)}}

    def _window_action(self, action: str) -> Dict[str, Any]:
        if not self.permissions.window_control:
            return {"success": False, "message": "权限不足：窗口控制", "data": {}}
        try:
            keys = self._WINDOW_HOTKEYS.get(
                sys.platform, self._WINDOW_HOTKEYS["linux"])[action]
            pyautogui.hotkey(*keys)
            return {"success": True,
                    "message": f"窗口操作已执行: {action}", "data": {}}
        except Exception as e:
            return {"success": False, "message": f"窗口操作失败: {e}",
                    "data": {"error": str(e)}}

    def window_minimize(self):
        return self._window_action("minimize")

    def window_maximize(self):
        return self._window_action("maximize")

    def window_restore(self):
        return self._window_action("restore")

    def window_close(self):
        return self._window_action("close")

    def _power_action(self, action: str) -> Dict[str, Any]:
        """电源/会话操作（固定 argv，无外部字符串拼接）。"""
        if not self.permissions.system_control:
            return {"success": False, "message": "权限不足：系统控制", "data": {}}
        try:
            argv = self._POWER_COMMANDS.get(
                sys.platform, self._POWER_COMMANDS["linux"])[action]
            subprocess.run(argv, timeout=10, check=False)
            return {"success": True,
                    "message": f"系统操作已执行: {action}", "data": {}}
        except Exception as e:
            return {"success": False, "message": f"系统操作失败: {e}",
                    "data": {"error": str(e)}}

    def system_lock(self):
        return self._power_action("lock")

    def system_shutdown(self):
        return self._power_action("shutdown")

    def system_restart(self):
        return self._power_action("restart")

    def system_sleep(self):
        return self._power_action("sleep")

    def set_volume(self, volume: int) -> Dict[str, Any]:
        if not self.permissions.system_control:
            return {"success": False, "message": "权限不足：系统控制", "data": {}}
        volume = max(0, min(100, int(volume)))
        try:
            if sys.platform == "win32":
                # Windows 无内置绝对音量 CLI：先静音复位，再以音量键逼近目标值
                pyautogui.press("volumemute")
                for _ in range(50):
                    pyautogui.press("volumeup")
                for _ in range(round((100 - volume) / 2)):
                    pyautogui.press("volumedown")
            elif sys.platform == "darwin":
                subprocess.run(
                    ["osascript", "-e",
                     f"set volume output volume {volume}"],
                    timeout=5, check=False)
            else:
                subprocess.run(
                    ["amixer", "sset", "Master", f"{volume}%"],
                    capture_output=True, timeout=5, check=False)
            return {"success": True,
                    "message": f"音量已设置为 {volume}%", "data": {}}
        except Exception as e:
            return {"success": False, "message": f"音量设置失败: {e}",
                    "data": {"error": str(e)}}

    def toggle_mute(self) -> Dict[str, Any]:
        if not self.permissions.system_control:
            return {"success": False, "message": "权限不足：系统控制", "data": {}}
        try:
            if sys.platform == "win32":
                pyautogui.press("volumemute")
            elif sys.platform == "darwin":
                subprocess.run(
                    ["osascript", "-e",
                     "set volume muted to not (muted)"],
                    timeout=5, check=False)
            else:
                subprocess.run(
                    ["amixer", "sset", "Master", "toggle"],
                    capture_output=True, timeout=5, check=False)
            return {"success": True, "message": "静音状态已切换", "data": {}}
        except Exception as e:
            return {"success": False, "message": f"静音切换失败: {e}",
                    "data": {"error": str(e)}}

    def execute_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "success": False,
            "operation": operation.get("type"),
            "message": "",
            "data": {}
        }

        op_type = operation.get("type")

        # 高危操作二次授权检查（统一入口，覆盖所有 AI 指令路径）
        denied = self._check_high_risk(op_type, operation)
        if denied is not None:
            return denied

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

        elif op_type == "mouse_move_relative":
            dx = operation.get("dx", 0)
            dy = operation.get("dy", 0)
            duration = operation.get("duration", 0.1)
            return self.mouse_move_relative(dx, dy, duration)

        elif op_type == "mouse_drag_start":
            return self.mouse_drag_start(operation.get("button", "left"))

        elif op_type == "mouse_drag_stop":
            return self.mouse_drag_stop(operation.get("button", "left"))

        elif op_type == "window_minimize":
            return self.window_minimize()

        elif op_type == "window_maximize":
            return self.window_maximize()

        elif op_type == "window_restore":
            return self.window_restore()

        elif op_type == "window_close":
            return self.window_close()

        elif op_type == "system_lock":
            return self.system_lock()

        elif op_type == "system_shutdown":
            return self.system_shutdown()

        elif op_type == "system_restart":
            return self.system_restart()

        elif op_type == "system_sleep":
            return self.system_sleep()

        elif op_type == "volume_set":
            return self.set_volume(operation.get("volume", 50))

        elif op_type == "mute_toggle":
            return self.toggle_mute()

        else:
            result["message"] = f"未知操作类型: {op_type}"
            return result