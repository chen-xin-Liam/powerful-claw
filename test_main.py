#!/usr/bin/env python
"""
AIclaw 主程序测试脚本
验证所有核心功能模块是否正常工作
"""

import sys
import os
import traceback
import importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 复用项目的统一异常体系，使测试输出的错误信息与正式运行一致
try:
    from utils.errors import AppError, get_suggestion
    from utils.error_codes import ErrorCode
    _HAS_APP_ERROR = True
except Exception:
    # 兜底：基础设施不可用时也能跑测试
    _HAS_APP_ERROR = False

    class AppError(Exception):  # type: ignore
        pass

    def get_suggestion(_code):
        return "请查看日志文件获取详细信息"


# ───────── pip 依赖库检查 ─────────

# 包名 → import 名 的映射（处理特殊命名的包）
# 未在此表中的包，默认将包名中的 "-" 替换为 "_" 作为 import 名
_PACKAGE_IMPORT_MAP = {
    "opencv-python":       "cv2",
    "pillow":              "PIL",
    "pydantic-settings":   "pydantic_settings",
    "python-dotenv":       "dotenv",
    "python-docx":         "docx",
    "python-pptx":         "pptx",
    "python-multipart":    "multipart",
    "python-rapidjson":    "rapidjson",
    "python-dateutil":     "dateutil",
    "pandas-ta":           "pandas_ta",
    "pyyaml":              "yaml",
    "pywinstyles":         "pywinstyles",
    "line-profiler":       "line_profiler",
    "memory-profiler":    "memory_profiler",
    "pre-commit":          "pre_commit",
    "async-timeout":       "async_timeout",
    "nest-asyncio":        "nest_asyncio",
    "argon2-cffi":        "argon2",
    "PyPDF2":              "PyPDF2",
    "PyMuPDF":             "fitz",
}

# 程序启动/核心功能必需的依赖（缺失则视为测试失败）
# 其余 requirements.txt 中的包为可选功能依赖，缺失只警告不阻断
_CORE_PACKAGES = {
    "openai", "pyautogui", "pyperclip", "keyboard", "requests",
    "markdown2", "ultralytics", "pillow", "opencv-python", "tenacity",
    "pydantic", "pydantic-settings", "python-dotenv", "colorama",
    "customtkinter", "pystray", "pywinstyles", "pexpect", "plumbum",
    "sqlalchemy", "psutil", "cattrs", "pyyaml",
}


def _get_import_name(pkg_name: str) -> str:
    """根据包名获取对应的 import 名。"""
    return _PACKAGE_IMPORT_MAP.get(pkg_name, pkg_name.replace("-", "_"))


def _is_package_installed(import_name: str) -> bool:
    """检查包是否已安装（用 find_spec，不触发 import 副作用）。"""
    try:
        return importlib.util.find_spec(import_name) is not None
    except (ImportError, ValueError):
        return False


