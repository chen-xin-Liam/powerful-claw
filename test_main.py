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