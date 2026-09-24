#!/usr/bin/env python
"""nodecalc 原生后端构建脚本（MinGW g++，无需 cmake/ninja）

职责：
1. 从 src/core/node_engine.py 的 EMBEDDED_CPP 提取 C++ 源码（单一事实来源），
   生成 build/nodecalc.hpp；
2. 用 g++ 编译 nodecalc_capi.cpp -> nodecalc_native.dll（发布版 -O2）；
3. --profile：额外编译 -pg 插桩的 nodecalc_bench.exe，运行后用 gprof 产出热点报告。

用法：
  python src/core/native/build_native.py            # 构建 DLL
  python src/core/native/build_native.py --profile  # 构建并运行 gprof 分析
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(HERE, "build")
HPP_PATH = os.path.join(BUILD_DIR, "nodecalc.hpp")
CAPI_PATH = os.path.join(HERE, "nodecalc_capi.cpp")
DLL_PATH = os.path.join(HERE, "nodecalc_native.dll")
ENGINE_PY = os.path.normpath(os.path.join(HERE, "..", "node_engine.py"))

if platform.system() == "Windows":
    DLL_NAME = "nodecalc_native.dll"
    EXE_NAME = "nodecalc_bench.exe"
    GPP_CANDIDATES = ["g++", r"E:\mingw64\bin\g++.exe"]
else:
    DLL_NAME = "libnodecalc_native.so"
    EXE_NAME = "nodecalc_bench"
    GPP_CANDIDATES = ["g++"]


def find_compiler():
    for cand in GPP_CANDIDATES:
        if os.path.isabs(cand):
            if os.path.exists(cand):
                return cand
        elif shutil.which(cand):
            return cand
    return None


def extract_embedded_cpp():
    """从 node_engine.py 提取 EMBEDDED_CPP = R\"\"\"(... )\"\"\"; 的完整内容"""
    text = open(ENGINE_PY, "r", encoding="utf-8").read()
    m = re.search(r'EMBEDDED_CPP\s*=\s*R"""\(.*?\)""";', text, re.S)
    if not m:
        raise RuntimeError("未能在 node_engine.py 中定位 EMBEDDED_CPP")
    body = m.group(0)
    start = body.index('(') + 1
    end = body.rfind(')"""')
    return body[start:end]


def generate_header():
    os.makedirs(BUILD_DIR, exist_ok=True)
    source = extract_embedded_cpp()
    with open(HPP_PATH, "w", encoding="utf-8") as f:
        f.write("// 由 build_native.py 自动生成，请勿手改。来源：node_engine.EMBEDDED_CPP\n")
        f.write("#pragma once\n")
        f.write(source)
    print(f"[1/3] 已生成 {os.path.relpath(HPP_PATH, HERE)}")