def test_pip_dependencies(file_path: str = None, strict: bool = None):
    """检查 pip 依赖库安装情况，缺失时给出 pip install 提示。

    参数:
        file_path: 依赖列表 txt 文件路径。None 时默认读取项目根目录的 requirements.txt。
                   支持标准 requirements.txt 格式（含版本约束、类别注释、行内注释），
                   也支持纯包名列表（每行一个包名，无版本约束）。
        strict:    是否严格模式。True 时所有缺失都视为失败；
                   False 时按 _CORE_PACKAGES 分级（核心缺失失败、可选缺失警告）；
                   None（默认）时自动判断：requirements.txt 用分级，自定义文件用严格模式。

    返回:
        True 表示所有必须的依赖均已安装，False 表示有缺失。
    """
    print("=== 测试 pip 依赖库 ===")
    is_default_requirements = False
    if file_path is None:
        file_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
        is_default_requirements = True
    else:
        # 支持相对路径（相对于脚本所在目录解析）
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        # 识别是否为 requirements.txt（大小写不敏感，按 basename 判断）
        is_default_requirements = os.path.basename(file_path).lower() == "requirements.txt"

    # strict 默认值：requirements.txt 用分级，自定义文件用严格模式
    if strict is None:
        strict = not is_default_requirements

    if not os.path.isfile(file_path):
        print(f"⚠ 未找到依赖列表文件: {file_path}")
        print("  用法: python test_main.py --deps <依赖文件路径>")
        return False

    mode_label = "严格模式（全部必须）" if strict else "分级模式（核心必须 / 可选警告）"
    print(f"依赖列表: {file_path}  [{mode_label}]")

    missing_core = []          # 缺失的必须依赖（缺失则失败）
    missing_optional = {}      # 缺失的可选依赖（按类别汇总，仅警告，仅 strict=False 时使用）
    installed_count = 0
    total = 0
    current_category = "其他"

    # 单次遍历：识别类别注释 + 解析包名 + 检查安装
    with open(file_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            # 跳过空行
            if not stripped:
                continue
            # 类别注释行（# 开头）
            if stripped.startswith("#"):
                category = stripped.lstrip("# ").strip()
                if category:  # 非空注释作为类别
                    current_category = category
                continue
            # 去掉行内注释
            line = stripped.split(" #", 1)[0].strip()
            # 解析包名（去掉版本约束）
            pkg_name = line
            for sep in (">=", "<=", "==", "~=", ">", "<", "!=", "==="):
                if sep in pkg_name:
                    pkg_name = pkg_name.split(sep, 1)[0]
                    break
            pkg_name = pkg_name.strip()
            # 去掉 extras（如 package[extra]）
            if "[" in pkg_name:
                pkg_name = pkg_name.split("[", 1)[0]
            if not pkg_name:
                continue

            total += 1
            import_name = _get_import_name(pkg_name)
            if _is_package_installed(import_name):
                installed_count += 1
            else:
                # 严格模式：全部视为必须；分级模式：按 _CORE_PACKAGES 判断
                if strict or pkg_name in _CORE_PACKAGES:
                    missing_core.append(pkg_name)
                else:
                    missing_optional.setdefault(current_category, []).append(pkg_name)

    print(f"已检查 {total} 个包，已安装 {installed_count} 个")

    # 必须依赖缺失：给出 pip install 命令
    if missing_core:
        label = "依赖" if strict else "核心依赖"
        print(f"\n✗ {label}缺失（{len(missing_core)} 个，必须安装）:")
        for pkg in missing_core:
            print(f"  - {pkg}")
        print("\n  安装命令（一次性安装全部缺失）:")
        print(f"    pip install {' '.join(missing_core)}")
        if is_default_requirements:
            print("\n  或安装全部依赖:")
            print("    pip install -r requirements.txt")
        else:
            # 自定义文件：提供从文件安装的命令
            print(f"\n  或从依赖列表文件安装:")
            print(f"    pip install -r {file_path}")
        if _HAS_APP_ERROR:
            print(f"\n  建议: {get_suggestion(ErrorCode.E_SERVICE_DEPENDENCY_MISSING)}")

    # 可选依赖缺失：仅警告（仅 strict=False 时）
    if missing_optional:
        total_optional = sum(len(v) for v in missing_optional.values())
        print(f"\n⚠ 可选依赖缺失（{total_optional} 个，仅影响对应功能）:")
        for category, pkgs in missing_optional.items():
            preview = ', '.join(pkgs[:5])
            suffix = " ..." if len(pkgs) > 5 else ""
            print(f"  [{category}] 缺失 {len(pkgs)} 个: {preview}{suffix}")
        print("\n  如需使用对应功能，安装命令:")
        print("    pip install -r requirements.txt")

    if not missing_core:
        if strict:
            print("✓ 所有依赖已安装")
        else:
            print("✓ 所有核心依赖已安装")
            if not missing_optional:
                print("✓ 所有依赖已安装")
        return True

    return False


def test_system_monitor():
    """测试系统监控模块"""
    print("=== 测试系统监控模块 ===")
    from services.cluster.system_monitor import SystemMonitor
    
    monitor = SystemMonitor()
    info = monitor.to_dict(include_gpu=True)
    
    print(f"平台: {info['platform']}")
    print(f"主机名: {info['hostname']}")
    print(f"CPU: {info['cpu']['model']}")
    print(f"CPU核心数: {info['cpu']['logical_cores']}")
    print(f"内存: {info['memory']['total_mb'] / 1024:.1f} GB")
    print(f"NPU数量: {info['npu_count']}")
    
    return True

def test_cluster_manager():
    """测试集群管理器"""
    print("\n=== 测试集群管理器 ===")
    from services.cluster import ClusterManager
    
    cluster = ClusterManager()
    summary = cluster.get_summary()
    
    print(f"集群状态: {summary['status']}")
    print(f"节点数: {summary['total_nodes']}")
    
    system_info = cluster.get_system_info()
    print(f"系统信息获取成功")
    
    return True

def test_ui_effects():
    """测试UI视觉特效模块"""
    print("\n=== 测试UI视觉特效模块 ===")
    from ui.effects import GLEffects, GLColor, GlassEffectParams, GlowEffectParams
    
    effects = GLEffects()
    print(f"版本: {effects.get_version()}")
    
    effects.init(800, 600)
    print("初始化成功")
    
    effects.set_transparency(0.8)
    print(f"透明度设置: {effects.get_transparency()}")
    
    effects.enable_glass_effect(True)
    print(f"毛玻璃效果: {effects.is_glass_enabled()}")
    
    effects.enable_glow_effect(True)
    print(f"光晕效果: {effects.is_glow_enabled()}")
    
    # 设置毛玻璃参数
    glass_params = GlassEffectParams()
    glass_params.blur_radius = 15.0
    effects.set_glass_params(glass_params)
    print("毛玻璃参数设置成功")
    
    # 设置光晕参数
    glow_params = GlowEffectParams()
    glow_params.glow_color = GLColor(0.3, 0.6, 1.0, 0.7)
    effects.set_glow_params(glow_params)
    print("光晕参数设置成功")
    
    # 渲染测试
    for i in range(5):
        effects.render()
    
    effects.shutdown()
    print("关闭成功")
    
    return True

def test_ai_agent():
    """测试AI代理系统"""
    print("\n=== 测试AI代理系统 ===")
    from services.ai_agent import AIAgent
    
    agent = AIAgent()
    print(f"AI代理系统初始化成功")
    
    tools = agent.get_available_tools()
    print(f"已注册工具数量: {len(tools)}")
    
    if tools:
        print("可用工具:")
        for tool in tools[:5]:
            print(f"  - {tool.name}")
    
    return True

def test_config():
    """测试配置模块"""
    print("\n=== 测试配置模块 ===")
    from config.settings import Settings
    
    settings = Settings()
    print(f"配置加载成功")
    print(f"DEBUG模式: {settings.debug}")
    print(f"端口: {settings.port}")
    
    return True

def test_screen_monitor():
    """测试屏幕监控模块"""
    print("\n=== 测试屏幕监控模块 ===")
    from services.screen_monitor import ScreenMonitor, HAS_OPENCV
    
    monitor = ScreenMonitor()
    print(f"屏幕监控初始化成功")
    print(f"支持OpenCV/RTMP: {HAS_OPENCV}")
    
    return True

def test_api_server():
    """测试API服务器模块"""
    print("\n=== 测试API服务器模块 ===")
    from services.api_server import APIServer
    
    print("API服务器模块导入成功")
    return True

def test_websocket_server():
    """测试WebSocket服务器模块"""
    print("\n=== 测试WebSocket服务器模块 ===")
    from services.websocket_server import WebSocketServer
    
    print("WebSocket服务器模块导入成功")
    return True

def test_high_risk_detector():
    """测试高危操作检测器（平台感知 + 黑名单 + 敏感路径 + 白名单）"""
    print("\n=== 测试高危操作检测 ===")
    from system.high_risk_detector import HighRiskDetector

    detector = HighRiskDetector()
    print(f"当前平台: {detector.platform}")

    failures = []

    # 1. 白名单：查看类命令不应判为高危
    safe_cmds = ["ls", "ls -la", "echo hello", "whoami", "date", "ps aux", "dir"]
    safe_fail = 0
    for cmd in safe_cmds:
        high, reason = detector.is_high_risk_command(cmd)
        if high:
            failures.append(f"白名单命令被误判为高危: {cmd!r} -> {reason}")
            safe_fail += 1
    print(f"白名单命令检查: {len(safe_cmds)} 个，{'通过' if safe_fail == 0 else f'失败 {safe_fail} 个'}")

    # 2. 当前平台高危命令应被识别
    if detector.platform == "Windows":
        high_risk_cmds = ["format D:", "reg add HKLM\\Software\\X", "netsh interface",
                          "taskkill /f /im explorer.exe", "shutdown /s /t 0",
                          "del /f /s C:\\Windows\\temp"]
    else:
        high_risk_cmds = ["sudo apt update", "rm -rf /", "systemctl stop nginx",
                          "chmod 777 /etc", "dd if=/dev/zero of=/dev/sda",
                          "useradd newuser"]
    hr_fail = 0
    for cmd in high_risk_cmds:
        high, reason = detector.is_high_risk_command(cmd)
        if not high:
            failures.append(f"高危命令未被识别: {cmd!r}")
            hr_fail += 1
        else:
            print(f"  ✓ 识别高危: {cmd!r} ({reason})")
    print(f"高危命令检查: {len(high_risk_cmds)} 个，{'通过' if hr_fail == 0 else f'失败 {hr_fail} 个'}")

    # 3. 危险热键应被识别
    high, reason = detector.is_high_risk_hotkey(["alt", "f4"])
    if not high:
        failures.append("危险热键 Alt+F4 未被识别")
    else:
        print(f"  ✓ 识别危险热键: Alt+F4 ({reason})")

    # 4. 安全热键不应误判
    high, _ = detector.is_high_risk_hotkey(["ctrl", "c"])
    if high:
        failures.append("安全热键 Ctrl+C 被误判为高危")

    # 5. 操作类型分发（用当前平台的高危命令 + 安全操作）
    high, _ = detector.is_high_risk_operation("execute_command", {"command": high_risk_cmds[0]})
    if not high:
        failures.append(f"is_high_risk_operation 未识别 execute_command 高危: {high_risk_cmds[0]!r}")
    high, _ = detector.is_high_risk_operation("mouse_move", {"x": 100, "y": 100})
    if high:
        failures.append("is_high_risk_operation 误判 mouse_move 为高危")

    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        return False

    print("✓ 高危操作检测全部通过")
    return True


def test_privilege_manager():
    """测试提权管理器（单例 + 平台探测 + fail-safe + PrivilegeTool 注册）"""
    print("\n=== 测试提权管理器 ===")
    from system.privilege_manager import PrivilegeManager

    mgr = PrivilegeManager()
    print(f"当前平台: {mgr.platform}")
    failures = []

    # 1. 单例
    if mgr is not PrivilegeManager():
        failures.append("PrivilegeManager 不是单例")

    # 2. 平台支持
    if not mgr.is_available():
        failures.append(f"当前平台 {mgr.platform} 不在支持列表")
    else:
        print(f"  ✓ 平台支持提权: {mgr.platform}")

    # 3. fail-safe：未配置 ConfirmationManager 时拒绝提权（不触发实际 UAC/sudo）
    result = mgr.execute_privileged("whoami", reason="测试提权")
    if result.get("success"):
        failures.append("fail-safe 失败：未配置确认管理器时不应允许提权")
    else:
        print(f"  ✓ fail-safe 生效（未配置时拒绝）")

    # 4. 空命令拒绝
    if mgr.execute_privileged("").get("success"):
        failures.append("空命令不应执行")

    # 5. PrivilegeTool 已注册到 AIAgent 且分类为 system
    try:
        import json as _json
        from services.ai_agent import AIAgent
        agent = AIAgent()
        tools_desc = agent.get_tool_descriptions(format="json")
        if "PrivilegeTool" not in tools_desc:
            failures.append("PrivilegeTool 未注册到 AIAgent")
        else:
            print("  ✓ PrivilegeTool 已注册到 AIAgent")
            tools_list = _json.loads(tools_desc)
            priv_tool = next((t for t in tools_list if t["name"] == "PrivilegeTool"), None)
            if priv_tool and priv_tool.get("category") != "system":
                failures.append(f"PrivilegeTool category 应为 system，实际: {priv_tool.get('category')}")
            elif priv_tool:
                print("  ✓ PrivilegeTool 分类为 system")
    except Exception as e:
        failures.append(f"AIAgent 注册检查失败: {e}")

    # 6. 真实权限检测（is_elevated，不弹框，可与系统命令交叉验证）
    try:
        import subprocess as _sp
        elevated = mgr.is_elevated()
        print(f"  ✓ 真实权限检测: 当前{'已提权' if elevated else '未提权（普通权限）'}")
        # 交叉验证：用系统命令核对 is_elevated 的真实性
        if mgr.platform == "Windows":
            chk = _sp.run("whoami /groups", shell=True, capture_output=True, text=True, timeout=10)
            has_high = "S-1-16-12288" in chk.stdout  # High Mandatory Level SID
            if elevated and not has_high:
                failures.append("is_elevated=True 但 whoami /groups 未显示高完整性，可能误报")
            print(f"    交叉验证（whoami /groups 高完整性）: {has_high}")
        else:
            chk = _sp.run("id -u", shell=True, capture_output=True, text=True, timeout=10)
            is_root = chk.stdout.strip() == "0"
            if elevated != is_root:
                failures.append(f"is_elevated={elevated} 与 id -u=0={is_root} 不一致")
            print(f"    交叉验证（id -u == 0）: {is_root}")
    except Exception as e:
        failures.append(f"真实权限检测失败: {e}")

    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        return False
    print("✓ 提权管理器测试全部通过")
    return True


def test_privilege_manager_cli():
    """测试提权管理器 __main__ CLI 入口（端到端，stdin 喂 no 走拒绝路径，不触发 UAC）"""
    print("\n=== 测试提权管理器 CLI 入口 ===")
    import subprocess as _sp
    import sys as _sys
    project_root = os.path.dirname(os.path.abspath(__file__))

    # 用 -m 运行（src 作为包），stdin 喂 "no" 模拟用户拒绝 → 不触发 UAC/sudo
    try:
        proc = _sp.run(
            [_sys.executable, "-m", "src.system.privilege_manager", "whoami"],
            input="no\n", capture_output=True, text=True,
            timeout=30, cwd=project_root,
        )
    except _sp.TimeoutExpired:
        print("  ✗ CLI 测试超时（可能卡在 input/UAC）")
        return False

    failures = []
    combined = proc.stdout + proc.stderr

    # 1. 拒绝路径退出码应为 1（sys.exit(0 if success else 1)）
    if proc.returncode != 1:
        failures.append(f"拒绝路径退出码应为 1，实际 {proc.returncode}")
    else:
        print("  ✓ 拒绝路径退出码 = 1")

    # 2. 输出含真实权限检测
    if "当前已提权" in combined:
        print("  ✓ 输出含真实权限检测")
    else:
        failures.append("输出未含权限检测信息（当前已提权）")

    # 3. 输出含拒绝信息
    if "用户未授权" in combined or "已拒绝" in combined:
        print("  ✓ 输出含拒绝信息")
    else:
        failures.append("输出未含拒绝信息")

    # 4. 拒绝路径不应触发 UAC
    if "UAC" in combined and "失败" in combined:
        failures.append("拒绝路径不应触发 UAC")

    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        return False
    print("✓ 提权管理器 CLI 入口测试通过")
    return True


def test_privilege_verify():
    """测试真实提权验证方法（在系统目录创建/写/删 test.txt）"""
    print("\n=== 测试提权验证方法 ===")
    from system.privilege_manager import PrivilegeManager
    mgr = PrivilegeManager()
    failures = []

    # 1. verify_privilege 可调用且返回结构正确（未提权失败，已提权成功）
    result = mgr.verify_privilege()
    if "success" not in result or "message" not in result:
        failures.append("verify_privilege 返回结构异常")
    elif result.get("success"):
        print("  ✓ verify_privilege 成功（当前以管理员运行，真实提权生效）")
    else:
        print(f"  ✓ verify_privilege 失败（未提权，符合预期）")

    # 2. _verify_shell_command 返回非空
    cmd = mgr._verify_shell_command()
    if not cmd:
        failures.append("_verify_shell_command 返回空")
    else:
        print(f"  ✓ verify shell 命令已生成（长度 {len(cmd)}）")

    # 3. execute_privileged("__verify__") 未配置确认管理器时 fail-safe 拒绝（不弹 UAC）
    no_confirm = mgr.execute_privileged("__verify__", reason="验证测试")
    if no_confirm.get("success"):
        failures.append("未配置确认管理器时 verify 不应成功")
    else:
        print("  ✓ fail-safe 生效（未配置时拒绝 verify，不弹 UAC）")

    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        return False
    print("✓ 提权验证方法测试通过")
    return True


def test_node_engine_runtime():
    """测试节点引擎运行时（后端自动检测 + 图执行 + 环检测）"""
    print("\n=== 测试节点引擎运行时 ===")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    try:
        from src.core.node_engine import NodeEngine, make_graph, execute_graph
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
        return False

    try:
        eng = NodeEngine()
    except Exception as e:
        print(f"  ✗ NodeEngine 实例化失败: {e}")
        return False

    failures = []

    # a. backend 检查
    if eng.backend not in ('python', 'cppyy'):
        failures.append(f"backend 应为 python/cppyy，实际: {eng.backend}")
    else:
        print(f"  ✓ backend: {eng.backend}")

    # b. node_classes 数量
    nc_len = len(eng.node_classes)
    if nc_len < 44:
        failures.append(f"node_classes 数量应 >= 44，实际: {nc_len}")
    else:
        print(f"  ✓ node_classes 数量: {nc_len}")

    # c. Number(2)+Number(3)→Add→output.s==5
    try:
        n2 = eng.Number(2)
        n3 = eng.Number(3)
        add_node = eng.Add()
        g = make_graph(n2, n3, add_node)
        idx_n2 = 0
        idx_n3 = 1
        idx_add = 2
        g.connect(idx_n2, 0, idx_add, 0)
        g.connect(idx_n3, 0, idx_add, 1)
        execute_graph(g)
        out_s = add_node.outputs[0].s
        if abs(float(out_s) - 5.0) < 1e-9:
            print(f"  ✓ Number(2)+Number(3) = {out_s}")
        else:
            failures.append(f"Number(2)+Number(3) 应为 5.0，实际: {out_s}")
    except Exception as e:
        failures.append(f"Number+Add 图执行失败: {e}")

    # d. 环检测：Add A 连 Add B，Add B 连 Add A
    try:
        num1 = eng.Number(1)
        add_a = eng.Add()
        add_b = eng.Add()
        g2 = make_graph(num1, add_a, add_b)
        idx_num1 = 0
        idx_a = 1
        idx_b = 2
        g2.connect(idx_num1, 0, idx_a, 0)
        g2.connect(idx_a, 0, idx_b, 0)
        g2.connect(idx_b, 0, idx_a, 1)
        has_cycle_err = False
        try:
            execute_graph(g2)
        except Exception as e2:
            err_msg = str(e2).lower()
            if "cycle" in err_msg:
                has_cycle_err = True
            else:
                failures.append(f"环检测异常信息不含 'cycle': {e2}")
        if has_cycle_err:
            print("  ✓ 环检测生效（cycle detected）")
        else:
            failures.append("环检测未触发异常")
    except Exception as e:
        failures.append(f"环检测测试异常: {e}")

    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        return False
    print("✓ 节点引擎运行时测试全部通过")
    return True


def test_math_nodes_correctness():
    """测试 12+ 数学节点与 Python math/statistics 对照正确性"""
    print("\n=== 测试数学节点正确性 ===")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    import math as _math
    try:
        from src.core.node_engine import NodeEngine, make_graph, execute_graph
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
        return False

    eng = NodeEngine()
    failures = []

    def _run_single(node_cls, inputs_info, expected, tol=1e-9):
        """通用：实例化节点，设 inputs，连边 make_graph 执行，取 outputs[0].s 比较"""
        try:
            node = node_cls()
        except Exception as e:
            return f"实例化 {node_cls.__name__ if hasattr(node_cls, '__name__') else node_cls} 失败: {e}"
        g = make_graph(node)
        try:
            for i, val in enumerate(inputs_info):
                if isinstance(val, (int, float)):
                    node.inputs[i].s = float(val)
                elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], (list, tuple)):
                    node.inputs[i].m = [[float(x) for x in r] for r in val]
                elif isinstance(val, list):
                    node.inputs[i].v = [float(x) for x in val]
        except Exception as e:
            return f"设 {node.name} inputs 失败: {e}"
        try:
            execute_graph(g)
        except Exception as e:
            return f"{node.name} execute 失败: {e}"
        out = node.outputs[0].s
        try:
            out_f = float(out)
        except Exception:
            return f"{node.name} outputs[0].s 不是标量: {out}"
        if abs(out_f - expected) < tol:
            return None
        return f"{node.name} 预期 {expected}，实际 {out_f}"

    def _check(label, err):
        if err is None:
            print(f"  ✓ {label}")
        else:
            print(f"  ✗ {label}: {err}")
            failures.append(label)

    # Number
    try:
        num = eng.Number(3.14)
        if abs(float(num.outputs[0].s) - 3.14) < 1e-9:
            print("  ✓ Number(3.14) == 3.14")
        else:
            _check("Number(3.14)", f"实际 {num.outputs[0].s}")
    except Exception as e:
        _check("Number(3.14)", f"失败: {e}")

    # Add / Sub / Mul / Div / Mod
    def _make_bin(cls, a, b, expected):
        na = eng.Number(a)
        nb = eng.Number(b)
        n = cls()
        g = make_graph(na, nb, n)
        g.connect(0, 0, 2, 0)
        g.connect(1, 0, 2, 1)
        execute_graph(g)
        return float(n.outputs[0].s)

    def _check_bin(name, a, b, expected):
        cls_map = {"Add": eng.Add, "Sub": eng.Sub, "Mul": eng.Mul, "Div": eng.Div, "Mod": eng.Mod, "Pow": eng.Pow}
        try:
            v = _make_bin(cls_map[name], a, b, expected)
            if abs(v - expected) < 1e-9:
                print(f"  ✓ {name}({a},{b}) == {expected}")
            else:
                _check(f"{name}({a},{b})", f"实际 {v}")
        except Exception as e:
            _check(f"{name}({a},{b})", f"失败: {e}")

    _check_bin("Add", 1.5, 2.5, 4.0)
    _check_bin("Sub", 5, 2, 3.0)
    _check_bin("Mul", 3, 4, 12.0)
    _check_bin("Div", 7, 2, 3.5)
    _check_bin("Mod", 7, 3, 1.0)

    # Negate / Abs (单输入)
    def _make_un(cls, x, expected):
        nx = eng.Number(x)
        n = cls()
        g = make_graph(nx, n)
        g.connect(0, 0, 1, 0)
        execute_graph(g)
        return float(n.outputs[0].s)

    def _check_un(name, x, expected):
        cls_map = {"Negate": eng.Negate, "Abs": eng.Abs, "Sqrt": eng.Sqrt, "Exp": eng.Exp,
                   "Log2": eng.Log2, "Log10": eng.Log10, "Sin": eng.Sin, "Cos": eng.Cos, "Asin": eng.Asin}
        try:
            v = _make_un(cls_map[name], x, expected)
            if abs(v - expected) < 1e-9:
                print(f"  ✓ {name}({x}) == {expected}")
            else:
                _check(f"{name}({x})", f"实际 {v}")
        except Exception as e:
            _check(f"{name}({x})", f"失败: {e}")

    _check_un("Negate", -5, 5)
    _check_un("Abs", -7, 7)
    _check_un("Sqrt", 9, 3.0)
    _check_un("Exp", 0, 1.0)
    _check_un("Log2", 8, 3.0)
    _check_un("Log10", 100, 2.0)
    _check_un("Sin", _math.pi / 2, 1.0)
    _check_un("Cos", 0, 1.0)
    _check_un("Asin", 0, 0.0)

    # Pow(2, 10)
    _check_bin("Pow", 2, 10, 1024.0)

    # Log(e) 自然对数
    try:
        ne = eng.Number(_math.e)
        log_node = eng.Log()
        g = make_graph(ne, log_node)
        g.connect(0, 0, 1, 0)
        execute_graph(g)
        v = float(log_node.outputs[0].s)
        if abs(v - 1.0) < 1e-9:
            print(f"  ✓ Log(e) == 1.0")
        else:
            _check("Log(e)", f"实际 {v}")
    except Exception as e:
        _check("Log(e)", f"失败: {e}")

    # VecDot([1,2,3],[4,5,6]) = 32
    try:
        vc1 = eng.VecCreate(3)
        vc1.inputs[0].s = 1.0
        vc1.inputs[1].s = 2.0
        vc1.inputs[2].s = 3.0
        vc2 = eng.VecCreate(3)
        vc2.inputs[0].s = 4.0
        vc2.inputs[1].s = 5.0
        vc2.inputs[2].s = 6.0
        vd = eng.VecDot()
        g = make_graph(vc1, vc2, vd)
        g.connect(0, 0, 2, 0)
        g.connect(1, 0, 2, 1)
        execute_graph(g)
        v = float(vd.outputs[0].s)
        if abs(v - 32.0) < 1e-9:
            print(f"  ✓ VecDot([1,2,3],[4,5,6]) == 32")
        else:
            _check("VecDot", f"实际 {v}")
    except Exception as e:
        _check("VecDot", f"失败: {e}")

    # VecNorm([3,4]) = 5.0
    try:
        vc = eng.VecCreate(2)
        vc.inputs[0].s = 3.0
        vc.inputs[1].s = 4.0
        vn = eng.VecNorm()
        g = make_graph(vc, vn)
        g.connect(0, 0, 1, 0)
        execute_graph(g)
        v = float(vn.outputs[0].s)
        if abs(v - 5.0) < 1e-9:
            print(f"  ✓ VecNorm([3,4]) == 5.0")
        else:
            _check("VecNorm", f"实际 {v}")
    except Exception as e:
        _check("VecNorm", f"失败: {e}")

    # Det([[1,2],[3,4]]) = -2.0
    try:
        mc = eng.MatCreate(2, 2)
        mc.inputs[0].s = 1.0
        mc.inputs[1].s = 2.0
        mc.inputs[2].s = 3.0
        mc.inputs[3].s = 4.0
        md = eng.MatDet()
        g = make_graph(mc, md)
        g.connect(0, 0, 1, 0)
        execute_graph(g)
        v = float(md.outputs[0].s)
        if abs(v - (-2.0)) < 1e-9:
            print(f"  ✓ Det([[1,2],[3,4]]) == -2.0")
        else:
            _check("Det", f"实际 {v}")
    except Exception as e:
        _check("Det", f"失败: {e}")

    # Median([3,1,4,1,5,9,2,6]) = 3.5
    try:
        data = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0]
        vc8 = eng.VecCreate(8)
        for i in range(8):
            vc8.inputs[i].s = data[i]
        med = eng.Median()
        g = make_graph(vc8, med)
        g.connect(0, 0, 1, 0)
        execute_graph(g)
        v = float(med.outputs[0].s)
        if abs(v - 3.5) < 1e-9:
            print(f"  ✓ Median([3,1,4,1,5,9,2,6]) == 3.5")
        else:
            _check("Median", f"实际 {v}")
    except Exception as e:
        _check("Median", f"失败: {e}")

    # Clamp(5, 1, 3) = 3
    def _make_ter(cls, v, lo, hi, expected):
        nv = eng.Number(v)
        nlo = eng.Number(lo)
        nhi = eng.Number(hi)
        n = cls()
        g = make_graph(nv, nlo, nhi, n)
        g.connect(0, 0, 3, 0)
        g.connect(1, 0, 3, 1)
        g.connect(2, 0, 3, 2)
        execute_graph(g)
        return float(n.outputs[0].s)

    def _check_ter(name, v, lo, hi, expected):
        cls_map = {"Clamp": eng.Clamp, "Lerp": eng.Lerp, "If": eng.If}
        try:
            val = _make_ter(cls_map[name], v, lo, hi, expected)
            if abs(val - expected) < 1e-9:
                print(f"  ✓ {name}({v},{lo},{hi}) == {expected}")
            else:
                _check(f"{name}({v},{lo},{hi})", f"实际 {val}")
        except Exception as e:
            _check(f"{name}({v},{lo},{hi})", f"失败: {e}")

    _check_ter("Clamp", 5, 1, 3, 3.0)
    _check_ter("Lerp", 0, 10, 0.5, 5.0)
    _check_ter("If", 1, 100, 200, 100.0)
    _check_ter("If", 0, 100, 200, 200.0)

    if failures:
        return False
    print("✓ 数学节点正确性测试全部通过")
    return True


