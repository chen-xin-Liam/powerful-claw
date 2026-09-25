#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档相对链接校验器

扫描仓库内所有 Markdown 文件中的相对链接（含图片），验证目标文件是否存在。
纯标准库实现，可在本地与 CI 中直接运行：

    python scripts/check_doc_links.py

退出码：0 = 全部有效；1 = 存在失效链接。
"""
import os
import re
import sys
import urllib.parse

# 扫描范围
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["docs", ".github", "config", "userspick"]
SCAN_FILES = ["README.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE"]
EXCLUDE_DIRS = {".git", "venv", "__pycache__", ".pytest_cache", ".trae", "node_modules", "build", "dist"}

# Markdown 链接/图片：[text](target) 与 ![alt](target)
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def iter_markdown_files():
    """枚举需要检查的 Markdown 文件。"""
    for name in SCAN_FILES:
        path = os.path.join(ROOT, name)
        if name.endswith(".md") and os.path.isfile(path):
            yield path
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in EXCLUDE_DIRS]
            for fn in filenames:
                if fn.lower().endswith(".md"):
                    yield os.path.join(dirpath, fn)


def check_file(md_path: str):
    """检查单个文件，返回失效链接 [(target, line_no), ...]。"""
    broken = []
    with open(md_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            for raw_target in LINK_RE.findall(line):
                target = raw_target.strip()
                # 跳过：网页链接、锚点、邮件链接、占位符
                if (target.startswith(("http://", "https://", "#", "mailto:"))
                        or target in ("...", "") or ":" in target.split("/")[0] and target[0].islower() and "://" not in target and target.split(":")[0] not in ("docs")):
                    continue
                # 分离锚点
                path_part, _, _anchor = target.partition("#")
                if not path_part:
                    continue
                path_part = urllib.parse.unquote(path_part)
                resolved = os.path.normpath(os.path.join(os.path.dirname(md_path), path_part))
                if not os.path.exists(resolved):
                    broken.append((raw_target, lineno))
    return broken


def main():
    total_files = 0
    total_broken = 0
    for md_path in sorted(set(iter_markdown_files())):
        total_files += 1
        broken = check_file(md_path)
        if broken:
            rel = os.path.relpath(md_path, ROOT)
            for target, lineno in broken:
                print(f"BROKEN  {rel}:{lineno}  ->  {target}")
                total_broken += 1

    print(f"\nChecked {total_files} markdown files, {total_broken} broken link(s).")
    return 1 if total_broken else 0


if __name__ == "__main__":
    sys.exit(main())
