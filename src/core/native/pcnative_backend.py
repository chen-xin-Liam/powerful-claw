# -*- coding: utf-8 -*-
"""
pcnative_backend - powerful-claw 原生加速内核的 Python 绑定（cffi）

后端选择（环境变量 PCNATIVE_BACKEND）：
    auto   优先原生，加载/调用失败静默回退 Python（默认）
    native 强制使用原生
    python 强制使用 Python

公开 API：
    NATIVE_AVAILABLE: bool
    backend_name() -> "native" | "python"
    ascii_gray(gray, width, height, invert) -> str
    pixel_matrix_rgb(rgb, width, height, sample_size) -> str
    plan_blocks(rgb, mask|None, width, height, block_size, min_ratio)
        -> (list[(x, y, w, h, hash)], changed_pixels)
    block_hash(rgb, width, height, x, y, w, h) -> int
    expr_eval(expr) -> float            # 失败抛 ValueError
    pack_message(msg_type, sequence, payload) -> bytes
    unpack_message(frame) -> (msg_type, sequence, payload)
    clamp(x, lo, hi) / lerp(a, b, t) / crc32(data)
"""
import os
import sys
from typing import List, Optional, Tuple

_CDEF = """
const char* pcn_version(void);
const char* pcn_last_error(void);
void pcn_free(void* ptr);

char* pcn_ascii_gray(const unsigned char*, int, int, int, int*);
char* pcn_pixel_matrix_rgb(const unsigned char*, int, int, int, int*);
char* pcn_sampled_matrix(const unsigned char*, int, int, int, int, int*);

typedef struct {
    int x, y, w, h;
    unsigned int hash;
} pcn_block_t;
int pcn_plan_blocks(const unsigned char*, const unsigned char*,
                    int, int, int, double,
                    pcn_block_t*, int, int*);
unsigned int pcn_block_hash(const unsigned char*, int, int,
                            int, int, int, int);
int pcn_scan_mask(const unsigned char*, int, int, int, double,
                  pcn_block_t*, int);
unsigned int pcn_adler32(const unsigned char*, int);

int pcn_expr_eval(const char*, double*);

unsigned char* pcn_pack(unsigned char, unsigned int,
                        const unsigned char*, unsigned int, int*);
int pcn_unpack(const unsigned char*, int,
               unsigned char*, unsigned int*,
               const unsigned char**, unsigned int*);

double pcn_clamp(double, double, double);
double pcn_lerp(double, double, double);
unsigned int pcn_crc32(const unsigned char*, int);
"""

ffi = None
lib = None
NATIVE_AVAILABLE = False
_load_error = ""


