"""MCP 标准配置导入测试

- 格式识别（.mcp.json / VS Code servers）
- stdio 服务器解析与规范化
- 不支持的传输类型拒绝
- 导入到扩展配置（含覆盖/跳过逻辑）
- 预置模板添加
"""
import json
import os
import tempfile

import pytest

from src.services.mcp_importer import (
    parse_mcp_config,
    import_mcp_config,
    add_from_template,
    list_templates,
    POPULAR_MCP_TEMPLATES,
)


# ───────── parse_mcp_config ─────────

class TestParseMcpConfig:
    def _write(self, data: dict) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, f)
        f.close()
        return f.name

    def test_standard_mcpservers_format(self):
        path = self._write({
            "mcpServers": {
                "fs": {"command": "npx", "args": ["-y", "server"], "env": {"A": "1"}},
            }
        })
        ok, failed = parse_mcp_config(path)
        os.unlink(path)
        assert len(ok) == 1
        assert len(failed) == 0
        assert ok[0]["name"] == "fs"
        assert ok[0]["command"] == "npx"
        assert ok[0]["args"] == ["-y", "server"]
        assert ok[0]["env"] == {"A": "1"}
        assert ok[0]["enabled"] is True

    def test_vscode_servers_format(self):
        path = self._write({
            "servers": {
                "gh": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "github"],
                }
            }
        })
        ok, failed = parse_mcp_config(path)
        os.unlink(path)
        assert len(ok) == 1
        assert ok[0]["name"] == "gh"
        assert ok[0]["enabled"] is True

    def test_disabled_field_inverts(self):
        path = self._write({
            "mcpServers": {
                "off": {"command": "npx", "disabled": True},
            }
        })
        ok, failed = parse_mcp_config(path)
        os.unlink(path)
        assert ok[0]["enabled"] is False

    def test_unsupported_transport(self):
        path = self._write({
            "mcpServers": {
                "remote": {"type": "sse", "url": "http://x"},
            }
        })
        ok, failed = parse_mcp_config(path)
        os.unlink(path)
        assert len(ok) == 0
        assert len(failed) == 1
        assert "stdio" in failed[0][1]

    def test_missing_command(self):
        path = self._write({"mcpServers": {"bad": {}}})
        ok, failed = parse_mcp_config(path)
        os.unlink(path)
        assert len(failed) == 1
        assert "command" in failed[0][1]

    def test_file_not_found(self):
        with pytest.raises(ValueError, match="不存在"):
            parse_mcp_config("nonexistent_xyz.json")

    def test_invalid_json(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        f.write("{not json")
        f.close()
        with pytest.raises(ValueError, match="JSON"):
            parse_mcp_config(f.name)
        os.unlink(f.name)

    def test_unrecognized_format(self):
        path = self._write({"random": {}})
        with pytest.raises(ValueError, match="未识别"):
            parse_mcp_config(path)
        os.unlink(path)


# ───────── import_mcp_config ─────────

class TestImportMcpConfig:
    def _write(self, data: dict) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, f)
        f.close()
        return f.name

    def test_import_and_cleanup(self):
        path = self._write({
            "mcpServers": {
                "test-import": {"command": "echo", "args": ["hi"]},
            }
        })
        report = import_mcp_config(path, save=False)
        os.unlink(path)
        assert "test-import" in report["imported"]
        assert len(report["failed"]) == 0

        # 清理
        from src.services.extension_manager import ExtensionManager
        ExtensionManager().remove_mcp_server("test-import")

    def test_import_overwrite(self):
        path = self._write({
            "mcpServers": {
                "test-ow": {"command": "old"},
            }
        })
        import_mcp_config(path, save=False)
        os.unlink(path)

        # 覆盖
        path2 = self._write({
            "mcpServers": {
                "test-ow": {"command": "new"},
            }
        })
        report = import_mcp_config(path2, overwrite=True, save=False)
        os.unlink(path2)
        assert "test-ow" in report["imported"]

        from src.services.extension_manager import ExtensionManager
        ExtensionManager().remove_mcp_server("test-ow")

    def test_import_skip_existing(self):
        path = self._write({
            "mcpServers": {
                "test-skip": {"command": "old"},
            }
        })
        import_mcp_config(path, save=False)
        os.unlink(path)

        path2 = self._write({
            "mcpServers": {
                "test-skip": {"command": "new"},
            }
        })
        report = import_mcp_config(path2, overwrite=False, save=False)
        os.unlink(path2)
        assert "test-skip" in report["skipped"]

        from src.services.extension_manager import ExtensionManager
        ExtensionManager().remove_mcp_server("test-skip")


# ───────── add_from_template ─────────

class TestAddFromTemplate:
    def test_add_fetch_template(self):
        r = add_from_template("fetch")
        assert r["success"] is True
        assert r["name"] == "fetch"
        from src.services.extension_manager import ExtensionManager
        ExtensionManager().remove_mcp_server("fetch")

    def test_add_unknown_template(self):
        r = add_from_template("nonexistent_xyz")
        assert r["success"] is False
        assert "可用" in r["error"]

    def test_add_with_env_override(self):
        r = add_from_template("github", env={"GITHUB_TOKEN": "tok123"})
        assert r["success"] is True
        assert r["config"]["env"]["GITHUB_TOKEN"] == "tok123"
        from src.services.extension_manager import ExtensionManager
        ExtensionManager().remove_mcp_server("github")

    def test_add_with_args_override(self):
        r = add_from_template("filesystem", args=["-y", "server", "D:/mydir"])
        assert r["config"]["args"] == ["-y", "server", "D:/mydir"]
        from src.services.extension_manager import ExtensionManager
        ExtensionManager().remove_mcp_server("filesystem")


# ───────── list_templates ─────────

class TestListTemplates:
    def test_returns_all_templates(self):
        templates = list_templates()
        assert len(templates) == len(POPULAR_MCP_TEMPLATES)
        names = {t["name"] for t in templates}
        assert "filesystem" in names
        assert "github" in names
        assert "fetch" in names