def test_math_calculator_tool():
    """测试 MathCalculatorTool evaluate/build_graph 及 AIAgent 注册"""
    print("\n=== 测试 MathCalculatorTool ===")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    import json as _json
    import re as _re
    try:
        from src.services.math_calculator_tool import MathCalculatorTool
        from src.services.ai_agent import AIAgent
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
        return False

    failures = []

    def _parse_result(text):
        code_match = _re.search(r'^code:\s*(\S+)', text, _re.MULTILINE)
        code = code_match.group(1) if code_match else None
        data_match = _re.search(r'^data:\s*(\{.*\})', text, _re.MULTILINE)
        data = None
        if data_match:
            try:
                data = _json.loads(data_match.group(1))
            except Exception:
                data = None
        return code, data

    # a. evaluate: 'sin(pi/2)+sqrt(16)' => code=OK, value=5.0
    try:
        res = MathCalculatorTool.execute(mode="evaluate", expression="sin(pi/2)+sqrt(16)")
        code, data = _parse_result(res)
        if code == "OK" and data and abs(float(data.get("value", 0)) - 5.0) < 1e-9:
            print(f"  ✓ evaluate sin(pi/2)+sqrt(16) = {data.get('value')}")
        else:
            failures.append(f"evaluate sin(pi/2)+sqrt(16) 失败: code={code}, data={data}, raw={res[:200]}")
    except Exception as e:
        failures.append(f"evaluate a 异常: {e}")

    # b. evaluate: '(1+2)*(3-4)/5' == -0.6
    try:
        res = MathCalculatorTool.execute(mode="evaluate", expression="(1+2)*(3-4)/5")
        code, data = _parse_result(res)
        if code == "OK" and data and abs(float(data.get("value", 0)) - (-0.6)) < 1e-9:
            print(f"  ✓ evaluate (1+2)*(3-4)/5 = {data.get('value')}")
        else:
            failures.append(f"evaluate (1+2)*(3-4)/5 失败: code={code}, data={data}")
    except Exception as e:
        failures.append(f"evaluate b 异常: {e}")

    # c. evaluate with variables: 'x*x + 2*x + 1', variables='{"x":3}' == 16.0
    try:
        res = MathCalculatorTool.execute(mode="evaluate", expression="x*x + 2*x + 1", variables='{"x":3}')
        code, data = _parse_result(res)
        if code == "OK" and data and abs(float(data.get("value", 0)) - 16.0) < 1e-9:
            print(f"  ✓ evaluate with x=3: x*x+2x+1 = {data.get('value')}")
        else:
            failures.append(f"evaluate with vars 失败: code={code}, data={data}")
    except Exception as e:
        failures.append(f"evaluate c 异常: {e}")

    # d. build_graph JSON: Number(2)×Number(3)=Mul 输出 6
    try:
        graph_desc = {
            "nodes": [
                {"id": "n1", "type": "Number", "params": {"value": 2}},
                {"id": "n2", "type": "Number", "params": {"value": 3}},
                {"id": "n3", "type": "Mul"},
            ],
            "edges": [
                {"from": "n1", "out": 0, "to": "n3", "in": 0},
                {"from": "n2", "out": 0, "to": "n3", "in": 1},
            ],
        }
        res = MathCalculatorTool.execute(mode="build_graph", graph_json=_json.dumps(graph_desc))
        code, data = _parse_result(res)
        out_val = None
        if data and "outputs_by_id" in data:
            out_val = data["outputs_by_id"].get("n3")
        ok = (code == "OK") and (out_val is not None) and (abs(float(out_val) - 6.0) < 1e-9)
        if ok:
            print(f"  ✓ build_graph Number(2)*Number(3) = {out_val}")
        else:
            failures.append(f"build_graph Mul 失败: code={code}, out={out_val}, raw={res[:200]}")
    except Exception as e:
        failures.append(f"build_graph d 异常: {e}")

    # e. AIAgent().get_tool_descriptions() 含 MathCalculatorTool 且 category=math
    try:
        agent = AIAgent()
        desc = agent.get_tool_descriptions(format="json")
        desc_list = _json.loads(desc)
        found = False
        for t in desc_list:
            if t.get("name") == "MathCalculatorTool":
                found = True
                if t.get("category") == "math":
                    print("  ✓ MathCalculatorTool 已注册且 category=math")
                else:
                    failures.append(f"MathCalculatorTool category 应为 math，实际: {t.get('category')}")
                break
        if not found:
            failures.append("AIAgent 工具列表未含 MathCalculatorTool")
    except Exception as e:
        failures.append(f"AIAgent 注册检查异常: {e}")

    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        return False
    print("✓ MathCalculatorTool 测试全部通过")
    return True


