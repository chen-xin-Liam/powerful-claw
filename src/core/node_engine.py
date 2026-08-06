#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys
import os
import math
import traceback

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


EMBEDDED_CPP = R"""(
#include <vector>
#include <string>
#include <stdexcept>
#include <cmath>
#include <algorithm>
#include <tuple>
#include <queue>
#include <stack>
#include <cstddef>
#include <limits>
#include <numeric>

namespace nodecalc {

enum class PortType { SCALAR, VECTOR, MATRIX };

struct Port {
    PortType type;
    double s;
    std::vector<double> v;
    std::vector<std::vector<double>> m;
    std::string name;
    Port(PortType t, std::string n) : type(t), name(n), s(0) {}
};

class Node {
public:
    std::string name;
    std::vector<Port> inputs;
    std::vector<Port> outputs;
    virtual ~Node() = default;
    virtual void compute() = 0;

    void connect_input(size_t dst_in_idx, Node* src, size_t src_out_idx) {
        if (dst_in_idx >= inputs.size()) {
            throw std::runtime_error("connect_input: dst_in_idx out of range");
        }
        if (!src) {
            throw std::runtime_error("connect_input: src node is null");
        }
        if (src_out_idx >= src->outputs.size()) {
            throw std::runtime_error("connect_input: src_out_idx out of range");
        }
        Port& dst = inputs[dst_in_idx];
        const Port& srcp = src->outputs[src_out_idx];
        if (dst.type != srcp.type) {
            throw std::runtime_error("connect_input: type mismatch");
        }
        switch (dst.type) {
            case PortType::SCALAR:
                dst.s = srcp.s;
                break;
            case PortType::VECTOR:
                dst.v = srcp.v;
                break;
            case PortType::MATRIX:
                dst.m = srcp.m;
                break;
        }
    }
};

class Graph {
public:
    std::vector<Node*> nodes;
    std::vector<std::tuple<size_t, size_t, size_t, size_t>> edges;

    size_t add_node(Node* n) {
        if (!n) {
            throw std::runtime_error("Graph add_node: null node");
        }
        nodes.push_back(n);
        return nodes.size() - 1;
    }

    void connect(size_t src_node_idx, size_t src_out, size_t dst_node_idx, size_t dst_in) {
        edges.emplace_back(src_node_idx, src_out, dst_node_idx, dst_in);
    }

    void validate() {
        for (size_t i = 0; i < edges.size(); ++i) {
            size_t src_n = std::get<0>(edges[i]);
            size_t src_o = std::get<1>(edges[i]);
            size_t dst_n = std::get<2>(edges[i]);
            size_t dst_i = std::get<3>(edges[i]);
            if (dst_n >= nodes.size()) {
                throw std::runtime_error("Graph validate: dst_node_idx out of range");
            }
            if (dst_i >= nodes[dst_n]->inputs.size()) {
                throw std::runtime_error("Graph validate: input out of range");
            }
            if (src_n >= nodes.size()) {
                throw std::runtime_error("Graph validate: src_node_idx out of range");
            }
            if (src_o >= nodes[src_n]->outputs.size()) {
                throw std::runtime_error("Graph validate: src output out of range");
            }
        }

        size_t n = nodes.size();
        std::vector<int> color(n, 0);
        std::vector<size_t> parent(n, (size_t)-1);
        std::stack<std::pair<size_t, size_t>> stk;
        for (size_t s = 0; s < n; ++s) {
            if (color[s] == 0) {
                stk.push({s, 0});
                while (!stk.empty()) {
                    size_t u = stk.top().first;
                    size_t& ei = stk.top().second;
                    color[u] = 1;
                    std::vector<size_t> out_edges_idx;
                    for (size_t k = 0; k < edges.size(); ++k) {
                        if (std::get<0>(edges[k]) == u) {
                            out_edges_idx.push_back(k);
                        }
                    }
                    bool found = false;
                    while (ei < out_edges_idx.size()) {
                        size_t v = std::get<2>(edges[out_edges_idx[ei]]);
                        ei++;
                        stk.top().second = ei;
                        if (color[v] == 1) {
                            std::vector<std::string> path;
                            path.push_back(nodes[v]->name);
                            size_t cur = u;
                            while (cur != v && cur != (size_t)-1) {
                                path.push_back(nodes[cur]->name);
                                cur = parent[cur];
                            }
                            path.push_back(nodes[v]->name);
                            std::reverse(path.begin(), path.end());
                            std::string msg = "Graph validate: cycle detected: ";
                            for (size_t pi = 0; pi < path.size(); ++pi) {
                                if (pi > 0) msg += " -> ";
                                msg += path[pi];
                            }
                            throw std::runtime_error(msg);
                        } else if (color[v] == 0) {
                            parent[v] = u;
                            stk.push({v, 0});
                            found = true;
                            break;
                        }
                    }
                    if (!found) {
                        color[u] = 2;
                        stk.pop();
                    }
                }
            }
        }

        std::vector<size_t> in_degree(n, 0);
        std::vector<std::vector<size_t>> adj(n);
        for (size_t i = 0; i < edges.size(); ++i) {
            size_t u = std::get<0>(edges[i]);
            size_t v = std::get<2>(edges[i]);
            adj[u].push_back(v);
            in_degree[v]++;
        }
        std::queue<size_t> q;
        for (size_t i = 0; i < n; ++i) {
            if (in_degree[i] == 0) q.push(i);
        }
        topo_order_.clear();
        while (!q.empty()) {
            size_t u = q.front();
            q.pop();
            topo_order_.push_back(u);
            for (size_t v : adj[u]) {
                if (--in_degree[v] == 0) q.push(v);
            }
        }
        if (topo_order_.size() != n) {
            throw std::runtime_error("Graph validate: topo sort failed");
        }
    }

    void execute() {
        validate();
        for (size_t step = 0; step < topo_order_.size(); ++step) {
            size_t i = topo_order_[step];
            for (size_t k = 0; k < edges.size(); ++k) {
                if (std::get<2>(edges[k]) == i) {
                    size_t src_n = std::get<0>(edges[k]);
                    size_t src_o = std::get<1>(edges[k]);
                    size_t dst_i = std::get<3>(edges[k]);
                    nodes[i]->connect_input(dst_i, nodes[src_n], src_o);
                }
            }
            try {
                nodes[i]->compute();
            } catch (const std::runtime_error& e) {
                std::string msg = std::string("[") + nodes[i]->name + std::string("] ") + e.what();
                throw std::runtime_error(msg);
            }
        }
    }

private:
    std::vector<size_t> topo_order_;
};

// ========== 算术节点 9 个 ==========

class Number : public Node {
public:
    Number(double v) {
        name = "Number";
        outputs.emplace_back(PortType::SCALAR, "out");
        outputs.back().s = v;
    }
    void compute() override {}
};

class Variable : public Node {
public:
    Variable(std::string n = "x") {
        name = "Variable";
        inputs.emplace_back(PortType::SCALAR, "value");
        inputs.back().s = 0.0;
        outputs.emplace_back(PortType::SCALAR, "out");
        outputs.back().name = n;
    }
    void compute() override {
        outputs[0].s = inputs[0].s;
    }
};

class Add : public Node {
public:
    Add() {
        name = "Add";
        inputs.emplace_back(PortType::SCALAR, "a");
        inputs.emplace_back(PortType::SCALAR, "b");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = inputs[0].s + inputs[1].s;
    }
};

class Sub : public Node {
public:
    Sub() {
        name = "Sub";
        inputs.emplace_back(PortType::SCALAR, "a");
        inputs.emplace_back(PortType::SCALAR, "b");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = inputs[0].s - inputs[1].s;
    }
};

class Mul : public Node {
public:
    Mul() {
        name = "Mul";
        inputs.emplace_back(PortType::SCALAR, "a");
        inputs.emplace_back(PortType::SCALAR, "b");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = inputs[0].s * inputs[1].s;
    }
};

class Div : public Node {
public:
    Div() {
        name = "Div";
        inputs.emplace_back(PortType::SCALAR, "a");
        inputs.emplace_back(PortType::SCALAR, "b");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[1].s == 0.0) {
            throw std::runtime_error("Div: division by zero");
        }
        outputs[0].s = inputs[0].s / inputs[1].s;
    }
};

class Mod : public Node {
public:
    Mod() {
        name = "Mod";
        inputs.emplace_back(PortType::SCALAR, "a");
        inputs.emplace_back(PortType::SCALAR, "b");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[1].s == 0.0) {
            throw std::runtime_error("Mod: division by zero");
        }
        outputs[0].s = std::fmod(inputs[0].s, inputs[1].s);
    }
};

class Negate : public Node {
public:
    Negate() {
        name = "Negate";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = -inputs[0].s;
    }
};

class Abs : public Node {
public:
    Abs() {
        name = "Abs";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::fabs(inputs[0].s);
    }
};

// ========== 幂根节点 7 个 ==========

class Pow : public Node {
public:
    Pow() {
        name = "Pow";
        inputs.emplace_back(PortType::SCALAR, "a");
        inputs.emplace_back(PortType::SCALAR, "b");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::pow(inputs[0].s, inputs[1].s);
    }
};

class Sqrt : public Node {
public:
    Sqrt() {
        name = "Sqrt";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].s < 0.0) {
            throw std::runtime_error("Sqrt: x < 0");
        }
        outputs[0].s = std::sqrt(inputs[0].s);
    }
};

class Cbrt : public Node {
public:
    Cbrt() {
        name = "Cbrt";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::cbrt(inputs[0].s);
    }
};

class Exp : public Node {
public:
    Exp() {
        name = "Exp";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::exp(inputs[0].s);
    }
};

class Log : public Node {
public:
    Log(double base = 2.718281828459045) : base_(base) {
        if (base <= 0.0 || base == 1.0) {
            throw std::runtime_error("Log: invalid base");
        }
        name = "Log";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].s <= 0.0) {
            throw std::runtime_error("Log: x <= 0");
        }
        outputs[0].s = std::log(inputs[0].s) / std::log(base_);
    }
private:
    double base_;
};

class Log2 : public Node {
public:
    Log2() {
        name = "Log2";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].s <= 0.0) {
            throw std::runtime_error("Log2: x <= 0");
        }
        outputs[0].s = std::log2(inputs[0].s);
    }
};

class Log10 : public Node {
public:
    Log10() {
        name = "Log10";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].s <= 0.0) {
            throw std::runtime_error("Log10: x <= 0");
        }
        outputs[0].s = std::log10(inputs[0].s);
    }
};

// ========== 三角节点 9 个 ==========

class Sin : public Node {
public:
    Sin() {
        name = "Sin";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::sin(inputs[0].s);
    }
};

class Cos : public Node {
public:
    Cos() {
        name = "Cos";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::cos(inputs[0].s);
    }
};

class Tan : public Node {
public:
    Tan() {
        name = "Tan";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::tan(inputs[0].s);
    }
};

class Asin : public Node {
public:
    Asin() {
        name = "Asin";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].s < -1.0 || inputs[0].s > 1.0) {
            throw std::runtime_error("Asin: x out of domain [-1,1]");
        }
        outputs[0].s = std::asin(inputs[0].s);
    }
};

class Acos : public Node {
public:
    Acos() {
        name = "Acos";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].s < -1.0 || inputs[0].s > 1.0) {
            throw std::runtime_error("Acos: x out of domain [-1,1]");
        }
        outputs[0].s = std::acos(inputs[0].s);
    }
};

class Atan : public Node {
public:
    Atan() {
        name = "Atan";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::atan(inputs[0].s);
    }
};

class Sinh : public Node {
public:
    Sinh() {
        name = "Sinh";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::sinh(inputs[0].s);
    }
};

class Cosh : public Node {
public:
    Cosh() {
        name = "Cosh";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::cosh(inputs[0].s);
    }
};

class Tanh : public Node {
public:
    Tanh() {
        name = "Tanh";
        inputs.emplace_back(PortType::SCALAR, "x");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = std::tanh(inputs[0].s);
    }
};

// ========== 向量节点 5 个 ==========

class VecCreate : public Node {
public:
    VecCreate(size_t n = 3) : n_(n) {
        if (n < 1) {
            throw std::runtime_error("VecCreate: n must be >= 1");
        }
        name = "VecCreate";
        for (size_t i = 0; i < n; ++i) {
            inputs.emplace_back(PortType::SCALAR, std::string("s") + std::to_string(i));
        }
        outputs.emplace_back(PortType::VECTOR, "out");
    }
    void compute() override {
        outputs[0].v.resize(n_);
        for (size_t i = 0; i < n_; ++i) {
            outputs[0].v[i] = inputs[i].s;
        }
    }
private:
    size_t n_;
};

class VecAdd : public Node {
public:
    VecAdd() {
        name = "VecAdd";
        inputs.emplace_back(PortType::VECTOR, "a");
        inputs.emplace_back(PortType::VECTOR, "b");
        outputs.emplace_back(PortType::VECTOR, "out");
    }
    void compute() override {
        if (inputs[0].v.size() != inputs[1].v.size()) {
            throw std::runtime_error("VecAdd: vector size mismatch");
        }
        size_t n = inputs[0].v.size();
        outputs[0].v.resize(n);
        for (size_t i = 0; i < n; ++i) {
            outputs[0].v[i] = inputs[0].v[i] + inputs[1].v[i];
        }
    }
};

class VecDot : public Node {
public:
    VecDot() {
        name = "VecDot";
        inputs.emplace_back(PortType::VECTOR, "a");
        inputs.emplace_back(PortType::VECTOR, "b");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].v.size() != inputs[1].v.size()) {
            throw std::runtime_error("VecDot: vector size mismatch");
        }
        double sum = 0.0;
        for (size_t i = 0; i < inputs[0].v.size(); ++i) {
            sum += inputs[0].v[i] * inputs[1].v[i];
        }
        outputs[0].s = sum;
    }
};

class VecNorm : public Node {
public:
    VecNorm() {
        name = "VecNorm";
        inputs.emplace_back(PortType::VECTOR, "v");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        double sum = 0.0;
        for (double x : inputs[0].v) {
            sum += x * x;
        }
        outputs[0].s = std::sqrt(sum);
    }
};

class VecSum : public Node {
public:
    VecSum() {
        name = "VecSum";
        inputs.emplace_back(PortType::VECTOR, "v");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        double sum = 0.0;
        for (double x : inputs[0].v) {
            sum += x;
        }
        outputs[0].s = sum;
    }
};

// ========== 辅助：LU 分解带部分选主元 ==========
static bool _lu_decompose(std::vector<std::vector<double>>& A, std::vector<size_t>& P, int& sign) {
    size_t n = A.size();
    P.resize(n);
    for (size_t i = 0; i < n; ++i) P[i] = i;
    sign = 1;
    for (size_t k = 0; k < n; ++k) {
        double max_val = std::fabs(A[k][k]);
        size_t max_row = k;
        for (size_t i = k + 1; i < n; ++i) {
            if (std::fabs(A[i][k]) > max_val) {
                max_val = std::fabs(A[i][k]);
                max_row = i;
            }
        }
        if (max_val < 1e-15) {
            return false;
        }
        if (max_row != k) {
            std::swap(A[k], A[max_row]);
            std::swap(P[k], P[max_row]);
            sign = -sign;
        }
        for (size_t i = k + 1; i < n; ++i) {
            A[i][k] /= A[k][k];
            for (size_t j = k + 1; j < n; ++j) {
                A[i][j] -= A[i][k] * A[k][j];
            }
        }
    }
    return true;
}

static std::vector<double> _lu_solve(const std::vector<std::vector<double>>& LU, const std::vector<size_t>& P, std::vector<double> b) {
    size_t n = LU.size();
    std::vector<double> Pb(n);
    for (size_t i = 0; i < n; ++i) Pb[i] = b[P[i]];
    std::vector<double> y(n);
    for (size_t i = 0; i < n; ++i) {
        y[i] = Pb[i];
        for (size_t j = 0; j < i; ++j) {
            y[i] -= LU[i][j] * y[j];
        }
    }
    std::vector<double> x(n);
    for (size_t i = n; i-- > 0;) {
        x[i] = y[i];
        for (size_t j = i + 1; j < n; ++j) {
            x[i] -= LU[i][j] * x[j];
        }
        x[i] /= LU[i][i];
    }
    return x;
}

// ========== 矩阵节点 5 个 ==========

class MatCreate : public Node {
public:
    MatCreate(size_t rows = 2, size_t cols = 2) : rows_(rows), cols_(cols) {
        if (rows < 1 || cols < 1) {
            throw std::runtime_error("MatCreate: rows/cols must be >= 1");
        }
        name = "MatCreate";
        for (size_t i = 0; i < rows * cols; ++i) {
            inputs.emplace_back(PortType::SCALAR, std::string("e") + std::to_string(i));
        }
        outputs.emplace_back(PortType::MATRIX, "out");
    }
    void compute() override {
        outputs[0].m.resize(rows_);
        for (size_t i = 0; i < rows_; ++i) {
            outputs[0].m[i].resize(cols_);
            for (size_t j = 0; j < cols_; ++j) {
                outputs[0].m[i][j] = inputs[i * cols_ + j].s;
            }
        }
    }
private:
    size_t rows_;
    size_t cols_;
};

class MatMul : public Node {
public:
    MatMul() {
        name = "MatMul";
        inputs.emplace_back(PortType::MATRIX, "A");
        inputs.emplace_back(PortType::MATRIX, "B");
        outputs.emplace_back(PortType::MATRIX, "C");
    }
    void compute() override {
        const auto& A = inputs[0].m;
        const auto& B = inputs[1].m;
        if (A.empty() || B.empty()) {
            throw std::runtime_error("MatMul: empty matrix");
        }
        size_t N = A.size();
        size_t K = A[0].size();
        size_t M = B[0].size();
        if (B.size() != K) {
            throw std::runtime_error("MatMul: K dimension mismatch");
        }
        outputs[0].m.assign(N, std::vector<double>(M, 0.0));
        for (size_t i = 0; i < N; ++i) {
            for (size_t k = 0; k < K; ++k) {
                double a = A[i][k];
                for (size_t j = 0; j < M; ++j) {
                    outputs[0].m[i][j] += a * B[k][j];
                }
            }
        }
    }
};

class MatTranspose : public Node {
public:
    MatTranspose() {
        name = "MatTranspose";
        inputs.emplace_back(PortType::MATRIX, "A");
        outputs.emplace_back(PortType::MATRIX, "AT");
    }
    void compute() override {
        const auto& A = inputs[0].m;
        if (A.empty()) {
            throw std::runtime_error("MatTranspose: empty matrix");
        }
        size_t rows = A.size();
        size_t cols = A[0].size();
        outputs[0].m.assign(cols, std::vector<double>(rows));
        for (size_t i = 0; i < rows; ++i) {
            for (size_t j = 0; j < cols; ++j) {
                outputs[0].m[j][i] = A[i][j];
            }
        }
    }
};

class MatDet : public Node {
public:
    MatDet() {
        name = "MatDet";
        inputs.emplace_back(PortType::MATRIX, "A");
        outputs.emplace_back(PortType::SCALAR, "det");
    }
    void compute() override {
        const auto& A = inputs[0].m;
        if (A.empty()) {
            throw std::runtime_error("MatDet: empty matrix");
        }
        size_t n = A.size();
        for (size_t i = 0; i < n; ++i) {
            if (A[i].size() != n) {
                throw std::runtime_error("MatDet: matrix is not square");
            }
        }
        auto LU = A;
        std::vector<size_t> P;
        int sign;
        if (!_lu_decompose(LU, P, sign)) {
            outputs[0].s = 0.0;
            return;
        }
        double det = sign;
        for (size_t i = 0; i < n; ++i) {
            det *= LU[i][i];
        }
        outputs[0].s = det;
    }
};

class MatInverse : public Node {
public:
    MatInverse() {
        name = "MatInverse";
        inputs.emplace_back(PortType::MATRIX, "A");
        outputs.emplace_back(PortType::MATRIX, "Ainv");
    }
    void compute() override {
        const auto& A = inputs[0].m;
        if (A.empty()) {
            throw std::runtime_error("MatInverse: empty matrix");
        }
        size_t n = A.size();
        for (size_t i = 0; i < n; ++i) {
            if (A[i].size() != n) {
                throw std::runtime_error("MatInverse: matrix is not square");
            }
        }
        auto LU = A;
        std::vector<size_t> P;
        int sign;
        if (!_lu_decompose(LU, P, sign)) {
            throw std::runtime_error("MatInverse: singular matrix");
        }
        outputs[0].m.assign(n, std::vector<double>(n));
        for (size_t col = 0; col < n; ++col) {
            std::vector<double> e(n, 0.0);
            e[col] = 1.0;
            std::vector<double> x = _lu_solve(LU, P, e);
            for (size_t row = 0; row < n; ++row) {
                outputs[0].m[row][col] = x[row];
            }
        }
    }
};

// ========== 统计节点 6 个 ==========

class Sum : public Node {
public:
    Sum() {
        name = "Sum";
        inputs.emplace_back(PortType::VECTOR, "data");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        double sum = 0.0;
        for (double x : inputs[0].v) sum += x;
        outputs[0].s = sum;
    }
};

class Mean : public Node {
public:
    Mean() {
        name = "Mean";
        inputs.emplace_back(PortType::VECTOR, "data");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        size_t n = inputs[0].v.size();
        if (n < 1) {
            throw std::runtime_error("Mean: empty data");
        }
        double sum = 0.0;
        for (double x : inputs[0].v) sum += x;
        outputs[0].s = sum / n;
    }
};

class StdDev : public Node {
public:
    StdDev() {
        name = "StdDev";
        inputs.emplace_back(PortType::VECTOR, "data");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        size_t n = inputs[0].v.size();
        if (n < 1) {
            throw std::runtime_error("StdDev: n < 1");
        }
        double sum = 0.0;
        for (double x : inputs[0].v) sum += x;
        double mean = sum / n;
        double var = 0.0;
        for (double x : inputs[0].v) {
            double d = x - mean;
            var += d * d;
        }
        var /= n;
        outputs[0].s = std::sqrt(var);
    }
};

class Min : public Node {
public:
    Min() {
        name = "Min";
        inputs.emplace_back(PortType::VECTOR, "data");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].v.empty()) {
            throw std::runtime_error("Min: empty data");
        }
        double m = inputs[0].v[0];
        for (double x : inputs[0].v) {
            if (x < m) m = x;
        }
        outputs[0].s = m;
    }
};

class Max : public Node {
public:
    Max() {
        name = "Max";
        inputs.emplace_back(PortType::VECTOR, "data");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].v.empty()) {
            throw std::runtime_error("Max: empty data");
        }
        double m = inputs[0].v[0];
        for (double x : inputs[0].v) {
            if (x > m) m = x;
        }
        outputs[0].s = m;
    }
};

class Median : public Node {
public:
    Median() {
        name = "Median";
        inputs.emplace_back(PortType::VECTOR, "data");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        size_t n = inputs[0].v.size();
        if (n < 1) {
            throw std::runtime_error("Median: empty data");
        }
        std::vector<double> tmp = inputs[0].v;
        if (n % 2 == 1) {
            size_t k = n / 2;
            std::nth_element(tmp.begin(), tmp.begin() + k, tmp.end());
            outputs[0].s = tmp[k];
        } else {
            size_t k1 = n / 2 - 1;
            size_t k2 = n / 2;
            std::nth_element(tmp.begin(), tmp.begin() + k1, tmp.end());
            double v1 = tmp[k1];
            std::nth_element(tmp.begin(), tmp.begin() + k2, tmp.end());
            double v2 = tmp[k2];
            outputs[0].s = (v1 + v2) / 2.0;
        }
    }
};

// ========== 特殊节点 3 个 ==========

class Clamp : public Node {
public:
    Clamp() {
        name = "Clamp";
        inputs.emplace_back(PortType::SCALAR, "v");
        inputs.emplace_back(PortType::SCALAR, "lo");
        inputs.emplace_back(PortType::SCALAR, "hi");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        double v = inputs[0].s;
        double lo = inputs[1].s;
        double hi = inputs[2].s;
        if (lo > hi) {
            throw std::runtime_error("Clamp: lo > hi");
        }
        if (v < lo) v = lo;
        else if (v > hi) v = hi;
        outputs[0].s = v;
    }
};

class Lerp : public Node {
public:
    Lerp() {
        name = "Lerp";
        inputs.emplace_back(PortType::SCALAR, "a");
        inputs.emplace_back(PortType::SCALAR, "b");
        inputs.emplace_back(PortType::SCALAR, "t");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        outputs[0].s = inputs[0].s + inputs[2].s * (inputs[1].s - inputs[0].s);
    }
};

class If : public Node {
public:
    If() {
        name = "If";
        inputs.emplace_back(PortType::SCALAR, "cond");
        inputs.emplace_back(PortType::SCALAR, "a");
        inputs.emplace_back(PortType::SCALAR, "b");
        outputs.emplace_back(PortType::SCALAR, "out");
    }
    void compute() override {
        if (inputs[0].s != 0.0) {
            outputs[0].s = inputs[1].s;
        } else {
            outputs[0].s = inputs[2].s;
        }
    }
};

} // namespace nodecalc
)""";


