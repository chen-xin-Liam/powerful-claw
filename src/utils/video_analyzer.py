import cv2
import time
from typing import List, Dict, Any, Optional
from PIL import Image
import numpy as np
from src.utils.yolo_detector import YOLODetector

class VideoAnalyzer:
    def __init__(self):
        self.yolo_detector = YOLODetector()
        self.is_running = False
        self.cap = None
    
    def analyze_video_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        try:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = self.yolo_detector.detect_objects(img, conf=0.3)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"帧分析失败: {str(e)}",
                "data": {"error": str(e)}
            }
    
    def analyze_video_file(self, video_path: str, frame_interval: int = 10) -> Dict[str, Any]:
        results = []
        try:
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                return {"success": False, "message": "无法打开视频文件", "data": {}}
            
            frame_count = 0
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            while self.cap.isOpened() and frame_count < total_frames:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    result = self.analyze_video_frame(frame)
                    result["frame_number"] = frame_count
                    result["timestamp"] = frame_count / fps
                    results.append(result)
                
                frame_count += 1
            
            self.cap.release()
            
            summary = self._generate_summary(results, fps)
            
            return {
                "success": True,
                "message": f"视频分析完成，共分析 {len(results)} 帧",
                "data": {
                    "results": results,
                    "total_frames": total_frames,
                    "fps": fps,
                    "summary": summary,
                    "frame_interval": frame_interval
                }
            }
        except Exception as e:
            if self.cap:
                self.cap.release()
            return {
                "success": False,
                "message": f"视频分析失败: {str(e)}",
                "data": {"error": str(e)}
            }
    
    def analyze_camera(self, duration: int = 5, frame_interval: int = 2) -> Dict[str, Any]:
        results = []
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                return {"success": False, "message": "无法打开摄像头", "data": {}}
            
            fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            start_time = time.time()
            frame_count = 0
            
            while time.time() - start_time < duration and self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    result = self.analyze_video_frame(frame)
                    result["frame_number"] = frame_count
                    result["timestamp"] = time.time() - start_time
                    results.append(result)
                
                frame_count += 1
                time.sleep(0.03)
            
            self.cap.release()
            self.is_running = False
            
            summary = self._generate_summary(results, fps)
            
            return {
                "success": True,
                "message": f"摄像头分析完成，持续 {duration} 秒，分析 {len(results)} 帧",
                "data": {
                    "results": results,
                    "duration": duration,
                    "fps": fps,
                    "summary": summary,
                    "frame_interval": frame_interval
                }
            }
        except Exception as e:
            if self.cap:
                self.cap.release()
            self.is_running = False
            return {
                "success": False,
                "message": f"摄像头分析失败: {str(e)}",
                "data": {"error": str(e)}
            }
    
    def start_live_analysis(self, callback=None):
        self.is_running = True
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                if callback:
                    callback({"success": False, "message": "无法打开摄像头"})
                return
            
            fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            frame_count = 0
            
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                if frame_count % 2 == 0:
                    result = self.analyze_video_frame(frame)
                    result["frame_number"] = frame_count
                    result["timestamp"] = frame_count / fps
                    
                    if callback:
                        callback(result)
                
                frame_count += 1
                time.sleep(0.03)
            
            self.cap.release()
        except Exception as e:
            if self.cap:
                self.cap.release()
            if callback:
                callback({"success": False, "message": f"实时分析失败: {str(e)}"})
    
    def stop_live_analysis(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
    
    def _generate_summary(self, results: List[Dict], fps: float) -> str:
        all_detections = []
        for result in results:
            if result.get("success"):
                detections = result.get("data", {}).get("detections", [])
                all_detections.extend(detections)
        
        if not all_detections:
            return "视频中未检测到任何对象"
        
        class_counts = {}
        for det in all_detections:
            cls_name = det["class_name"]
            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
        
        summary_lines = ["📹 视频分析摘要"]
        summary_lines.append("=" * 40)
        summary_lines.append(f"分析帧数: {len(results)}")
        summary_lines.append(f"视频帧率: {fps:.1f} FPS")
        summary_lines.append("")
        summary_lines.append("检测到的对象:")
        
        for cls_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(all_detections)) * 100
            summary_lines.append(f"  • {cls_name}: {count}次 ({percentage:.1f}%)")
        
        return "\n".join(summary_lines)
    
    def format_result_for_ai(self, result: Dict[str, Any]) -> str:
        if not result.get("success"):
            return f"视频分析失败: {result.get('message', 'Unknown error')}"
        
        data = result.get("data", {})
        
        if "summary" in data:
            return data["summary"]
        
        return self.yolo_detector.format_detection_for_ai(result)