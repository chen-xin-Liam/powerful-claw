# -*- coding: utf-8 -*-
"""
上传到 Git 前的一键清理脚本。

默认执行（dry-run）只列出将清理的项，不真正删除。
加 --apply 才真正执行。

清理内容：
  1. Python 缓存：__pycache__、*.pyc、.pytest_cache
  2. 运行日志：logs/*.log
  3. 构建产物：build/、dist/、src/core/native/build/、*.dll、*.o
  4. 主题缓存：config/themes/.cache/
  5. 隐私会话数据：conversations.json（仅从 git 索引移除，保留本地文件）
  6. 开发杂项：.trae/、.vscode/、venv/

用法：
  python scripts/clean_for_git.py          # 预览（dry-run）
  python scripts/clean_for_git.py --apply  # 实际清理
  python scripts/clean_for_git.py --apply --keep-venv  # 保留虚拟环境
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON_CACHE = {"__pycache__", ".pytest_cache"}
BUILD_DIRS = {"build", "dist"}
EXTRA_DIR_PATTERNS = [".trae", ".vscode"]
NATIVE_DLL = Path("src/core/native/nodecalc_native.dll")
PRIVACY_TRACKED = ["conversations.json"]  # 保留本地但应从仓库索引移除


def iter_targets(keep_venv: bool):
    """返回 (绝对路径, 描述) 的生成器。"""
    for dirpath, dirnames, filenames in __import__("os").walk(ROOT):
        p = Path(dirpath)
        parts = set(p.parts)
        # 跳过 venv（除非用户明确 --include-venv）
        if not keep_venv and "venv" in parts:
            dirnames[:] = []
            continue
        # 删除匹配目录
        for d in list(dirnames):
            full = p / d
            rel = full.relative_to(ROOT)
            if d in PYTHON_CACHE:
                yield full, f"Python 缓存目录 {rel}"
                dirnames.remove(d)
            elif d in BUILD_DIRS:
                yield full, f"构建产物目录 {rel}"
                dirnames.remove(d)
            elif d in EXTRA_DIR_PATTERNS:
                yield full, f"开发杂项目录 {rel}"
                dirnames.remove(d)
        # 删除匹配文件
        for f in filenames:
            full = p / f
            rel = full.relative_to(ROOT)
            if f.endswith((".pyc", ".pyo")):
                yield full, f"Python 缓存文件 {rel}"
            elif f.endswith(".log") and p.name == "logs":
                yield full, f"运行日志 {rel}"
            elif f.endswith(".dll") and "native" in str(rel):
                yield full, f"原生编译产物 {rel}"
            elif f.endswith((".o", ".obj")):
                yield full, f"编译中间产物 {rel}"


def remove_git_track(path: str):
    """把 path 从 git 索引移除（保留本地文件）。"""
    result = subprocess.run(
        ["git", "rm", "--cached", "--quiet", path],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="上传 git 前清理无用/隐私数据")
    parser.add_argument("--apply", action="store_true", help="实际执行删除（默认 dry-run）")
    parser.add_argument("--keep-venv", action="store_true", help="保留 venv 虚拟环境")
    args = parser.parse_args()

    targets = list(iter_targets(args.keep_venv))
    if not targets:
        print("没有可清理的文件。")
    else:
        print(f"{'[DRY-RUN] ' if not args.apply else ''}共找到 {len(targets)} 项：")
        total = 0
        for path, desc in sorted(targets):
            try:
                size = sum(f.stat().st_size for f in path.rglob("*")) if path.is_dir() else path.stat().st_size
            except OSError:
                size = 0
            total += size
            print(f"  - {desc}  ({size / 1024:.1f} KB)")
        print(f"合计约 {total / 1024 / 1024:.2f} MB")

    # 隐私文件处理
    for fname in PRIVACY_TRACKED:
        p = ROOT / fname
        if not p.exists():
            continue
        print(f"\n[隐私] {fname} 当前在 git 追踪中。")
        if args.apply:
            if remove_git_track(fname):
                print(f"  已执行 `git rm --cached {fname}`（本地文件保留，请加入 .gitignore）")
            else:
                print("  git rm --cached 失败，请手动处理")
        else:
            print(f"  dry-run 未改动。执行 `--apply` 将运行 `git rm --cached {fname}`")

    if not args.apply:
        print("\n这是预览模式，未删除任何文件。加 `--apply` 真正执行。")
    else:
        print("\n清理完成。")


if __name__ == "__main__":
    sys.exit(main())
