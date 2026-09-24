// nodecalc_capi.cpp
// C ABI 封装层：把 nodecalc C++ 节点图引擎（与 node_engine.EMBEDDED_CPP 同源）
// 暴露为纯 C 接口，供 Python 通过 cffi ABI 模式加载，无需 cppyy/编译器环境。
//
// 构建：见 build_native.py（MinGW g++ -O2 -shared）
#include "build/nodecalc.hpp"

#include <cstring>
#include <string>

#if defined(_WIN32)
#  define NC_API extern "C" __declspec(dllexport)
#else
#  define NC_API extern "C" __attribute__((visibility("default")))
#endif

namespace {
// 与 src/core/node_engine.py::_NODE_CLASS_NAMES 顺序保持一致
enum NcKind {
    NC_NUMBER = 0, NC_VARIABLE = 1,
    NC_ADD = 2, NC_SUB = 3, NC_MUL = 4, NC_DIV = 5, NC_MOD = 6,
    NC_NEGATE = 7, NC_ABS = 8, NC_POW = 9,
    NC_SQRT = 10, NC_CBRT = 11, NC_EXP = 12, NC_LOG = 13,
    NC_LOG2 = 14, NC_LOG10 = 15,
    NC_SIN = 16, NC_COS = 17, NC_TAN = 18,
    NC_ASIN = 19, NC_ACOS = 20, NC_ATAN = 21,
    NC_SINH = 22, NC_COSH = 23, NC_TANH = 24,
    NC_VECCREATE = 25, NC_VECADD = 26, NC_VECDOT = 27, NC_VECNORM = 28, NC_VECSUM = 29,
    NC_MATCREATE = 30, NC_MATMUL = 31, NC_MATTRANSPOSE = 32, NC_MATDET = 33, NC_MATINVERSE = 34,
    NC_SUM = 35, NC_MEAN = 36, NC_STDDEV = 37, NC_MIN = 38, NC_MAX = 39, NC_MEDIAN = 40,
    NC_CLAMP = 41, NC_LERP = 42, NC_IF = 43,
};

thread_local std::string g_last_error;

nodecalc::Node* make_node(int kind) {
    using namespace nodecalc;
    switch (kind) {
        case NC_VARIABLE:  return new Variable("x");
        case NC_ADD:       return new Add();
        case NC_SUB:       return new Sub();
        case NC_MUL:       return new Mul();
        case NC_DIV:       return new Div();
        case NC_MOD:       return new Mod();
        case NC_NEGATE:    return new Negate();
        case NC_ABS:       return new Abs();
        case NC_POW:       return new Pow();
        case NC_SQRT:      return new Sqrt();
        case NC_CBRT:      return new Cbrt();
        case NC_EXP:       return new Exp();
        case NC_LOG:       return new Log();
        case NC_LOG2:      return new Log2();
        case NC_LOG10:     return new Log10();
        case NC_SIN:       return new Sin();
        case NC_COS:       return new Cos();
        case NC_TAN:       return new Tan();
        case NC_ASIN:      return new Asin();
        case NC_ACOS:      return new Acos();
        case NC_ATAN:      return new Atan();
        case NC_SINH:      return new Sinh();
        case NC_COSH:      return new Cosh();
        case NC_TANH:      return new Tanh();
        case NC_VECCREATE: return new VecCreate();
        case NC_VECADD:    return new VecAdd();
        case NC_VECDOT:    return new VecDot();
        case NC_VECNORM:   return new VecNorm();
        case NC_VECSUM:    return new VecSum();
        case NC_MATCREATE: return new MatCreate();
        case NC_MATMUL:    return new MatMul();
        case NC_MATTRANSPOSE: return new MatTranspose();
        case NC_MATDET:    return new MatDet();
        case NC_MATINVERSE:return new MatInverse();
        case NC_SUM:       return new Sum();
        case NC_MEAN:      return new Mean();
        case NC_STDDEV:    return new StdDev();
        case NC_MIN:       return new Min();
        case NC_MAX:       return new Max();
        case NC_MEDIAN:    return new Median();
        case NC_CLAMP:     return new Clamp();
        case NC_LERP:      return new Lerp();
        case NC_IF:        return new If();
        default:           return nullptr;
    }
}

int port_type_to_int(const nodecalc::Port& p) {
    return static_cast<int>(p.type);  // 0=SCALAR 1=VECTOR 2=MATRIX
}
}  // namespace

NC_API const char* nc_last_error() {
    return g_last_error.c_str();
}

// ── 节点生命周期 ────────────────────────────────────────────────────

NC_API void* nc_node_new(int kind) {
    try {
        return static_cast<void*>(make_node(kind));
    } catch (const std::exception& e) {
        g_last_error = e.what();
        return nullptr;
    }
}

NC_API void* nc_node_new_number(double value) {
    return static_cast<void*>(new nodecalc::Number(value));
}

NC_API void* nc_node_new_log(double base) {
    return static_cast<void*>(new nodecalc::Log(base));
}

