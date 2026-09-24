"""nodecalc 原生后端包

- nodecalc_capi.cpp：C ABI 封装（封装与 node_engine.EMBEDDED_CPP 同源的 C++ 节点引擎）
- build_native.py：MinGW 构建脚本（DLL / gprof 侧写），DLL 缺失时由 native_backend 自动调用
- native_backend.py：cffi 加载与 Graph/Node/Port 兼容层
"""