def test_copilot_provider():
    """测试 GitHub Copilot SDK provider 接入（fail-safe：SDK 未安装时正确报错）"""
    print("\n=== 测试 GitHub Copilot provider ===")
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    failures = []

    # 1. GitHubCopilot provider 已注册到 AIProviderManager
    try:
        from src.config.ai_providers import AIProviderManager
        mgr = AIProviderManager()
        names = mgr.list_providers()
        if "GitHubCopilot" not in names:
            failures.append(f"GitHubCopilot 未注册，当前 providers: {names}")
        else:
            p = mgr.get_provider("GitHubCopilot")
            print(f"  ✓ GitHubCopilot provider 已注册: base_url={p.base_url}, model={p.default_model}")
            if not p.base_url.startswith("copilot://"):
                failures.append(f"base_url 应以 copilot:// 开头，实际: {p.base_url}")
    except Exception as e:
        failures.append(f"AIProviderManager 检查失败: {e}")

    # 2. settings 含 copilot 配置项
    try:
        from src.config import settings
        for attr in ["copilot_model", "copilot_github_token", "copilot_auto_approve_permissions"]:
            if not hasattr(settings, attr):
                failures.append(f"settings 缺少 {attr}")
        # 默认值检查
        if hasattr(settings, 'copilot_model') and settings.copilot_model != "auto":
            failures.append(f"copilot_model 默认值应为 auto，实际: {settings.copilot_model}")
        if hasattr(settings, 'copilot_auto_approve_permissions') and not settings.copilot_auto_approve_permissions:
            failures.append("copilot_auto_approve_permissions 默认应为 True")
        print("  ✓ settings 配置项完整: copilot_model/copilot_github_token/copilot_auto_approve_permissions")
    except Exception as e:
        failures.append(f"settings 检查失败: {e}")

    # 3. AIService.is_copilot_provider 正确识别
    try:
        from src.services.ai_service import AIService
        from src.config.ai_providers import AIProvider
        svc = AIService(provider=AIProvider(name="GitHubCopilot", base_url="copilot://github", api_key="", default_model="auto"))
        if not svc.is_copilot_provider():
            failures.append("is_copilot_provider() 应识别 GitHubCopilot provider")
        # 反例：OpenAI provider 不应被识别为 copilot
        svc2 = AIService(provider=AIProvider(name="OpenAI", base_url="https://api.openai.com/v1", api_key="sk-test", default_model="gpt-4o"))
        if svc2.is_copilot_provider():
            failures.append("OpenAI provider 不应被识别为 copilot")
        print("  ✓ is_copilot_provider() 正确识别 GitHubCopilot 与非 Copilot provider")
    except Exception as e:
        # 当前没装 github-copilot-sdk 时实例化会抛 ExternalDependencyError，这是预期
        from src.utils.errors import ExternalDependencyError
        if "ExternalDependencyError" in type(e).__name__ or isinstance(e, ExternalDependencyError):
            print(f"  ✓ Copilot SDK 未安装时实例化 AIService 抛 ExternalDependencyError（fail-safe 正常）")
        else:
            # 但 is_copilot_provider 应该不依赖 SDK 也能判断（不实例化 CopilotService 就行）
            # 这里走 _initialize_client 失败，但 is_copilot_provider 是 provider 字段判断
            failures.append(f"AIService 实例化异常: {type(e).__name__}: {e}")

    # 4. CopilotService fail-safe：未安装 github-copilot-sdk 时抛 ExternalDependencyError
    try:
        # 模拟 SDK 未安装：临时把 copilot 模块设为 None
        import sys as _sys
        original = _sys.modules.get('copilot')
        _sys.modules['copilot'] = None  # 让 import copilot 失败
        try:
            from src.services.copilot_service import CopilotService
            try:
                svc = CopilotService(model="auto")
                failures.append("SDK 未安装时 CopilotService 应抛 ExternalDependencyError，但实例化成功")
            except Exception as ex:
                from src.utils.errors import ExternalDependencyError
                if isinstance(ex, ExternalDependencyError):
                    code = getattr(ex, 'code', None)
                    code_str = str(code) if code is not None else ''
                    if 'E_EXT_DEPENDENCY_MISSING' in code_str or 'EXT_DEPENDENCY' in code_str:
                        print(f"  ✓ CopilotService fail-safe: 抛 ExternalDependencyError(E_EXT_DEPENDENCY_MISSING)")
                    else:
                        failures.append(f"ExternalDependencyError 但错误码不对: {code}")
                else:
                    failures.append(f"应抛 ExternalDependencyError，实际抛: {type(ex).__name__}")
        finally:
            # 恢复
            if original is not None:
                _sys.modules['copilot'] = original
            else:
                _sys.modules.pop('copilot', None)
    except Exception as e:
        failures.append(f"CopilotService fail-safe 测试异常: {e}")

    # 5. requirements.txt 含 github-copilot-sdk
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt"), "r", encoding="utf-8") as f:
            reqs = f.read()
        if "github-copilot-sdk" not in reqs:
            failures.append("requirements.txt 缺少 github-copilot-sdk")
        else:
            print("  ✓ requirements.txt 含 github-copilot-sdk")
    except Exception as e:
        failures.append(f"requirements.txt 读取失败: {e}")

    # 6. .env.example 含 COPILOT_ 配置项
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.example"), "r", encoding="utf-8") as f:
            env_ex = f.read()
        for key in ["COPILOT_MODEL", "COPILOT_GITHUB_TOKEN", "COPILOT_AUTO_APPROVE_PERMISSIONS"]:
            if key not in env_ex:
                failures.append(f".env.example 缺少 {key}")
        if not failures:
            print("  ✓ .env.example 含 COPILOT_MODEL/COPILOT_GITHUB_TOKEN/COPILOT_AUTO_APPROVE_PERMISSIONS")
    except Exception as e:
        failures.append(f".env.example 读取失败: {e}")

    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        return False
    print("✓ GitHub Copilot provider 测试全部通过")
    return True


