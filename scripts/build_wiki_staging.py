#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 GitHub Wiki 同步用的暂存目录

GitHub Wiki 与普通仓库的链接规则不同：
  - Wiki 不支持子目录网页路由（/wiki/zh/INDEX 返回 502）
  - 子目录文件会被扁平化为页面名：zh/INDEX.md -> 页面 "zh-INDEX"（/wiki/zh-INDEX 可访问）
  - 页面间链接必须是无扩展名的 wiki 链接：[x](zh-INDEX)

本脚本把 docs/ 复制到暂存目录并完成：
  1. 扁平化：lang/NAME.md -> lang-NAME.md（Home.md 保留在根作为 Wiki 首页）
  2. 重写 docs 内部的 .md 相对链接为 wiki 链接（去掉 .md，路径分隔符改为 -）
  3. 指向 docs 之外的链接（../../CONTRIBUTING.md、../../LICENSE 等）改为
     仓库 blob/main 完整 URL
  4. 外部 http(s) 链接、纯锚点保持不变

源码 docs/ 不做任何修改，仓库内浏览与 scripts/check_doc_links.py 校验照常工作。

用法：
    python scripts/build_wiki_staging.py <docs_dir> <staging_dir>
"""
import os
import re
import shutil
import sys
import urllib.parse

REPO_URL = "https://github.com/chen-xin-Liam/powerful-claw"

# Markdown 链接/图片：[text](target) 与 ![alt](target)
LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")


def flatten_name(rel_posix: str) -> str:
    """docs 内相对路径 -> 扁平 wiki 页面名（去扩展名，分隔符替换为 -）。"""
    if rel_posix.endswith(".md"):
        rel_posix = rel_posix[:-3]
    return rel_posix.replace("/", "-")


def rewrite_target(target: str, src_file: str, docs_dir: str) -> str:
    """重写单个链接目标。src_file/docs_dir 为绝对路径。"""
    # 外部链接、协议链接、纯锚点
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return target

    path_part, sep, anchor = target.partition("#")
    if not path_part:
        return target

    path_part = urllib.parse.unquote(path_part)
    resolved = os.path.normpath(os.path.join(os.path.dirname(src_file), path_part))
    docs_dir = os.path.normpath(docs_dir)

    if resolved.startswith(docs_dir + os.sep) or resolved == docs_dir:
        # docs 内部链接：指向 docs 根目录时落到 Wiki 首页 Home
        if resolved == docs_dir:
            wiki_page = "Home"
        else:
            rel = os.path.relpath(resolved, docs_dir).replace(os.sep, "/")
            wiki_page = flatten_name(rel)
        return wiki_page + (("#" + anchor) if sep else "")

    # docs 之外（仓库根的 README/CONTRIBUTING/SECURITY/LICENSE、config/ 等）
    repo_root = os.path.dirname(docs_dir)
    if resolved.startswith(repo_root + os.sep) or resolved == repo_root:
        if resolved == repo_root:
            url = REPO_URL
        else:
            rel = os.path.relpath(resolved, repo_root).replace(os.sep, "/")
            url = f"{REPO_URL}/blob/main/{urllib.parse.quote(rel)}"
        return url + (("#" + anchor) if sep else "")

    # 无法定位的相对链接原样保留
    return target


def main():
    if len(sys.argv) != 3:
        print("usage: build_wiki_staging.py <docs_dir> <staging_dir>")
        return 2

    docs_dir = os.path.abspath(sys.argv[1])
    staging = os.path.abspath(sys.argv[2])

    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    count = 0
    for dirpath, _dirnames, filenames in os.walk(docs_dir):
        for fn in filenames:
            if not fn.lower().endswith(".md"):
                continue
            src = os.path.join(dirpath, fn)
            rel = os.path.relpath(src, docs_dir).replace(os.sep, "/")

            with open(src, "r", encoding="utf-8") as f:
                content = f.read()

            # Home.md 保留在 wiki 根；其余扁平化
            out_name = "Home.md" if rel == "Home.md" else flatten_name(rel) + ".md"

            def _sub(m):
                prefix, target, suffix = m.group(1), m.group(2), m.group(3)
                return prefix + rewrite_target(target, src, docs_dir) + suffix

            content = LINK_RE.sub(_sub, content)

            with open(os.path.join(staging, out_name), "w", encoding="utf-8") as f:
                f.write(content)
            count += 1

    print(f"Wiki staging: {count} pages -> {staging}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
