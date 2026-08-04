#!/usr/bin/env python
"""
GL Effects 编译脚本
使用MinGW工具链编译生成32位和64位DLL文件
"""

import os
import subprocess
import sys
import platform

def run_command(cmd, cwd=None):
    """执行命令并返回结果"""
    print(f"执行命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"命令执行失败: {e}")
        return False

def build():
    """执行编译"""
    system = platform.system()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("GL Effects 编译脚本")
    print("=" * 60)
    print(f"操作系统: {system}")
    print(f"工作目录: {script_dir}")
    print()
    
    # 检查CMake是否安装
    if not run_command("cmake --version"):
        print("错误: CMake 未安装，请先安装 CMake")
        return False
    
    # 创建构建目录
    build_dir_32 = os.path.join(script_dir, "build", "win32")
    build_dir_64 = os.path.join(script_dir, "build", "win64")
    
    os.makedirs(build_dir_32, exist_ok=True)
    os.makedirs(build_dir_64, exist_ok=True)
    
    # 编译32位版本
    print("\n" + "=" * 60)
    print("编译32位版本")
    print("=" * 60)
    
    os.chdir(build_dir_32)
    if not run_command('cmake -G "MinGW Makefiles" -DCMAKE_C_FLAGS=-m32 -DCMAKE_CXX_FLAGS=-m32 ..'):
        print("错误: CMake配置失败 (32位)")
        return False
    
    if not run_command("mingw32-make"):
        print("错误: 编译失败 (32位)")
        return False
    
    # 编译64位版本
    print("\n" + "=" * 60)
    print("编译64位版本")
    print("=" * 60)
    
    os.chdir(build_dir_64)
    if not run_command('cmake -G "MinGW Makefiles" -DCMAKE_C_FLAGS=-m64 -DCMAKE_CXX_FLAGS=-m64 ..'):
        print("错误: CMake配置失败 (64位)")
        return False
    
    if not run_command("mingw32-make"):
        print("错误: 编译失败 (64位)")
        return False
    
    # 复制DLL文件到输出目录
    print("\n" + "=" * 60)
    print("复制DLL文件")
    print("=" * 60)
    
    output_dir = os.path.join(script_dir, "bin")
    os.makedirs(output_dir, exist_ok=True)
    
    dll_32 = os.path.join(build_dir_32, "libgl_effects.dll")
    dll_64 = os.path.join(build_dir_64, "libgl_effects.dll")
    
    if os.path.exists(dll_32):
        run_command(f"copy \"{dll_32}\" \"{os.path.join(output_dir, 'gl_effects_x86.dll')}\"")
    else:
        print("警告: 32位DLL文件不存在")
    
    if os.path.exists(dll_64):
        run_command(f"copy \"{dll_64}\" \"{os.path.join(output_dir, 'gl_effects_x64.dll')}\"")
    else:
        print("警告: 64位DLL文件不存在")
    
    print("\n" + "=" * 60)
    print("编译完成!")
    print("=" * 60)
    print(f"DLL文件位置: {output_dir}")
    
    return True

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)