_NODE_CLASS_NAMES = [
    "Number", "Variable",
    "Add", "Sub", "Mul", "Div", "Mod", "Negate", "Abs",
    "Pow", "Sqrt", "Cbrt", "Exp", "Log", "Log2", "Log10",
    "Sin", "Cos", "Tan", "Asin", "Acos", "Atan", "Sinh", "Cosh", "Tanh",
    "VecCreate", "VecAdd", "VecDot", "VecNorm", "VecSum",
    "MatCreate", "MatMul", "MatTranspose", "MatDet", "MatInverse",
    "Sum", "Mean", "StdDev", "Min", "Max", "Median",
    "Clamp", "Lerp", "If",
]

_ALL_CLASS_NAMES = _NODE_CLASS_NAMES + ["Port", "PortType", "Node", "Graph"]


class NodeEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        try:
            import cppyy
            self._cppyy = cppyy
        except ImportError:
            from src.utils.errors import ExternalDependencyError
            from src.utils.error_codes import ErrorCode
            raise ExternalDependencyError(
                ErrorCode.E_EXT_DEPENDENCY_MISSING,
                "cppyy",
                module="src.core.node_engine",
                suggestion="pip install cppyy"
            )

        try:
            self._cppyy.cppdef(EMBEDDED_CPP)
        except Exception as e:
            from src.utils.errors import ExternalDependencyError
            from src.utils.error_codes import ErrorCode
            err_lines = str(e).splitlines()
            summary = " | ".join(err_lines[:3]) if err_lines else str(e)[:200]
            raise ExternalDependencyError(
                ErrorCode.E_EXT_DEPENDENCY_MISSING,
                f"cppyy C++ 编译失败: {summary}",
                module="src.core.node_engine",
                suggestion="请检查 EMBEDDED_CPP 中的 C++ 语法或更新 cppyy 到最新版"
            )

        for name in _ALL_CLASS_NAMES:
            cls_obj = getattr(self._cppyy.gbl.nodecalc, name)
            setattr(self, name, cls_obj)

        self.node_classes = _NODE_CLASS_NAMES.copy()


def execute_graph(g):
    from src.utils.errors import AppError
    from src.utils.error_codes import ErrorCode
    engine = NodeEngine()
    try:
        g.execute()
    except Exception as e:
        msg = str(e)
        node_name = ""
        if msg.startswith("["):
            end = msg.find("]")
            if end > 0:
                node_name = msg[1:end]
        raise AppError(
            ErrorCode.E_VALIDATION_MATH_ERROR,
            f"节点图执行错误: {msg}",
            details={
                "reason": msg,
                "node_name": node_name,
            },
            cause=e,
            module="src.core.node_engine",
        ) from e


def make_graph(*nodes):
    engine = NodeEngine()
    g = engine.Graph()
    for n in nodes:
        g.add_node(n)
    return g


def quick_add(g, *nodes):
    indices = []
    for n in nodes:
        indices.append(g.add_node(n))
    return indices
