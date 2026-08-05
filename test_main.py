#!/usr/bin/env python
"""
AIclaw 主程序测试脚本
验证所有核心功能模块是否正常工作
"""

import sys
import os
import traceback
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

def main():
    """运行所有测试"""
    print("=" * 60)
    print("AIclaw 完整功能测试")
    print("=" * 60)
    
    tests = [
        ("系统监控", test_system_monitor),
        ("集群管理器", test_cluster_manager),
        ("UI视觉特效", test_ui_effects),
        ("AI代理系统", test_ai_agent),
        ("配置模块", test_config),
        ("屏幕监控", test_screen_monitor),
        ("API服务器", test_api_server),
        ("WebSocket服务器", test_websocket_server),
    ]
    
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