def run(cmd):
    print("    $", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
        raise RuntimeError(f"编译失败（exit {proc.returncode}）")
    return proc


def run_in(cmd, cwd):
    print("    $", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
        raise RuntimeError(f"运行失败（exit {proc.returncode}）")
    return proc


def build_dll(gpp, profile=False):
    out = os.path.join(HERE, DLL_NAME if not profile else "nodecalc_native_pg.dll")
    flags = ["-std=c++17", "-O2", "-DNDEBUG", "-shared"]
    if profile:
        flags.append("-pg")
    if platform.system() == "Windows":
        flags += ["-static", "-static-libgcc", "-static-libstdc++"]
    cmd = [gpp] + flags + [CAPI_PATH, "-o", out]
    run(cmd)
    print(f"[2/3] 已生成 {os.path.relpath(out, HERE)}")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", action="store_true", help="同时生成 -pg 插桩基准并运行 gprof")
    args = parser.parse_args()

    gpp = find_compiler()
    if not gpp:
        print("错误: 未找到 g++（MinGW）。已探测: " + ", ".join(GPP_CANDIDATES))
        sys.exit(2)

    print("=" * 60)
    print("nodecalc 原生后端构建")
    print("=" * 60)
    generate_header()
    build_dll(gpp, profile=False)

    if args.profile:
        _build_and_run_profile(gpp)

    print("[3/3] 完成。Python 侧下次导入 NodeEngine 时自动加载原生 DLL。")


def _build_and_run_profile(gpp):
    """编译 -pg 基准 exe，运行后调用 gprof 输出 flat profile"""
    bench_cpp = os.path.join(BUILD_DIR, "nodecalc_bench_main.cpp")
    bench_exe = os.path.join(BUILD_DIR, EXE_NAME)
    with open(bench_cpp, "w", encoding="utf-8") as f:
        f.write(PROFILE_MAIN)
    run([gpp, "-std=c++17", "-O1", "-fno-inline", "-fno-inline-functions",
         "-pg", "-DNDEBUG", bench_cpp, "-o", bench_exe])
    print("    运行插桩基准 ...")
    bench_proc = run_in([bench_exe], BUILD_DIR)
    gprof = "gprof" if shutil.which("gprof") else os.path.join(os.path.dirname(gpp), "gprof.exe")
    gmon = os.path.join(BUILD_DIR, "gmon.out")
    report = os.path.join(HERE, "gprof_report.txt")
    with open(report, "w", encoding="utf-8") as out:
        proc = subprocess.run([gprof, "-b", bench_exe, gmon], cwd=BUILD_DIR,
                              stdout=out, stderr=subprocess.PIPE, text=True)
        # 部分 MinGW/binutils 版本下 gprof 无法解析自身 gmon.out（报告为空），
        # 追加确定性的阶段计时作为热点证据补充
        out.write("\n\n==== 阶段计时（chrono，-O1 -fno-inline 插桩构建）====\n")
        out.write((bench_proc.stdout or "") + "\n")
        out.write("说明：build=节点图构建（add/connect/对象构造），exec=validate+拓扑+compute\n")
    if proc.returncode != 0:
        print(proc.stderr)
        raise RuntimeError("gprof 分析失败")
    print(f"    gprof 报告: {os.path.relpath(report, HERE)}")


PROFILE_MAIN = r"""
// 热点驱动：反复构建并执行典型节点图（数值/三角/统计/向量节点）
// -pg 插桩供 gprof 使用；同时输出"图构建/图执行"阶段计时，规避部分 MinGW
// 版本下 gprof 无法解析 gmon.out 的工具兼容问题。
#include "nodecalc.hpp"
#include <cstdio>
#include <chrono>
using namespace nodecalc;

// 返回输出节点索引集合（sq/si/pw/c）由 main 端记录
struct RoundResult { size_t sq, si, pw, agg; };

static RoundResult build_round(Graph& g) {
    auto add_num = [&](double v) -> size_t { return g.add_node(new Number(v)); };

    size_t n16 = add_num(16.0);
    size_t sq = g.add_node(new Sqrt());
    g.connect(n16, 0, sq, 0);

    size_t nh = add_num(3.14159265358979323846 / 2.0);
    size_t si = g.add_node(new Sin());
    g.connect(nh, 0, si, 0);

    size_t a2 = add_num(2.0), a3 = add_num(3.0), two = add_num(2.0);
    size_t addi = g.add_node(new Add());
    g.connect(a2, 0, addi, 0);
    g.connect(a3, 0, addi, 1);
    size_t pwi = g.add_node(new Pow());
    g.connect(addi, 0, pwi, 0);
    g.connect(two, 0, pwi, 1);

    const size_t N = 7;
    double data[N] = {5, 1, 3, 2, 4, 9, 7};
    std::vector<size_t> elems;
    for (size_t i = 0; i < N; ++i) elems.push_back(add_num(data[i]));
    size_t vec_idx = g.add_node(new VecCreate(N));
    for (size_t i = 0; i < N; ++i) g.connect(elems[i], 0, vec_idx, i);

    size_t mean_idx = g.add_node(new Mean());   g.connect(vec_idx, 0, mean_idx, 0);
    size_t sd_idx   = g.add_node(new StdDev()); g.connect(vec_idx, 0, sd_idx, 0);
    size_t med_idx  = g.add_node(new Median()); g.connect(vec_idx, 0, med_idx, 0);
    size_t sum_idx  = g.add_node(new VecSum()); g.connect(vec_idx, 0, sum_idx, 0);

    size_t a = g.add_node(new Add()); g.connect(mean_idx, 0, a, 0); g.connect(sd_idx, 0, a, 1);
    size_t b = g.add_node(new Add()); g.connect(a, 0, b, 0);        g.connect(med_idx, 0, b, 1);
    size_t c = g.add_node(new Add()); g.connect(b, 0, c, 0);        g.connect(sum_idx, 0, c, 1);
    return {sq, si, pwi, c};
}

int main() {
    const int ITERS = 100000;
    double acc = 0.0;
    long long build_ns = 0, exec_ns = 0;
    for (int i = 0; i < ITERS; ++i) {
        Graph g;
        auto t0 = std::chrono::high_resolution_clock::now();
        RoundResult r = build_round(g);
        auto t1 = std::chrono::high_resolution_clock::now();
        g.execute();
        auto t2 = std::chrono::high_resolution_clock::now();
        build_ns += std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count();
        exec_ns  += std::chrono::duration_cast<std::chrono::nanoseconds>(t2 - t1).count();
        acc += g.nodes[r.sq]->outputs[0].s + g.nodes[r.si]->outputs[0].s
             + g.nodes[r.pw]->outputs[0].s + g.nodes[r.agg]->outputs[0].s;
        for (auto* n : g.nodes) delete n;
    }
    std::printf("acc=%f iters=%d\n", acc, ITERS);
    std::printf("phase_build_us_per_round=%.3f\n", build_ns / 1000.0 / ITERS);
    std::printf("phase_exec_us_per_round=%.3f\n", exec_ns / 1000.0 / ITERS);
    return 0;
}
"""


if __name__ == "__main__":
    main()
