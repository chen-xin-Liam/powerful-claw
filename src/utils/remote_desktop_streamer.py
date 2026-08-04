import io
import time
import base64
import struct
import zlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from PIL import Image
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


@dataclass
class RDConfig:
    enabled: bool = True
    fps: int = 30
    quality: int = 70
    scale: float = 1.0

    diff_threshold: int = 10
    min_changed_pixels: int = 100

    block_size: int = 64
    keyframe_interval: int = 60

    motion_detection: bool = True
    motion_threshold: int = 25

    adaptive_quality: bool = True
    min_quality: int = 30
    max_quality: int = 95

    compress_blocks: bool = True
    block_cache_size: int = 256


class FrameDiffer:
    """帧差计算器"""

    def __init__(self, threshold: int = 10):
        self.threshold = threshold
        self.prev_frame = None
        self.prev_gray = None

    def compare(self, frame: np.ndarray) -> Tuple[bool, np.ndarray, np.ndarray]:
        """
        比较当前帧与上一帧
        Returns: (has_changes, diff_mask, changed_regions)
        """
        if not HAS_CV2:
            return True, None, None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        if self.prev_gray is None:
            self.prev_gray = gray
            return True, None, None

        diff = cv2.absdiff(gray, self.prev_gray)
        _, diff_binary = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)

        kernel = np.ones((5, 5), np.uint8)
        diff_binary = cv2.morphologyEx(diff_binary, cv2.MORPH_OPEN, kernel)
        diff_binary = cv2.morphologyEx(diff_binary, cv2.MORPH_CLOSE, kernel)

        changed_pixels = cv2.countNonZero(diff_binary)
        has_changes = changed_pixels > 100

        self.prev_gray = gray

        return has_changes, diff, diff_binary

    def reset(self):
        self.prev_frame = None
        self.prev_gray = None


class BlockEncoder:
    """分块编码器 - 将图像分成块独立编码"""

    def __init__(self, config: RDConfig):
        self.config = config
        self.block_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def encode_blocks(self, frame: Image.Image, diff_mask: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """分块编码图像"""
        if self.config.compress_blocks:
            return self._encode_with_blocks(frame, diff_mask)
        else:
            return self._encode_full(frame)

    def _encode_full(self, frame: Image.Image) -> Dict[str, Any]:
        """编码完整帧"""
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG', quality=self.config.quality, progressive=True)
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return {
            'type': 'full',
            'data': encoded,
            'blocks': [],
            'width': frame.width,
            'height': frame.height,
            'timestamp': time.time()
        }

    def _encode_with_blocks(self, frame: Image.Image, diff_mask: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """分块编码，只编码变化的区域"""
        width, height = frame.width, frame.height
        block_size = self.config.block_size

        blocks = []
        changed_indices = []

        frame_array = np.array(frame)
        if diff_mask is not None and len(diff_mask.shape) == 2 and HAS_CV2:
            diff_resized = cv2.resize(diff_mask, (width, height))
        else:
            diff_resized = None

        for y in range(0, height, block_size):
            for x in range(0, width, block_size):
                block_x2 = min(x + block_size, width)
                block_y2 = min(y + block_size, height)

                should_encode = True

                if diff_resized is not None:
                    block_diff = diff_resized[y:block_y2, x:block_x2]
                    changed_ratio = np.sum(block_diff > 0) / (block_diff.shape[0] * block_diff.shape[1])

                    if changed_ratio < 0.05:
                        should_encode = False

                if should_encode:
                    block = frame.crop((x, y, block_x2, block_y2))
                    block_hash = self._get_block_hash(block)

                    if block_hash in self.block_cache:
                        block_data = self.block_cache[block_hash]
                        self.cache_hits += 1
                    else:
                        buffer = io.BytesIO()
                        block.save(buffer, format='JPEG', quality=self.config.quality)
                        block_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

                        if len(self.block_cache) < self.config.block_cache_size:
                            self.block_cache[block_hash] = block_data

                        self.cache_misses += 1

                    blocks.append({
                        'x': x,
                        'y': y,
                        'w': block_x2 - x,
                        'h': block_y2 - y,
                        'data': block_data
                    })
                    changed_indices.append(f"{x},{y}")

        return {
            'type': 'blocks',
            'data': blocks,
            'changed': changed_indices,
            'width': width,
            'height': height,
            'block_size': block_size,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'timestamp': time.time()
        }

    def _get_block_hash(self, block: Image.Image) -> str:
        """获取图像块的哈希值"""
        block_array = np.array(block.resize((32, 32)))
        return zlib.adler32(block_array.tobytes()).__hex__()

    def clear_cache(self):
        self.block_cache.clear()


class MotionDetector:
    """运动检测器"""

    def __init__(self, threshold: int = 25):
        self.threshold = threshold
        self.prev_frame = None
        self.motion_regions = []

    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        检测运动区域
        Returns: List of (x, y, w, h) bounding boxes
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_frame is None:
            self.prev_frame = gray
            return []

        frameDelta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frameDelta, self.threshold, 255, cv2.THRESH_BINARY)[1]

        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions = []
        for contour in contours:
            if cv2.contourArea(contour) < 500:
                continue

            (x, y, w, h) = cv2.boundingRect(contour)
            regions.append((x, y, w, h))

        self.prev_frame = gray
        self.motion_regions = regions

        return regions

    def reset(self):
        self.prev_frame = None
        self.motion_regions = []


class AdaptiveQualityController:
    """自适应质量控制器"""

    def __init__(self, min_q: int = 30, max_q: int = 95, target_fps: int = 30):
        self.min_quality = min_q
        self.max_quality = max_quality
        self.target_fps = target_fps

        self.frame_times = []
        self.window_size = 30

        self.current_quality = (min_q + max_q) // 2
        self.bytes_per_second = 0
        self.last_bytes = 0
        self.last_check_time = time.time()

    def update(self, frame_size: int, current_fps: float):
        """更新质量参数"""
        current_time = time.time()
        time_delta = current_time - self.last_check_time

        if time_delta >= 1.0:
            self.bytes_per_second = (frame_size - self.last_bytes) / time_delta
            self.last_bytes = frame_size
            self.last_check_time = current_time

        self.frame_times.append(current_fps)
        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)

        avg_fps = sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0

        if avg_fps < self.target_fps * 0.7:
            self.current_quality = max(self.min_quality, self.current_quality - 5)
        elif avg_fps > self.target_fps * 0.95 and self.current_quality < self.max_quality:
            self.current_quality = min(self.max_quality, self.current_quality + 2)

        return self.current_quality


