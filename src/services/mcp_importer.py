# -*- coding: utf-8 -*-
"""标准 MCP 配置便捷导入

支持业界通用的 MCP 配置文件格式，一键导入为本项目的扩展配置：

  1. **标准 .mcp.json**（mcp.json 根级 "mcpServers" 键）
     Claude Desktop / Cline / Continue / Cursor 等通用：
     ```json
     {
       "mcpServers": {
         "filesystem": {
           "command": "npx",
           "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:/"],
           "env": {"FOO": "bar"},
           "disabled": false
         }
       }
     }
     ```

  2. **VS Code**（.vscode/mcp.json，根级 "servers" 键）
     ```json
     {
       "servers": {
         "github": {
           "type": "stdio",
           "command": "npx",
           "args": ["-y", "@modelcontextprotocol/server-github"],
           "env": {"GITHUB_TOKEN": "..."}
         }
       }
     }
     ```

  3. **Claude Desktop**（claude_desktop_config.json，同 .mcp.json 格式）

导入后写入 src/config/extension_config.json，由 ExtensionManager 加载。
"""
import json
import os
from typing import Dict, List, Any, Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ───────── 格式识别与解析 ─────────

def _detect_format(data: dict) -> Optional[str]:
    """识别 MCP 配置格式，返回 'mcpServers' / 'servers' / None"""
    if isinstance(data.get("mcpServers"), dict):
        return "mcpServers"
    if isinstance(data.get("servers"), dict):
        return "servers"
    return None


def _normalize_server(name: str, raw: dict) -> Tuple[Optional[dict], Optional[str]]:
    """把不同格式的单个服务器配置统一为内部格式。

    返回 (config_dict, error)。仅支持 stdio（command+args）类型；
    sse/http 远程类型当前不支持，返回错误说明。
    """
    # VS Code 的 type 字段；标准 .mcp.json 无 type（默认 stdio）
    server_type = raw.get("type", "stdio")
    if server_type not in ("stdio",):
        return None, f"暂不支持的传输类型 '{server_type}'（仅支持 stdio 子进程）"

    command = raw.get("command")
    if not command:
        return None, "缺少 command 字段"

    config = {
        "name": name,
        "command": command,
        "args": list(raw.get("args", [])),
        "env": dict(raw.get("env", {})),
        # 标准 .mcp.json 用 "disabled"，内部用 "enabled"
        "enabled": not bool(raw.get("disabled", False)) if "disabled" in raw
                   else bool(raw.get("enabled", True)),
        "auto_reconnect": True,
        "reconnect_interval": 5,
        "max_reconnect_attempts": 3,
    }
    return config, None


def parse_mcp_config(path: str) -> Tuple[List[dict], List[Tuple[str, str]]]:
    """解析标准 MCP 配置文件。

    返回 (成功列表, 失败列表[(name, 原因)])。
    文件不存在或格式非法时抛 ValueError。
    """
    if not os.path.exists(path):
        raise ValueError(f"配置文件不存在: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")

    fmt = _detect_format(data)
    if fmt is None:
        raise ValueError("未识别的 MCP 配置格式（需要 'mcpServers' 或 'servers' 键）")

    servers = data[fmt]
    ok, failed = [], []
    for name, raw in servers.items():
        if not isinstance(raw, dict):
            failed.append((name, "配置不是对象"))
            continue
        config, err = _normalize_server(name, raw)
        if err:
            failed.append((name, err))
        else:
            ok.append(config)
    return ok, failed


# ───────── 导入到扩展管理器 ─────────

def import_mcp_config(path: str, overwrite: bool = True, save: bool = True) -> Dict[str, Any]:
    """从标准 MCP 配置文件导入服务器定义。

    参数:
        path: 配置文件路径（.mcp.json / claude_desktop_config.json / VS Code mcp.json）
        overwrite: 同名服务器是否覆盖
        save: 导入后是否立即保存到 extension_config.json

    返回导入报告 {imported, skipped, failed, total}。
    """
    from src.services.extension_manager import ExtensionManager
    em = ExtensionManager()

    configs, failed = parse_mcp_config(path)
    existing = {c["name"] for c in em._mcp_configs}

    imported, skipped = [], []
    for cfg in configs:
        name = cfg["name"]
        if name in existing and not overwrite:
            skipped.append(name)
            continue
        # 覆盖：先移除旧配置
        if name in existing:
            em.remove_mcp_server(name)
        em._mcp_configs.append(cfg)
        imported.append(name)
        logger.info(f"已导入 MCP 服务器 '{name}' ({cfg['command']})")

    if save and imported:
        em._save_config()

    return {
        "imported": imported,
        "skipped": skipped,
        "failed": [{"name": n, "reason": r} for n, r in failed],
        "total": len(configs),
    }


