"""自动化测试套件

本目录提供项目核心模块的自动化测试，覆盖：
- 表达式解析与节点计算引擎（覆盖全部 44 个节点类型）
- 多后端等价性（native / cppyy / python）
- 性能回归（启动、小表达式、大数据量向量统计）

运行方式：
    python auto_tests/run_tests.py                 # 运行全部测试
    python auto_tests/run_tests.py --backend py    # 强制纯 Python 后端
    pytest auto_tests/                             # 用 pytest 运行
"""