class RemoteDesktopStreamer:
    """远程桌面式视频流处理器"""

    def __init__(self, config: Optional[RDConfig] = None):
        self.config = config or RDConfig()

        self.frame_differ = FrameDiffer(threshold=self.config.diff_threshold)
        self.block_encoder = BlockEncoder(self.config)
        self.motion_detector = MotionDetector(threshold=self.config.motion_threshold)
        self.quality_controller = AdaptiveQualityController(
            min_q=self.config.min_quality,
            max_q=self.config.max_quality,
            target_fps=self.config.fps
        )

        self.prev_frame = None
        self.frame_count = 0
        self.last_keyframe_time = 0
        self.keyframe_interval = self.config.keyframe_interval

        self.stats = {
            'frames_sent': 0,
            'bytes_sent': 0,
            'keyframes': 0,
            'delta_frames': 0,
            'avg_fps': 0,
            'compression_ratio': 0
        }

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """处理单帧图像，返回编码后的数据"""

        has_changes, diff_mask, _ = self.frame_differ.compare(frame)

        should_send_keyframe = (
            self.frame_count == 0 or
            self.frame_count % self.keyframe_interval == 0 or
            not has_changes
        )

        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if should_send_keyframe:
            result = self.block_encoder.encode_blocks(frame_pil, None)
            result['is_keyframe'] = True
            self.stats['keyframes'] += 1
        else:
            result = self.block_encoder.encode_blocks(frame_pil, diff_mask)
            result['is_keyframe'] = False
            self.stats['delta_frames'] += 1

        result['stats'] = self.get_stats()

        if self.config.adaptive_quality:
            quality = self.quality_controller.update(
                len(str(result).encode()),
                self.stats['avg_fps']
            )
            result['adaptive_quality'] = quality

        self.frame_count += 1
        self.stats['frames_sent'] += 1

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取传输统计信息"""
        return {
            'frames_sent': self.stats['frames_sent'],
            'keyframes': self.stats['keyframes'],
            'delta_frames': self.stats['delta_frames'],
            'cache_hits': self.block_encoder.cache_hits,
            'cache_misses': self.block_encoder.cache_misses,
            'current_quality': self.quality_controller.current_quality
        }

    def reset(self):
        """重置状态"""
        self.frame_differ.reset()
        self.motion_detector.reset()
        self.block_encoder.clear_cache()
        self.prev_frame = None
        self.frame_count = 0


class ScreenCapturer:
    """屏幕捕获器 - 优化版"""

    def __init__(self, config: Optional[RDConfig] = None):
        self.config = config or RDConfig()
        self.streamer = RemoteDesktopStreamer(config)

        self._is_running = False
        self._capture_thread = None

        self._callbacks = []

    def add_callback(self, callback):
        """添加帧回调函数"""
        self._callbacks.append(callback)

    def remove_callback(self, callback):
        """移除帧回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def capture_screen(self) -> Optional[np.ndarray]:
        """捕获屏幕"""
        try:
            if HAS_CV2:
                import mss
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    screenshot = sct.grab(monitor)
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    return frame
            else:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
                return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[ScreenCapturer] 截图失败: {e}")
            return None

    def start(self):
        """启动捕获"""
        if self._is_running:
            return

        self._is_running = True
        self._capture_thread = None

    def stop(self):
        """停止捕获"""
        self._is_running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=1)

    def capture_and_process(self) -> Optional[Dict[str, Any]]:
        """捕获并处理一帧"""
        if not self._is_running:
            return None

        frame = self.capture_screen()
        if frame is None:
            return None

        if self.config.scale != 1.0:
            width = int(frame.shape[1] * self.config.scale)
            height = int(frame.shape[0] * self.config.scale)
            frame = cv2.resize(frame, (width, height))

        result = self.streamer.process_frame(frame)

        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                print(f"[ScreenCapturer] 回调错误: {e}")

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.streamer.get_stats()


if __name__ == '__main__':
    import time

    config = RDConfig(
        fps=30,
        quality=70,
        scale=1.0,
        motion_detection=True,
        adaptive_quality=True
    )

    capturer = ScreenCapturer(config)

    print("[测试] 屏幕捕获器启动")
    capturer.start()

    try:
        for i in range(100):
            result = capturer.capture_and_process()
            if result:
                stats = result['stats']
                print(f"[测试] 帧 {i}: 类型={result['type']}, "
                      f"关键帧={result.get('is_keyframe', False)}, "
                      f"质量={stats.get('current_quality', 0)}, "
                      f"缓存命中={stats.get('cache_hits', 0)}")
            time.sleep(0.033)
    except KeyboardInterrupt:
        print("\n[测试] 停止捕获")

    capturer.stop()
    print("[测试] 屏幕捕获器已停止")