NC_API void* nc_node_new_vec(int n) {
    if (n < 0) { g_last_error = "VecCreate: negative size"; return nullptr; }
    return static_cast<void*>(new nodecalc::VecCreate(static_cast<size_t>(n)));
}

NC_API void* nc_node_new_mat(int rows, int cols) {
    if (rows <= 0 || cols <= 0) { g_last_error = "MatCreate: invalid dimensions"; return nullptr; }
    return static_cast<void*>(new nodecalc::MatCreate(static_cast<size_t>(rows),
                                                      static_cast<size_t>(cols)));
}

NC_API void nc_node_delete(void* node) {
    delete static_cast<nodecalc::Node*>(node);
}

NC_API int nc_node_input_count(void* node) {
    return static_cast<int>(static_cast<nodecalc::Node*>(node)->inputs.size());
}

NC_API int nc_node_output_count(void* node) {
    return static_cast<int>(static_cast<nodecalc::Node*>(node)->outputs.size());
}

NC_API int nc_node_input_type(void* node, int idx) {
    auto* n = static_cast<nodecalc::Node*>(node);
    if (idx < 0 || static_cast<size_t>(idx) >= n->inputs.size()) return -1;
    return port_type_to_int(n->inputs[idx]);
}

NC_API int nc_node_output_type(void* node, int idx) {
    auto* n = static_cast<nodecalc::Node*>(node);
    if (idx < 0 || static_cast<size_t>(idx) >= n->outputs.size()) return -1;
    return port_type_to_int(n->outputs[idx]);
}

// ── 图 ──────────────────────────────────────────────────────────────

NC_API void* nc_graph_new() {
    return static_cast<void*>(new nodecalc::Graph());
}

NC_API void nc_graph_delete(void* graph) {
    auto* g = static_cast<nodecalc::Graph*>(graph);
    if (g) {
        for (auto* n : g->nodes) delete n;
        delete g;
    }
}

NC_API int nc_graph_add_node(void* graph, void* node) {
    auto* g = static_cast<nodecalc::Graph*>(graph);
    try {
        return static_cast<int>(g->add_node(static_cast<nodecalc::Node*>(node)));
    } catch (const std::exception& e) {
        g_last_error = e.what();
        return -1;
    }
}

NC_API int nc_graph_connect(void* graph, int src_node, int src_out, int dst_node, int dst_in) {
    auto* g = static_cast<nodecalc::Graph*>(graph);
    try {
        g->connect(static_cast<size_t>(src_node), static_cast<size_t>(src_out),
                   static_cast<size_t>(dst_node), static_cast<size_t>(dst_in));
        return 0;
    } catch (const std::exception& e) {
        g_last_error = e.what();
        return 1;
    }
}

NC_API int nc_graph_execute(void* graph) {
    auto* g = static_cast<nodecalc::Graph*>(graph);
    try {
        g->execute();
        return 0;
    } catch (const std::exception& e) {
        g_last_error = e.what();
        return 1;
    }
}

// ── 输出端口读取（执行后调用） ───────────────────────────────────────

NC_API int nc_port_type(void* node, int output_idx) {
    auto* n = static_cast<nodecalc::Node*>(node);
    if (output_idx < 0 || static_cast<size_t>(output_idx) >= n->outputs.size()) return -1;
    return port_type_to_int(n->outputs[output_idx]);
}

NC_API double nc_port_scalar(void* node, int output_idx) {
    return static_cast<nodecalc::Node*>(node)->outputs[output_idx].s;
}

NC_API int nc_port_vec_len(void* node, int output_idx) {
    auto* n = static_cast<nodecalc::Node*>(node);
    if (output_idx < 0 || static_cast<size_t>(output_idx) >= n->outputs.size()) return -1;
    return static_cast<int>(n->outputs[output_idx].v.size());
}

NC_API int nc_port_vec_copy(void* node, int output_idx, double* out, int capacity) {
    auto* n = static_cast<nodecalc::Node*>(node);
    const auto& vec = n->outputs[output_idx].v;
    int count = static_cast<int>(vec.size());
    if (count > capacity) count = capacity;
    for (int i = 0; i < count; ++i) out[i] = vec[i];
    return static_cast<int>(vec.size());
}

NC_API int nc_port_mat_rows(void* node, int output_idx) {
    auto* n = static_cast<nodecalc::Node*>(node);
    return static_cast<int>(n->outputs[output_idx].m.size());
}

NC_API int nc_port_mat_cols(void* node, int output_idx) {
    auto* n = static_cast<nodecalc::Node*>(node);
    const auto& mat = n->outputs[output_idx].m;
    return mat.empty() ? 0 : static_cast<int>(mat[0].size());
}

NC_API int nc_port_mat_copy(void* node, int output_idx, double* out, int capacity) {
    auto* n = static_cast<nodecalc::Node*>(node);
    const auto& mat = n->outputs[output_idx].m;
    int written = 0;
    for (const auto& row : mat) {
        for (double x : row) {
            if (written >= capacity) break;
            out[written++] = x;
        }
    }
    int total = 0;
    for (const auto& row : mat) total += static_cast<int>(row.size());
    return total;
}