def _parse_test_args(argv):
    """解析 test_main.py 的命令行参数。

    支持的参数：
      --deps <路径>          指定依赖列表 txt 文件路径进行依赖检查
      --deps-only            仅运行依赖检查测试，跳过其他功能测试
      --strict / --no-strict 强制启用/禁用严格模式（默认自动判断）
      -h, --help             显示帮助

    示例：
      python test_main.py                              # 默认全部测试，依赖检查用 requirements.txt
      python test_main.py --deps my_deps.txt           # 全部测试，依赖检查用 my_deps.txt
      python test_main.py --deps my_deps.txt --deps-only  # 仅用 my_deps.txt 跑依赖检查
      python test_main.py --deps requirements.txt --no-strict  # 用 requirements.txt 但强制严格模式
    """
    deps_file = None
    deps_only = False
    strict_override = None
    show_help = False

    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            show_help = True
        elif arg == "--deps":
            if i + 1 < len(argv):
                deps_file = argv[i + 1]
                i += 1
            else:
                print("错误: --deps 需要一个文件路径参数")
                show_help = True
        elif arg == "--deps-only":
            deps_only = True
        elif arg == "--strict":
            strict_override = True
        elif arg == "--no-strict":
            strict_override = False
        else:
            # 兼容位置参数：第一个非选项参数视为依赖文件路径
            if deps_file is None and not arg.startswith("-"):
                deps_file = arg
            else:
                print(f"警告: 忽略未知参数 {arg}")
        i += 1

    return deps_file, deps_only, strict_override, show_help


