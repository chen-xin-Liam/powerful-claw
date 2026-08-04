from PIL import ImageGrab
import cv2
import numpy as np
from typing import Optional, Tuple

class VisionCapture:
    def __init__(self):
        self.camera = None
    
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[ImageGrab.Image]:
        try:
            screenshot = ImageGrab.grab(bbox=region)
            return screenshot
        except Exception as e:
            return None
    
    def capture_screen_np(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        screenshot = self.capture_screen(region)
        if screenshot:
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return None
    
    def save_screenshot(self, path: str, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        screenshot = self.capture_screen(region)
        if screenshot:
            try:
                screenshot.save(path)
                return True
            except Exception as e:
                return False
        return False
    
    def initialize_camera(self, index: int = 0) -> bool:
        try:
            self.camera = cv2.VideoCapture(index)
            if not self.camera.isOpened():
                self.camera = None
                return False
            return True
        except Exception as e:
            self.camera = None
            return False
    
    def capture_camera(self) -> Optional[np.ndarray]:
        if not self.camera:
            if not self.initialize_camera():
                return None
        
        try:
            ret, frame = self.camera.read()
            if ret:
                return frame
            return None
        except Exception as e:
            return None
    
    def release_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
    
    def get_camera_resolution(self) -> Optional[Tuple[int, int]]:
        if not self.camera:
            return None
        try:
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (width, height)
        except Exception as e:
            return None
