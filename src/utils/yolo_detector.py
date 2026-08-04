import os
from PIL import ImageGrab, Image
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
import cv2

class YOLODetector:
    MODELS_DIR = "./models"
    
    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model = None
        self.model_name = model_name
        self.is_loaded = False
        self.is_streaming = False
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
            'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
            'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book',
            'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush', 'wine glass'
        ]
        self._ensure_models_dir()
    
    def _ensure_models_dir(self):
        os.makedirs(self.MODELS_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.MODELS_DIR, "ultralytics"), exist_ok=True)
    
    def load_model(self, model_name: Optional[str] = None) -> bool:
        try:
            from ultralytics import YOLO
            model_path = model_name or self.model_name
            
            if not os.path.exists(model_path) and model_path == "yolov8n.pt":
                model_path = os.path.join(self.MODELS_DIR, "yolov8n.pt")
            
            self.model = YOLO(model_path)
            self.model_name = model_path
            self.is_loaded = True
            return True
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            self.is_loaded = False
            return False
    
    def start_camera_stream(self, camera_id: int = 0, conf: float = 0.25, callback=None) -> Dict[str, Any]:
        if self.is_streaming:
            return {"success": False, "message": "摄像头已经在运行中"}
        
        if not self.is_loaded:
            if not self.load_model():
                return {"success": False, "message": "YOLO模型加载失败"}
        
        self.is_streaming = True
        
        def stream_thread():
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                if callback:
                    callback({"success": False, "message": "无法打开摄像头"})
                self.is_streaming = False
                return
            
            while self.is_streaming:
                ret, frame = cap.read()
                if not ret:
                    break
                
                results = self.model(frame, conf=conf, verbose=False)
                
                annotated_frame = results[0].plot()
                
                cv2.imshow("YOLO Real-time Detection", annotated_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                if callback:
                    detections = []
                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf_score = float(box.conf[0].cpu().numpy())
                            cls_id = int(box.cls[0].cpu().numpy())
                            cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else f"class_{cls_id}"
                            detections.append({
                                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                "confidence": round(conf_score, 3),
                                "class_name": cls_name,
                                "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)]
                            })
                    
                    callback({
                        "success": True,
                        "frame": frame,
                        "detections": detections,
                        "count": len(detections)
                    })
            
            cap.release()
            cv2.destroyAllWindows()
            self.is_streaming = False
        
        import threading
        thread = threading.Thread(target=stream_thread, daemon=True)
        thread.start()
        
        return {"success": True, "message": "摄像头实时检测已启动，按Q退出"}
    
    def stop_camera_stream(self):
        self.is_streaming = False
        try:
            cv2.destroyAllWindows()
        except:
            pass
        return {"success": True, "message": "摄像头已关闭"}
    
    def analyze_camera_realtime(self, duration: int = 10, camera_id: int = 0, conf: float = 0.25) -> Dict[str, Any]:
        if not self.is_loaded:
            if not self.load_model():
                return {"success": False, "message": "YOLO模型加载失败"}
        
        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                return {"success": False, "message": "无法打开摄像头"}
            
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            import time
            start_time = time.time()
            frame_count = 0
            all_detections = []
            
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % 2 == 0:
                    results = self.model(frame, conf=conf, verbose=False)
                    
                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            conf_score = float(box.conf[0].cpu().numpy())
                            cls_id = int(box.cls[0].cpu().numpy())
                            cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else f"class_{cls_id}"
                            all_detections.append({
                                "class_name": cls_name,
                                "confidence": round(conf_score, 3),
                                "timestamp": time.time() - start_time
                            })
                
                frame_count += 1
            
            cap.release()
            
            summary = self._generate_realtime_summary(all_detections)
            
            return {
                "success": True,
                "message": f"实时分析完成，持续 {duration} 秒",
                "data": {
                    "detections": all_detections,
                    "duration": duration,
                    "summary": summary
                }
            }
        except Exception as e:
            return {"success": False, "message": f"实时分析失败: {str(e)}"}
    
    def _generate_realtime_summary(self, detections: List[Dict]) -> str:
        if not detections:
            return "未检测到任何对象"
        
        class_counts = {}
        for det in detections:
            cls_name = det["class_name"]
            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
        
        lines = ["📹 YOLO实时摄像头分析摘要"]
        lines.append("=" * 40)
        lines.append(f"检测总数: {len(detections)}")
        lines.append("")
        lines.append("检测到的对象:")
        
        for cls_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  • {cls_name}: {count}次")
        
        return "\n".join(lines)
    
    def detect_objects(self, image: Image.Image, conf: float = 0.25) -> Dict[str, Any]:
        if not self.is_loaded:
            if not self.load_model():
                return {
                    "success": False,
                    "message": "YOLO模型加载失败",
                    "data": {}
                }
        
        try:
            img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            results = self.model(img_array, conf=conf)
            
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf_score = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else f"class_{cls_id}"
                    
                    detections.append({
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "confidence": round(conf_score, 3),
                        "class_id": cls_id,
                        "class_name": cls_name,
                        "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)]
                    })
            
            return {
                "success": True,
                "message": f"检测到 {len(detections)} 个对象",
                "data": {
                    "detections": detections,
                    "count": len(detections),
                    "model": self.model_name
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"检测失败: {str(e)}",
                "data": {"error": str(e)}
            }
    
    def detect_screen(self, region: Optional[Tuple[int, int, int, int]] = None, conf: float = 0.25) -> Dict[str, Any]:
        try:
            screenshot = ImageGrab.grab(bbox=region)
            return self.detect_objects(screenshot, conf)
        except Exception as e:
            return {
                "success": False,
                "message": f"截图失败: {str(e)}",
                "data": {"error": str(e)}
            }
    
    def find_object(self, class_name: str, conf: float = 0.25, region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        result = self.detect_screen(region, conf)
        
        if not result["success"]:
            return result
        
        detections = result["data"]["detections"]
        targets = [d for d in detections if class_name.lower() in d["class_name"].lower()]
        
        if targets:
            targets.sort(key=lambda x: x["confidence"], reverse=True)
            best = targets[0]
            return {
                "success": True,
                "message": f"找到对象: {best['class_name']}",
                "data": {
                    "object": best,
                    "count": len(targets),
                    "all_objects": targets
                }
            }
        
        return {
            "success": False,
            "message": f"未找到对象: {class_name}",
            "data": {"available_objects": [d["class_name"] for d in detections[:10]]}
        }
    
    def get_detection_summary(self, result: Dict[str, Any]) -> str:
        if not result.get("success"):
            return f"检测失败: {result.get('message', 'Unknown error')}"
        
        data = result.get("data", {})
        detections = data.get("detections", [])
        
        if not detections:
            return "未检测到任何对象"
        
        summary = [f"检测到 {len(detections)} 个对象:"]
        
        class_counts = {}
        for det in detections:
            cls_name = det["class_name"]
            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
        
        for cls_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 1:
                summary.append(f"  • {cls_name}: {count}个")
            else:
                det = next(d for d in detections if d["class_name"] == cls_name)
                summary.append(f"  • {cls_name} (置信度: {det['confidence']:.2f})")
        
        return "\n".join(summary)
    
    def format_detection_for_ai(self, result: Dict[str, Any]) -> str:
        if not result.get("success"):
            return f"YOLO检测失败: {result.get('message', 'Unknown error')}"
        
        data = result.get("data", {})
        detections = data.get("detections", [])
        
        if not detections:
            return "屏幕中未检测到任何已知对象"
        
        lines = ["📷 YOLO对象检测结果", "=" * 40]
        lines.append(f"模型: {data.get('model', 'unknown')}")
        lines.append(f"检测数量: {len(detections)}")
        lines.append("")
        
        class_counts = {}
        for det in detections:
            cls_name = det["class_name"]
            if cls_name not in class_counts:
                class_counts[cls_name] = []
            class_counts[cls_name].append(det)
        
        lines.append("检测到的对象:")
        for cls_name, dets in sorted(class_counts.items(), key=lambda x: len(x[1]), reverse=True):
            lines.append(f"  [{cls_name}] x {len(dets)}")
            for det in dets:
                x1, y1, x2, y2 = det["bbox"]
                lines.append(f"    - 位置: ({x1}, {y1}) 到 ({x2}, {y2})")
                lines.append(f"      中心点: ({det['center'][0]}, {det['center'][1]})")
                lines.append(f"      置信度: {det['confidence']:.2%}")
        
        return "\n".join(lines)