# ───────── 常用工具的预置模板 ─────────

POPULAR_MCP_TEMPLATES: Dict[str, dict] = {
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        "description": "文件系统访问（读写本地目录）",
    },
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_TOKEN": "<在此填入你的 GitHub Token>"},
        "description": "GitHub 仓库操作",
    },
    "fetch": {
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "description": "网页抓取",
    },
    "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "description": "持久化记忆存储",
    },
    "sqlite": {
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", "data.db"],
        "description": "SQLite 数据库查询",
    },
    "puppeteer": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "description": "浏览器自动化",
    },
}


def add_from_template(template_name: str, **overrides) -> Dict[str, Any]:
    """按预置模板快速添加一个 MCP 服务器。

    参数:
        template_name: POPULAR_MCP_TEMPLATES 中的键
        **overrides: 覆盖模板字段（args/env/enabled 等）

    返回添加结果字典。
    """
    if template_name not in POPULAR_MCP_TEMPLATES:
        return {"success": False, "error": f"未知模板 '{template_name}'，"
                f"可用: {', '.join(POPULAR_MCP_TEMPLATES)}"}

    tpl = POPULAR_MCP_TEMPLATES[template_name]
    config = {
        "name": template_name,
        "command": tpl["command"],
        "args": list(tpl["args"]),
        "env": dict(tpl.get("env", {})),
        "enabled": True,
        "auto_reconnect": True,
        "reconnect_interval": 5,
        "max_reconnect_attempts": 3,
    }
    # 应用覆盖
    for key, val in overrides.items():
        if key == "env" and isinstance(val, dict):
            config["env"].update(val)
        elif key in config:
            config[key] = val

    from src.services.extension_manager import ExtensionManager
    em = ExtensionManager()
    if config["name"] in {c["name"] for c in em._mcp_configs}:
        em.remove_mcp_server(config["name"])
    em._mcp_configs.append(config)
    em._save_config()
    logger.info(f"已通过模板添加 MCP 服务器 '{config['name']}'")
    return {"success": True, "name": config["name"], "config": config}


def list_templates() -> List[Dict[str, str]]:
    """列出所有预置模板（名称 + 描述）。"""
    return [
        {"name": name, "description": tpl.get("description", ""),
         "command": tpl["command"], "args": " ".join(tpl["args"])}
        for name, tpl in POPULAR_MCP_TEMPLATES.items()
    ]


# ───────── 命令行入口 ─────────

def _cli():
    """python -m src.services.mcp_importer <config.json> [--no-save]"""
    import argparse
    parser = argparse.ArgumentParser(description="导入标准 MCP 配置")
    parser.add_argument("config", nargs="?", help="MCP 配置文件路径")
    parser.add_argument("--no-save", action="store_true", help="只解析不保存")
    parser.add_argument("--no-overwrite", action="store_true", help="不覆盖同名服务器")
    parser.add_argument("--templates", action="store_true", help="列出预置模板")
    args = parser.parse_args()

    if args.templates:
        print("可用 MCP 模板:")
        for t in list_templates():
            print(f"  {t['name']:<12} {t['command']} {t['args']:<45} # {t['description']}")
        return 0

    if not args.config:
        parser.error("需要提供配置文件路径，或使用 --templates 查看模板")

    try:
        report = import_mcp_config(
            args.config,
            overwrite=not args.no_overwrite,
            save=not args.no_save,
        )
    except ValueError as e:
        print(f"导入失败: {e}")
        return 1

    print(f"导入完成: 成功 {len(report['imported'])}, "
          f"跳过 {len(report['skipped'])}, 失败 {len(report['failed'])}")
    for name in report["imported"]:
        print(f"  ✅ {name}")
    for name in report["skipped"]:
        print(f"  ⏭️  {name} (已存在)")
    for item in report["failed"]:
        print(f"  ❌ {item['name']}: {item['reason']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