def _print_usage():
    print("""
AIclaw 测试脚本用法:
  python test_main.py [选项] [依赖文件路径]

选项:
  --deps <路径>          指定依赖列表 txt 文件路径进行依赖检查
  --deps-only            仅运行依赖检查测试，跳过其他功能测试
  --strict               强制严格模式（所有缺失都视为失败）
  --no-strict            强制分级模式（核心缺失失败、可选缺失警告）
  -h, --help             显示本帮助

示例:
  python test_main.py                              默认全部测试
  python test_main.py --deps my_deps.txt           指定依赖文件
  python test_main.py --deps my_deps.txt --deps-only  仅跑依赖检查
  python test_main.py --deps requirements.txt --strict  强制严格模式
""")


def main():
    """运行所有测试"""
    deps_file, deps_only, strict_override, show_help = _parse_test_args(sys.argv)

    if show_help:
        _print_usage()
        return True

    print("=" * 60)
    print("AIclaw 完整功能测试")
    print("=" * 60)

    # 构造依赖检查测试的调用（支持文件路径与 strict 覆盖）
    def _run_pip_deps():
        if strict_override is not None:
            return test_pip_dependencies(file_path=deps_file, strict=strict_override)
        return test_pip_dependencies(file_path=deps_file)

    tests = [
        ("pip 依赖库", _run_pip_deps),
        ("系统监控", test_system_monitor),
        ("集群管理器", test_cluster_manager),
        ("UI视觉特效", test_ui_effects),
        ("AI代理系统", test_ai_agent),
        ("配置模块", test_config),
        ("屏幕监控", test_screen_monitor),
        ("API服务器", test_api_server),
        ("WebSocket服务器", test_websocket_server),
        ("高危操作检测", test_high_risk_detector),
        ("提权管理器", test_privilege_manager),
        ("提权CLI入口", test_privilege_manager_cli),
        ("提权验证方法", test_privilege_verify),
        ("节点引擎运行时", test_node_engine_runtime),
        ("数学节点正确性", test_math_nodes_correctness),
        ("数学计算器工具", test_math_calculator_tool),
        ("Copilot provider", test_copilot_provider),
    ]

    # --deps-only：仅保留依赖检查测试
    if deps_only:
        tests = [tests[0]]
        print("(仅运行依赖检查测试 --deps-only)")

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"✓ {name}: 通过")
                passed += 1
            else:
                print(f"✗ {name}: 失败（测试函数返回 False）")
                failed += 1
        except AppError as e:
            # 业务异常：输出错误码 + 模块 + 上下文 + 建议
            print(f"✗ {name}: {e}")
            if _HAS_APP_ERROR and hasattr(e, "module"):
                print(f"    模块: {e.module}")
                print(f"    错误码: {e.code.name if hasattr(e, 'code') else 'unknown'}")
                if getattr(e, "details", None):
                    print(f"    上下文: {e.details}")
                suggestion = get_suggestion(getattr(e, "code", None)) if getattr(e, "code", None) else ""
                if suggestion:
                    print(f"    建议: {suggestion}")
            failed += 1
        except Exception as e:
            # 未预期错误：打印完整 traceback 帮助定位
            print(f"✗ {name}: 未预期错误 - {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{len(tests)} 通过")

    if failed > 0:
        print(f"失败: {failed}")
        return False

    print("所有测试通过!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)