def _candidate_paths() -> List[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(here, "pcnative", "build")
    if sys.platform == "win32":
        names = ["libpcnative.dll", "pcnative.dll"]
    elif sys.platform == "darwin":
        names = ["libpcnative.dylib"]
    else:
        names = ["libpcnative.so"]
    paths = [os.path.join(build_dir, n) for n in names]
    explicit = os.environ.get("PCNATIVE_LIB")
    if explicit:
        paths.insert(0, explicit)
    return paths


def _load():
    global ffi, lib, NATIVE_AVAILABLE, _load_error
    mode = os.environ.get("PCNATIVE_BACKEND", "auto").strip().lower()
    if mode == "python":
        _load_error = "PCNATIVE_BACKEND=python"
        return
    try:
        import cffi

        ffi = cffi.FFI()
        ffi.cdef(_CDEF)
        last = ""
        for path in _candidate_paths():
            if os.path.exists(path):
                try:
                    lib = ffi.dlopen(path)
                    NATIVE_AVAILABLE = True
                    return
                except Exception as e:  # dlopen 失败（缺符号等）尝试下一个
                    last = str(e)
        if last:
            _load_error = last
    except ImportError as e:
        _load_error = f"cffi 未安装: {e}"
    except Exception as e:
        _load_error = str(e)


_load()


def backend_name() -> str:
    return "native" if NATIVE_AVAILABLE else "python"


def _last_error() -> str:
    try:
        p = lib.pcn_last_error()
        return ffi.string(p).decode("utf-8", "replace") if p else "未知错误"
    except Exception:
        return "未知错误"


# ---------------- 1. 图像热点 ----------------

def ascii_gray(gray: bytes, width: int, height: int,
               invert: bool = False) -> str:
    n = ffi.new("int*")
    ptr = lib.pcn_ascii_gray(gray, width, height,
                             1 if invert else 0, n)
    if ptr == ffi.NULL:
        raise RuntimeError(_last_error())
    try:
        return ffi.string(ptr, n[0]).decode("utf-8", "replace")
    finally:
        lib.pcn_free(ptr)


def pixel_matrix_rgb(rgb: bytes, width: int, height: int,
                     sample_size: int = 20) -> str:
    n = ffi.new("int*")
    ptr = lib.pcn_pixel_matrix_rgb(rgb, width, height, sample_size, n)
    if ptr == ffi.NULL:
        raise RuntimeError(_last_error())
    try:
        return ffi.string(ptr, n[0]).decode("utf-8", "replace")
    finally:
        lib.pcn_free(ptr)


def sampled_matrix(points: bytes, grid_cols: int, grid_rows: int,
                   orig_w: int, orig_h: int) -> str:
    n = ffi.new("int*")
    ptr = lib.pcn_sampled_matrix(points, grid_cols, grid_rows,
                                 orig_w, orig_h, n)
    if ptr == ffi.NULL:
        raise RuntimeError(_last_error())
    try:
        return ffi.string(ptr, n[0]).decode("utf-8", "replace")
    finally:
        lib.pcn_free(ptr)


# ---------------- 2. 帧差分块规划 ----------------

def _validate_block_coords(arr, count, width, height):
    """校验返回块坐标均在画面内（C 侧 PCN_ERR=1 与"1 个块"同值，
    用边界校验识别异常返回，避免把错误数据当块读取）。"""
    for i in range(count):
        x, y, w, h = arr[i].x, arr[i].y, arr[i].w, arr[i].h
        if not (0 <= x < width and 0 <= y < height and
                w > 0 and h > 0 and
                x + w <= width and y + h <= height):
            raise RuntimeError(_last_error() or "原生块规划返回非法坐标")


def plan_blocks(rgb: bytes, mask: Optional[bytes],
                width: int, height: int, block_size: int,
                min_changed_ratio: float = 0.05
                ) -> Tuple[List[Tuple[int, int, int, int, int]], int]:
    cols = (width + block_size - 1) // block_size
    rows = (height + block_size - 1) // block_size
    cap = cols * rows
    arr = ffi.new("pcn_block_t[]", cap)
    changed = ffi.new("int*")
    mask_arg = mask if mask else ffi.NULL
    count = lib.pcn_plan_blocks(
        rgb, mask_arg, width, height, block_size,
        float(min_changed_ratio), arr, cap, changed)
    if count < 0:
        raise RuntimeError(_last_error())
    _validate_block_coords(arr, count, width, height)
    result = [(arr[i].x, arr[i].y, arr[i].w, arr[i].h,
               int(arr[i].hash))
              for i in range(count)]
    return result, changed[0]


def block_hash(rgb: bytes, width: int, height: int,
               x: int, y: int, w: int, h: int) -> int:
    return int(lib.pcn_block_hash(rgb, width, height, x, y, w, h))


def scan_mask(mask: bytes, width: int, height: int, block_size: int,
              min_changed_ratio: float = 0.05
              ) -> List[Tuple[int, int, int, int]]:
    """稀疏路径：仅扫描掩码，返回选中块坐标（无整帧 RGB 拷贝）。"""
    cols = (width + block_size - 1) // block_size
    rows = (height + block_size - 1) // block_size
    cap = cols * rows
    arr = ffi.new("pcn_block_t[]", cap)
    count = lib.pcn_scan_mask(
        mask, width, height, block_size,
        float(min_changed_ratio), arr, cap)
    if count < 0:
        raise RuntimeError(_last_error())
    _validate_block_coords(arr, count, width, height)
    return [(arr[i].x, arr[i].y, arr[i].w, arr[i].h)
            for i in range(count)]


def adler32(data: bytes) -> int:
    """连续字节 adler32（与 zlib.adler32 一致）。"""
    return int(lib.pcn_adler32(data, len(data)))


# ---------------- 3. 表达式 ----------------

def expr_eval(expr: str) -> float:
    out = ffi.new("double*")
    rc = lib.pcn_expr_eval(expr.encode("utf-8"), out)
    if rc != 0:
        raise ValueError(_last_error())
    return float(out[0])


# ---------------- 4. 封包 / 核心计算 ----------------

def pack_message(msg_type: int, sequence: int,
                 payload: bytes = b"") -> bytes:
    n = ffi.new("int*")
    payload_arg = payload if payload else ffi.NULL
    buf = lib.pcn_pack(int(msg_type), int(sequence),
                       payload_arg, len(payload), n)
    if buf == ffi.NULL:
        raise RuntimeError(_last_error())
    try:
        return ffi.buffer(buf, n[0])[:]
    finally:
        lib.pcn_free(buf)


def unpack_message(frame: bytes) -> Tuple[int, int, bytes]:
    mt = ffi.new("unsigned char*")
    seq = ffi.new("unsigned int*")
    plen = ffi.new("unsigned int*")
    pl = ffi.new("const unsigned char**")
    rc = lib.pcn_unpack(frame, len(frame), mt, seq, pl, plen)
    if rc != 0:
        raise ValueError(_last_error())
    return int(mt[0]), int(seq[0]), bytes(ffi.buffer(pl[0], plen[0]))


def clamp(x: float, lo: float, hi: float) -> float:
    return float(lib.pcn_clamp(x, lo, hi))


def lerp(a: float, b: float, t: float) -> float:
    return float(lib.pcn_lerp(a, b, t))


def crc32(data: bytes) -> int:
    if not data:
        return 0
    return int(lib.pcn_crc32(data, len(data)))
