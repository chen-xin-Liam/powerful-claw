"""nodecalc 原生后端（C++ DLL + cffi）

与 node_engine.py 中 EMBEDDED_CPP 同源（由 build_native.py 编译为 DLL）。
加载优先级：native（即时加载，无 JIT 开销）> cppyy（JIT 编译）> python（纯 Python 回退）。

对 expression_parser 暴露的 Graph/Node/Port 接口与 Python 回退完全一致：
  - g.add_node(node) -> int；g.nodes（支持 .index）；g.connect(...)；g.execute()
  - node.outputs[i].type / .s / .v / .m（type 为 'scalar'/'vector'/'matrix'）
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

# 节点名 -> C ABI kind（必须与 nodecalc_capi.cpp 的枚举一致）
_KIND = {
    "Number": 0, "Variable": 1,
    "Add": 2, "Sub": 3, "Mul": 4, "Div": 5, "Mod": 6,
    "Negate": 7, "Abs": 8, "Pow": 9,
    "Sqrt": 10, "Cbrt": 11, "Exp": 12, "Log": 13, "Log2": 14, "Log10": 15,
    "Sin": 16, "Cos": 17, "Tan": 18, "Asin": 19, "Acos": 20, "Atan": 21,
    "Sinh": 22, "Cosh": 23, "Tanh": 24,
    "VecCreate": 25, "VecAdd": 26, "VecDot": 27, "VecNorm": 28, "VecSum": 29,
    "MatCreate": 30, "MatMul": 31, "MatTranspose": 32, "MatDet": 33, "MatInverse": 34,
    "Sum": 35, "Mean": 36, "StdDev": 37, "Min": 38, "Max": 39, "Median": 40,
    "Clamp": 41, "Lerp": 42, "If": 43,
}

_TYPE_NAMES = {0: "scalar", 1: "vector", 2: "matrix"}

_CDEF = """
void* nc_node_new(int kind);
void* nc_node_new_number(double value);
void* nc_node_new_log(double base);
void* nc_node_new_vec(int n);
void* nc_node_new_mat(int rows, int cols);
void  nc_node_delete(void* node);
int   nc_node_input_count(void* node);
int   nc_node_output_count(void* node);
int   nc_node_input_type(void* node, int idx);
int   nc_node_output_type(void* node, int idx);
void* nc_graph_new(void);
void  nc_graph_delete(void* graph);
int   nc_graph_add_node(void* graph, void* node);
int   nc_graph_connect(void* graph, int src_node, int src_out, int dst_node, int dst_in);
int   nc_graph_execute(void* graph);
int   nc_port_type(void* node, int output_idx);
double nc_port_scalar(void* node, int output_idx);
int   nc_port_vec_len(void* node, int output_idx);
int   nc_port_vec_copy(void* node, int output_idx, double* out, int capacity);
int   nc_port_mat_rows(void* node, int output_idx);
int   nc_port_mat_cols(void* node, int output_idx);
int   nc_port_mat_copy(void* node, int output_idx, double* out, int capacity);
const char* nc_last_error(void);
"""


def _dll_path():
    if getattr(sys, "frozen", False):  # PyInstaller 打包后
        base = getattr(sys, "_MEIPASS", _HERE)
        candidates = [os.path.join(base, "nodecalc_native.dll"),
                      os.path.join(base, "src", "core", "native", "nodecalc_native.dll")]
    else:
        candidates = [os.path.join(_HERE, "nodecalc_native.dll")]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _ensure_dll():
    """DLL 缺失时，若本机存在 g++ 则自动执行一次构建（与 cppyy 自动 JIT 同范式）"""
    if _dll_path() is not None:
        return True
    if os.environ.get("NODECALC_NO_AUTOBUILD", "").lower() in ("1", "true"):
        return False
    import shutil
    import subprocess

    gpp = shutil.which("g++") or (r"E:\mingw64\bin\g++.exe"
                                  if os.path.exists(r"E:\mingw64\bin\g++.exe") else None)
    if not gpp:
        return False
    build_script = os.path.join(_HERE, "build_native.py")
    try:
        subprocess.run([sys.executable, build_script], cwd=_HERE,
                       capture_output=True, text=True, timeout=240)
    except Exception:
        return False
    return _dll_path() is not None


class _Lib:
    """cffi 库句柄单例"""
    _ffi = None
    _lib = None

    @classmethod
    def get(cls):
        if cls._lib is not None:
            return cls._ffi, cls._lib
        if not _ensure_dll():
            return None, None
        path = _dll_path()
        if not path:
            return None, None
        try:
            from cffi import FFI
            ffi = FFI()
            ffi.cdef(_CDEF)
            lib = ffi.dlopen(path)
        except Exception:
            return None, None
        cls._ffi, cls._lib = ffi, lib
        return ffi, lib


def _last_error(ffi, lib):
    raw = lib.nc_last_error()
    return ffi.string(raw).decode("utf-8", errors="replace") if raw else "未知原生错误"


class NativePort:
    """与 PyPort 兼容；s/v/m 在首次访问时从 C++ 输出端口惰性拉取（仅输出端口可取）"""

    def __init__(self, ffi, lib, node_handle, port_index, is_output, type_name, name=""):
        self._ffi = ffi
        self._lib = lib
        self._node = node_handle
        self._idx = port_index
        self._is_output = is_output
        self.type = type_name
        self.name = name
        self._fetched = False
        self._s = 0.0
        self._v = []
        self._m = []

    def _ensure_fetched(self):
        if self._fetched or not self._is_output:
            return
        lib, ffi = self._lib, self._ffi
        if self.type == "scalar":
            self._s = float(lib.nc_port_scalar(self._node, self._idx))
        elif self.type == "vector":
            n = lib.nc_port_vec_len(self._node, self._idx)
            if n > 0:
                buf = ffi.new("double[]", n)
                lib.nc_port_vec_copy(self._node, self._idx, buf, n)
                self._v = [float(buf[i]) for i in range(n)]
        elif self.type == "matrix":
            rows = lib.nc_port_mat_rows(self._node, self._idx)
            cols = lib.nc_port_mat_cols(self._node, self._idx)
            total = rows * cols
            if total > 0:
                buf = ffi.new("double[]", total)
                lib.nc_port_mat_copy(self._node, self._idx, buf, total)
                self._m = [[float(buf[r * cols + c]) for c in range(cols)] for r in range(rows)]
        self._fetched = True

    @property
    def s(self):
        self._ensure_fetched()
        return self._s

    @property
    def v(self):
        self._ensure_fetched()
        return self._v

    @property
    def m(self):
        self._ensure_fetched()
        return self._m


class NativeNode:
    """C++ Node 句柄的 Python 包装；图接管后由图负责释放

    端口结构按节点类型固定（VecCreate/MatCreate 除外，由构造参数决定），
    描述符在进程内缓存，避免每个节点都发起多次 cffi 元数据查询。
    """

    _descriptor_cache = {}  # kind -> (input_type_names, output_type_names)

    @classmethod
    def _describe_kind(cls, ffi, lib, kind):
        cached = cls._descriptor_cache.get(kind)
        if cached is not None:
            return cached
        handle = lib.nc_node_new(kind)
        if not handle:
            raise RuntimeError(_last_error(ffi, lib))
        try:
            in_types = tuple(
                _TYPE_NAMES.get(lib.nc_node_input_type(handle, i), "scalar")
                for i in range(lib.nc_node_input_count(handle)))
            out_types = tuple(
                _TYPE_NAMES.get(lib.nc_node_output_type(handle, i), "scalar")
                for i in range(lib.nc_node_output_count(handle)))
        finally:
            lib.nc_node_delete(handle)
        desc = (in_types, out_types)
        cls._descriptor_cache[kind] = desc
        return desc

    def __init__(self, ffi, lib, name, handle, in_types, out_types):
        self._ffi = ffi
        self._lib = lib
        self.name = name
        self._handle = handle
        self._owned_by_graph = False
        self.inputs = [NativePort(ffi, lib, handle, i, False, t)
                       for i, t in enumerate(in_types)]
        self.outputs = [NativePort(ffi, lib, handle, i, True, t)
                        for i, t in enumerate(out_types)]

    def __del__(self):
        try:
            if not self._owned_by_graph and self._handle:
                self._lib.nc_node_delete(self._handle)
        except Exception:
            pass


class NativeGraph:
    """与 PyGraph 接口兼容的 C++ 图包装"""

    def __init__(self, ffi, lib):
        self._ffi = ffi
        self._lib = lib
        self._handle = lib.nc_graph_new()
        self.nodes = []

    def add_node(self, node):
        if not isinstance(node, NativeNode):
            raise RuntimeError("NativeGraph.add_node: 仅接受 NativeNode")
        idx = self._lib.nc_graph_add_node(self._handle, node._handle)
        if idx < 0:
            raise RuntimeError(_last_error(self._ffi, self._lib))
        node._owned_by_graph = True
        self.nodes.append(node)
        return idx

    def connect(self, src_node_idx, src_out, dst_node_idx, dst_in):
        rc = self._lib.nc_graph_connect(self._handle, src_node_idx, src_out,
                                        dst_node_idx, dst_in)
        if rc != 0:
            raise RuntimeError(_last_error(self._ffi, self._lib))

    def execute(self):
        rc = self._lib.nc_graph_execute(self._handle)
        if rc != 0:
            raise RuntimeError(_last_error(self._ffi, self._lib))
        # 输出值在 NativePort.s/v/m 首次访问时惰性拉取，避免全量跨语言拷贝

    def __del__(self):
        try:
            if getattr(self, "_handle", None):
                self._lib.nc_graph_delete(self._handle)
                self._handle = None
        except Exception:
            pass


def _make_generic_node_class(name, kind):
    ffi, lib = _Lib.get()

    class _Node(NativeNode):
        def __init__(self):
            handle = lib.nc_node_new(kind)
            if not handle:
                raise RuntimeError(_last_error(ffi, lib))
            in_types, out_types = NativeNode._describe_kind(ffi, lib, kind)
            super().__init__(ffi, lib, name, handle, in_types, out_types)

    _Node.__name__ = f"Native{name}"
    return _Node


# 结构由构造参数决定的节点（描述符不适合全局缓存）
class _NativeNumber(NativeNode):
    def __init__(self, value):
        ffi, lib = _Lib.get()
        handle = lib.nc_node_new_number(float(value))
        super().__init__(ffi, lib, "Number", handle, (), ("scalar",))


class _NativeLog(NativeNode):
    def __init__(self, base):
        ffi, lib = _Lib.get()
        handle = lib.nc_node_new_log(float(base))
        in_types, out_types = NativeNode._describe_kind(ffi, lib, _KIND["Log"])
        super().__init__(ffi, lib, "Log", handle, in_types, out_types)


class _NativeVecCreate(NativeNode):
    def __init__(self, n):
        ffi, lib = _Lib.get()
        n = int(n)
        handle = lib.nc_node_new_vec(n)
        if not handle:
            raise RuntimeError(_last_error(ffi, lib))
        super().__init__(ffi, lib, "VecCreate", handle,
                         ("vector",) * n, ("vector",))


class _NativeMatCreate(NativeNode):
    def __init__(self, rows, cols):
        ffi, lib = _Lib.get()
        rows, cols = int(rows), int(cols)
        handle = lib.nc_node_new_mat(rows, cols)
        if not handle:
            raise RuntimeError(_last_error(ffi, lib))
        super().__init__(ffi, lib, "MatCreate", handle,
                         ("scalar",) * (rows * cols), ("matrix",))


def register_native_backend(engine) -> bool:
    """把原生节点类与 NativeGraph 绑定到 NodeEngine 单例；失败返回 False"""
    ffi, lib = _Lib.get()
    if lib is None:
        return False

    try:
        for name in _KIND:
            if name == "Number":
                engine.Number = _NativeNumber
            elif name == "Log":
                engine.Log = _NativeLog
            elif name == "VecCreate":
                engine.VecCreate = _NativeVecCreate
            elif name == "MatCreate":
                engine.MatCreate = _NativeMatCreate
            else:
                setattr(engine, name, _make_generic_node_class(name, _KIND[name]))

        def graph_factory():
            f, l = _Lib.get()
            return NativeGraph(f, l)

        engine.Graph = graph_factory
        engine.Port = NativePort
        engine.node_classes = list(_KIND.keys())
    except Exception:
        return False
    return True
