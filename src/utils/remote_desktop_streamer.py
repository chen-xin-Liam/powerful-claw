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

try:
    from src.core.native import pcnative_backend
except Exception:
    pcnative_backend = None


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

    def __init__(self, threshold: int = 10, min_changed_pixels: int = 100):
        self.threshold = threshold
        self.min_changed_pixels = min_changed_pixels
        self.prev_frame = None
        self.prev_gray = None
        # 复用单个形态学 kernel，避免每帧重建
        self._kernel = np.ones((5, 5), np.uint8)

    def compare(self, frame: np.ndarray) -> Tuple[bool, np.ndarray, np.ndarray]:
        """
        比较当前帧与上一帧
        Returns: (has_changes, diff_mask, changed_regions)
        """
        if not HAS_CV2:
            # 无 cv2 时无法做差分，保守地认为有变化（首帧兜底），调用方会正常编码
            return True, None, None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        if self.prev_gray is None:
            self.prev_gray = gray
            return True, None, None

        diff = cv2.absdiff(gray, self.prev_gray)
        _, diff_binary = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)

        diff_binary = cv2.morphologyEx(diff_binary, cv2.MORPH_OPEN, self._kernel)
        diff_binary = cv2.morphologyEx(diff_binary, cv2.MORPH_CLOSE, self._kernel)

        changed_pixels = cv2.countNonZero(diff_binary)
        has_changes = changed_pixels > self.min_changed_pixels

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

    def encode_blocks(self, frame: Image.Image, diff_mask: Optional[np.ndarray] = None,
                      quality: Optional[int] = None) -> Dict[str, Any]:
        """分块编码图像。quality 为 None 时使用 config.quality。"""
        if self.config.compress_blocks:
            return self._encode_with_blocks(frame, diff_mask, quality)
        else:
            return self._encode_full(frame, quality)

    def _encode_full(self, frame: Image.Image, quality: Optional[int] = None) -> Dict[str, Any]:
        """编码完整帧"""
        jpeg_quality = self.config.quality if quality is None else quality
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG', quality=jpeg_quality, progressive=True)
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return {
            'type': 'full',
            'data': encoded,
            'blocks': [],
            'width': frame.width,
            'height': frame.height,
            'timestamp': time.time()
        }

    def _encode_with_blocks(self, frame: Image.Image, diff_mask: Optional[np.ndarray] = None,
                            quality: Optional[int] = None) -> Dict[str, Any]:
        """分块编码，只编码变化的区域"""
        jpeg_quality = self.config.quality if quality is None else quality
        width, height = frame.width, frame.height
        block_size = self.config.block_size

        blocks = []
        changed_indices = []

        if diff_mask is not None and len(diff_mask.shape) == 2 and HAS_CV2:
            diff_resized = cv2.resize(diff_mask, (width, height))
        else:
            diff_resized = None

        # 原生路径：
        #   - 无掩码 / 掩码密集：plan_blocks 一次完成扫描+哈希（需整帧字节）；
        #   - 掩码稀疏：scan_mask 仅扫掩码（不复制整帧），再按块取字节哈希
        if pcnative_backend is not None and pcnative_backend.NATIVE_AVAILABLE:
            try:
                if diff_resized is None:
                    planned, _ = pcnative_backend.plan_blocks(
                        frame.tobytes(), None, width, height,
                        block_size, 0.05)
                else:
                    mask_bytes = (diff_resized > 0).astype(np.uint8).tobytes()
                    coords = pcnative_backend.scan_mask(
                        mask_bytes, width, height, block_size, 0.05)
                    # 选中块覆盖过半时视为密集，改用整帧单次规划
                    total_blocks = ((width + block_size - 1) // block_size) * \
                                   ((height + block_size - 1) // block_size)
                    if len(coords) > total_blocks // 2:
                        planned, _ = pcnative_backend.plan_blocks(
                            frame.tobytes(), mask_bytes, width, height,
                            block_size, 0.05)
                    else:
                        planned = []
                        for bx, by, bw, bh in coords:
                            blk = frame.crop(
                                (bx, by, bx + bw, by + bh))
                            hsh = pcnative_backend.adler32(blk.tobytes())
                            planned.append((bx, by, bw, bh, hsh))
                return self._build_blocks_response(
                    frame, planned, jpeg_quality, width, height, block_size)
            except Exception:
                # 原生路径异常时回退到纯 Python 规划
                pass

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
                    block_hash = f"{jpeg_quality}:{self._get_block_hash(block):08x}"

                    if block_hash in self.block_cache:
                        block_data = self.block_cache[block_hash]
                        self.cache_hits += 1
                    else:
                        buffer = io.BytesIO()
                        block.save(buffer, format='JPEG', quality=jpeg_quality)
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

    def _build_blocks_response(self, frame: Image.Image, planned,
                               jpeg_quality: int, width: int,
                               height: int, block_size: int) -> Dict[str, Any]:
        """依据原生规划结果执行 JPEG 编码与缓存（输出结构与纯 Python 路径一致）。"""
        blocks: List[Dict[str, Any]] = []
        changed_indices: List[str] = []

        for x, y, w, h, hsh in planned:
            key = f"{jpeg_quality}:{int(hsh):08x}"
            if key in self.block_cache:
                block_data = self.block_cache[key]
                self.cache_hits += 1
            else:
                block = frame.crop((x, y, x + w, y + h))
                buffer = io.BytesIO()
                block.save(buffer, format='JPEG', quality=jpeg_quality)
                block_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

                if len(self.block_cache) < self.config.block_cache_size:
                    self.block_cache[key] = block_data

                self.cache_misses += 1

            blocks.append({'x': x, 'y': y, 'w': w, 'h': h,
                           'data': block_data})
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

    def _get_block_hash(self, block: Image.Image) -> int:
        """获取图像块哈希：块原始 RGB 字节的 adler32（与原生后端一致）。"""
        return zlib.adler32(block.tobytes()) & 0xFFFFFFFF

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
        if not HAS_CV2:
            # 无 cv2 时不做运动检测，返回空（而不是抛 NameError）
            return []

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
        self.max_quality = max_q
        self.target_fps = target_fps

        self.frame_times = []
        self.window_size = 30

        self.current_quality = (min_q + max_q) // 2
        self.bytes_per_second = 0
        self.last_bytes = 0
        self.last_check_time = time.time()

    def update(self, cumulative_bytes: int, current_fps: float):
        """基于累计字节数更新码率估计，并依据实测帧率调整质量。

        Args:
            cumulative_bytes: 截至当前已发送的累计字节数（非单帧大小）。
            current_fps: 实测（平滑后的）当前帧率。
        """
        current_time = time.time()
        time_delta = current_time - self.last_check_time

        if time_delta >= 1.0:
            # 累计字节之差 / 经过时间；钳制为非负，避免异常输入产生负码率
            self.bytes_per_second = max(0.0, (cumulative_bytes - self.last_bytes) / time_delta)
            self.last_bytes = cumulative_bytes
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

        self.frame_differ = FrameDiffer(
            threshold=self.config.diff_threshold,
            min_changed_pixels=self.config.min_changed_pixels,
        )
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

        # 实测帧率（EMA 平滑）与帧间隔计时
        self._fps = 0.0
        self._last_frame_time = 0.0

        self.stats = {
            'frames_sent': 0,
            'bytes_sent': 0,
            'keyframes': 0,
            'delta_frames': 0,
            'avg_fps': 0,
            'compression_ratio': 0
        }

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """处理单帧图像，返回编码后的数据。

        - 无变化帧直接跳过，不做 PIL/JPEG 编码；
        - 关键帧仅在首帧或达到 keyframe_interval 时产生；
        - 自适应质量在编码前确定，并真正作为 JPEG quality 传入编码器。
        """
        # 1. 实测帧率（EMA 平滑），供自适应质量控制器使用
        now = time.time()
        if self._last_frame_time > 0:
            dt_frame = now - self._last_frame_time
            instant_fps = 1.0 / dt_frame if dt_frame > 1e-6 else 0.0
            self._fps = instant_fps if self._fps == 0.0 else self._fps * 0.8 + instant_fps * 0.2
        self._last_frame_time = now

        # 2. 帧差
        has_changes, diff_mask, _ = self.frame_differ.compare(frame)

        # 3. 无变化帧：跳过（首帧除外，首帧必须送出），不产生任何编码字节
        if self.frame_count > 0 and not has_changes:
            self.frame_count += 1
            return {
                'type': 'skip',
                'skipped': True,
                'is_keyframe': False,
                'timestamp': now,
                'stats': self.get_stats(),
            }

        # 4. 关键帧判定（真实逻辑：不再因"无变化"反发全帧）
        should_send_keyframe = (
            self.frame_count == 0 or
            self.frame_count % self.keyframe_interval == 0
        )

        # 5. 编码前先确定本次质量，并钳制为合法正数
        if self.config.adaptive_quality:
            quality = self.quality_controller.update(self.stats['bytes_sent'], self._fps)
        else:
            quality = self.config.quality
        quality = int(max(1, min(100, quality)))

        # 6. BGR→RGB（无 cv2 或非三通道时直接使用原数组）
        if HAS_CV2 and len(frame.shape) == 3:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = frame
        frame_pil = Image.fromarray(frame_rgb)

        if should_send_keyframe:
            result = self.block_encoder.encode_blocks(frame_pil, None, quality=quality)
            result['is_keyframe'] = True
            self.stats['keyframes'] += 1
        else:
            result = self.block_encoder.encode_blocks(frame_pil, diff_mask, quality=quality)
            result['is_keyframe'] = False
            self.stats['delta_frames'] += 1

        # 7. 统计实际编码字节（base64 长度近似线上字节）
        if result.get('type') == 'full':
            encoded_bytes = len(result['data'])
        else:
            encoded_bytes = sum(len(b['data']) for b in result.get('data', []))
        self.stats['bytes_sent'] += encoded_bytes
        result['encoded_bytes'] = encoded_bytes
        # 本次实际使用的 JPEG 质量（反馈闭环）
        result['quality'] = quality
        result['adaptive_quality'] = quality
        result['stats'] = self.get_stats()

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
        self._fps = 0.0
        self._last_frame_time = 0.0


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