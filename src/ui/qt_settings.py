# -*- coding: utf-8 -*-
"""PySide6 设置窗口

通过 QDialog + exec() 模态运行，与 CustomTkinter 主循环互不阻塞。
保存时直接写回 src.config.settings.settings 并持久化到 .env。
主题联动：从 ThemeManager 读取当前主题颜色生成 Qt 样式表。
"""
import os
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QGroupBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QSlider,
    QLabel, QPushButton, QHBoxLayout, QMessageBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor

from src.config.settings import settings
from src.config.theme_manager import theme_manager


def _hex_to_qcolor(hex_str: str) -> QColor:
    """将 #RRGGBB 转为 QColor"""
    h = hex_str.lstrip("#")
    if len(h) == 6:
        return QColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return QColor("#1E90FF")


def _build_stylesheet() -> str:
    """根据当前主题生成 Qt 样式表"""
    try:
        theme_manager.load_all_themes()
        theme = theme_manager.current_theme
        mode = settings.theme.lower()
        colors = theme.get_colors(mode) if theme else None
    except Exception:
        colors = None

    if colors is None:
        # 回退到默认深色
        primary = "#1E90FF"
        background = "#0A192F"
        surface = "#112240"
        text_primary = "#FFFFFF"
        border = "#2D4A6F"
    else:
        primary = colors.primary
        background = colors.background
        surface = colors.surface
        text_primary = colors.text_primary
        border = colors.border

    return f"""
        QDialog {{
            background-color: {background};
            color: {text_primary};
        }}
        QTabWidget::pane {{
            border: 1px solid {border};
            background: {surface};
        }}
        QTabBar::tab {{
            background: {background};
            color: {text_primary};
            padding: 8px 16px;
            border: 1px solid {border};
            border-bottom: none;
        }}
        QTabBar::tab:selected {{
            background: {surface};
            color: {primary};
        }}
        QGroupBox {{
            border: 1px solid {border};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background: {background};
            color: {text_primary};
            border: 1px solid {border};
            padding: 4px;
            border-radius: 4px;
        }}
        QPushButton {{
            background: {primary};
            color: white;
            border: none;
            padding: 6px 16px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background: {border};
        }}
        QCheckBox, QLabel {{
            color: {text_primary};
        }}
        QSlider::groove:horizontal {{
            border: 1px solid {border};
            height: 6px;
            background: {background};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {primary};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QScrollArea {{
            border: none;
        }}
    """


class SettingsDialog(QDialog):
    """PySide6 设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置 (PySide6)")
        self.setModal(True)
        self.resize(900, 700)

        self.setStyleSheet(_build_stylesheet())

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._setup_general_tab()
        self._setup_ai_tab()
        self._setup_network_tab()
        self._setup_security_tab()
        self._setup_interface_tab()
        self._setup_advanced_tab()

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("恢复默认")
        self.reset_btn.clicked.connect(self._reset_defaults)
        self.export_btn = QPushButton("导出设置")
        self.export_btn.clicked.connect(self._export_settings)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()

        self.save_btn = QPushButton("保存")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self._load_from_settings()

    # ───────── 各标签页 ─────────

    def _setup_general_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)

        gb_app = QGroupBox("应用")
        gb_layout = QFormLayout(gb_app)
        self.app_name_edit = QLineEdit()
        self.app_version_edit = QLineEdit()
        gb_layout.addRow("应用名称", self.app_name_edit)
        gb_layout.addRow("版本", self.app_version_edit)
        form.addRow(gb_app)

        gb_limits = QGroupBox("限制")
        gb_layout = QFormLayout(gb_limits)
        self.max_calls_spin = QSpinBox(); self.max_calls_spin.setRange(1, 1000)
        self.max_iterations_spin = QSpinBox(); self.max_iterations_spin.setRange(1, 100)
        self.iteration_delay_spin = QDoubleSpinBox(); self.iteration_delay_spin.setRange(0.1, 10.0); self.iteration_delay_spin.setSingleStep(0.1)
        gb_layout.addRow("每分钟最大调用", self.max_calls_spin)
        gb_layout.addRow("最大迭代次数", self.max_iterations_spin)
        gb_layout.addRow("迭代间隔(秒)", self.iteration_delay_spin)
        form.addRow(gb_limits)

        gb_history = QGroupBox("对话历史")
        gb_layout = QFormLayout(gb_history)
        self.max_history_spin = QSpinBox(); self.max_history_spin.setRange(10, 1000)
        self.auto_save_check = QCheckBox("自动保存")
        self.auto_save_interval_spin = QSpinBox(); self.auto_save_interval_spin.setRange(10, 3600)
        gb_layout.addRow("最大历史记录数", self.max_history_spin)
        gb_layout.addRow(self.auto_save_check)
        gb_layout.addRow("自动保存间隔(秒)", self.auto_save_interval_spin)
        form.addRow(gb_history)

        scroll.setWidget(inner)
        layout = QVBoxLayout(widget)
        layout.addWidget(scroll)
        self.tabs.addTab(widget, "通用")

    def _setup_ai_tab(self):
        widget = QWidget()
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        inner = QWidget(); form = QFormLayout(inner)

        gb_model = QGroupBox("模型")
        gb_layout = QFormLayout(gb_model)
        self.model_name_edit = QLineEdit()
        self.temperature_spin = QDoubleSpinBox(); self.temperature_spin.setRange(0.0, 2.0); self.temperature_spin.setSingleStep(0.1)
        self.top_p_spin = QDoubleSpinBox(); self.top_p_spin.setRange(0.0, 1.0); self.top_p_spin.setSingleStep(0.05)
        self.max_tokens_spin = QSpinBox(); self.max_tokens_spin.setRange(256, 65536)
        gb_layout.addRow("模型名称", self.model_name_edit)
        gb_layout.addRow("Temperature", self.temperature_spin)
        gb_layout.addRow("Top P", self.top_p_spin)
        gb_layout.addRow("Max Tokens", self.max_tokens_spin)
        form.addRow(gb_model)

        gb_thinking = QGroupBox("思考链")
        gb_layout = QFormLayout(gb_thinking)
        self.enable_thinking_check = QCheckBox("启用思考链")
        self.clear_thinking_check = QCheckBox("清除思考内容")
        gb_layout.addRow(self.enable_thinking_check)
        gb_layout.addRow(self.clear_thinking_check)
        form.addRow(gb_thinking)

        gb_provider = QGroupBox("AI 提供方")
        gb_layout = QFormLayout(gb_provider)
        self.ai_provider_combo = QComboBox(); self.ai_provider_combo.addItems(["openai", "nvidia", "azure", "local"])
        self.ai_api_key_edit = QLineEdit(); self.ai_api_key_edit.setEchoMode(QLineEdit.Password)
        self.ai_base_url_edit = QLineEdit()
        self.test_conn_btn = QPushButton("🌐 测试连接")
        self.test_conn_btn.clicked.connect(self._test_api_connection)
        self.test_conn_label = QLabel("")
        self.test_conn_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        gb_layout.addRow("提供方", self.ai_provider_combo)
        gb_layout.addRow("API Key", self.ai_api_key_edit)
        gb_layout.addRow("Base URL", self.ai_base_url_edit)
        gb_layout.addRow(self.test_conn_btn)
        gb_layout.addRow(self.test_conn_label)
        form.addRow(gb_provider)

        scroll.setWidget(inner)
        layout = QVBoxLayout(widget); layout.addWidget(scroll)
        self.tabs.addTab(widget, "AI 模型")

    def _setup_network_tab(self):
        widget = QWidget(); form = QFormLayout(widget)

        gb_server = QGroupBox("服务器")
        gb_layout = QFormLayout(gb_server)
        self.host_edit = QLineEdit()
        self.port_spin = QSpinBox(); self.port_spin.setRange(1, 65535)
        self.websocket_port_spin = QSpinBox(); self.websocket_port_spin.setRange(1, 65535)
        self.api_port_spin = QSpinBox(); self.api_port_spin.setRange(1, 65535)
        self.screen_monitor_port_spin = QSpinBox(); self.screen_monitor_port_spin.setRange(1, 65535)
        self.video_editor_port_spin = QSpinBox(); self.video_editor_port_spin.setRange(1, 65535)
        gb_layout.addRow("监听地址", self.host_edit)
        gb_layout.addRow("HTTP 端口", self.port_spin)
        gb_layout.addRow("WebSocket 端口", self.websocket_port_spin)
        gb_layout.addRow("API 端口", self.api_port_spin)
        gb_layout.addRow("屏幕监控端口", self.screen_monitor_port_spin)
        gb_layout.addRow("视频编辑器端口", self.video_editor_port_spin)
        form.addRow(gb_server)

        gb_proxy = QGroupBox("代理")
        gb_layout = QFormLayout(gb_proxy)
        self.proxy_enabled_check = QCheckBox("启用代理")
        self.proxy_url_edit = QLineEdit()
        gb_layout.addRow(self.proxy_enabled_check)
        gb_layout.addRow("代理 URL", self.proxy_url_edit)
        form.addRow(gb_proxy)

        self.tabs.addTab(widget, "网络")

    def _setup_security_tab(self):
        widget = QWidget(); form = QFormLayout(widget)

        gb_perm = QGroupBox("权限")
        gb_layout = QFormLayout(gb_perm)
        self.permission_combo = QComboBox(); self.permission_combo.addItems(["strict", "normal", "trusted"])
        gb_layout.addRow("权限级别", self.permission_combo)
        form.addRow(gb_perm)

        gb_risk = QGroupBox("高危操作二次授权")
        gb_layout = QFormLayout(gb_risk)
        self.high_risk_check = QCheckBox("启用二次授权")
        self.high_risk_timeout_spin = QSpinBox(); self.high_risk_timeout_spin.setRange(5, 300)
        self.high_risk_whitelist_edit = QLineEdit()
        self.high_risk_extra_blacklist_edit = QLineEdit()
        gb_layout.addRow(self.high_risk_check)
        gb_layout.addRow("确认超时(秒)", self.high_risk_timeout_spin)
        gb_layout.addRow("免确认命令(逗号分隔)", self.high_risk_whitelist_edit)
        gb_layout.addRow("追加黑名单关键词", self.high_risk_extra_blacklist_edit)
        form.addRow(gb_risk)

        self.tabs.addTab(widget, "安全")

    def _setup_interface_tab(self):
        widget = QWidget(); form = QFormLayout(widget)

        gb_theme = QGroupBox("主题")
        gb_layout = QFormLayout(gb_theme)
        self.theme_combo = QComboBox()
        try:
            theme_manager.load_all_themes()
            self.theme_combo.addItems(theme_manager.get_theme_names())
        except Exception:
            self.theme_combo.addItem("Default")
        self.theme_mode_combo = QComboBox(); self.theme_mode_combo.addItems(["dark", "light", "system"])
        gb_layout.addRow("主题", self.theme_combo)
        gb_layout.addRow("模式", self.theme_mode_combo)
        form.addRow(gb_theme)

        gb_ui = QGroupBox("界面选项")
        gb_layout = QFormLayout(gb_ui)
        self.enable_systray_check = QCheckBox("启用系统托盘")
        self.enable_auto_start_check = QCheckBox("开机自启动")
        self.language_combo = QComboBox(); self.language_combo.addItems(["zh_CN", "en_US"])
        self.timezone_edit = QLineEdit()
        gb_layout.addRow(self.enable_systray_check)
        gb_layout.addRow(self.enable_auto_start_check)
        gb_layout.addRow("语言", self.language_combo)
        gb_layout.addRow("时区", self.timezone_edit)
        form.addRow(gb_ui)

        self.tabs.addTab(widget, "界面")

    def _setup_advanced_tab(self):
        widget = QWidget(); form = QFormLayout(widget)

        gb_debug = QGroupBox("调试")
        gb_layout = QFormLayout(gb_debug)
        self.debug_check = QCheckBox("调试模式")
        self.log_level_combo = QComboBox(); self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.enable_file_logging_check = QCheckBox("启用文件日志")
        self.log_dir_edit = QLineEdit()
        gb_layout.addRow(self.debug_check)
        gb_layout.addRow("日志级别", self.log_level_combo)
        gb_layout.addRow(self.enable_file_logging_check)
        gb_layout.addRow("日志目录", self.log_dir_edit)
        form.addRow(gb_debug)

        gb_flags = QGroupBox("启动选项")
        gb_layout = QFormLayout(gb_flags)
        self.noui_check = QCheckBox("无 UI 模式")
        self.noweb_check = QCheckBox("禁用 Web 服务")
        self.noeditor_check = QCheckBox("禁用视频编辑器")
        self.nomonitor_check = QCheckBox("禁用屏幕监控")
        gb_layout.addRow(self.noui_check)
        gb_layout.addRow(self.noweb_check)
        gb_layout.addRow(self.noeditor_check)
        gb_layout.addRow(self.nomonitor_check)
        form.addRow(gb_flags)

        self.tabs.addTab(widget, "高级")

    # ───────── 数据读写 ─────────

    def _load_from_settings(self):
        """从 settings 读取当前值到控件"""
        s = settings
        self.app_name_edit.setText(s.app_name)
        self.app_version_edit.setText(s.app_version)
        self.max_calls_spin.setValue(s.max_calls_per_minute)
        self.max_iterations_spin.setValue(s.max_iterations)
        self.iteration_delay_spin.setValue(s.iteration_delay)
        self.max_history_spin.setValue(s.max_history)
        self.auto_save_check.setChecked(s.auto_save)
        self.auto_save_interval_spin.setValue(s.auto_save_interval)

        self.model_name_edit.setText(s.model_name)
        self.temperature_spin.setValue(s.temperature)
        self.top_p_spin.setValue(s.top_p)
        self.max_tokens_spin.setValue(s.max_tokens)
        self.enable_thinking_check.setChecked(s.enable_thinking)
        self.clear_thinking_check.setChecked(s.clear_thinking)
        self.ai_provider_combo.setCurrentText(s.ai_provider)
        self.ai_api_key_edit.setText(s.ai_api_key or "")
        self.ai_base_url_edit.setText(s.ai_base_url or "")

        self.host_edit.setText(s.host)
        self.port_spin.setValue(s.port)
        self.websocket_port_spin.setValue(s.websocket_port)
        self.api_port_spin.setValue(s.api_port)
        self.screen_monitor_port_spin.setValue(s.screen_monitor_port)
        self.video_editor_port_spin.setValue(s.video_editor_port)
        self.proxy_enabled_check.setChecked(s.proxy_enabled)
        self.proxy_url_edit.setText(s.proxy_url or "")

        self.permission_combo.setCurrentText(s.permission_level)
        self.high_risk_check.setChecked(s.high_risk_confirmation)
        self.high_risk_timeout_spin.setValue(s.high_risk_timeout)
        self.high_risk_whitelist_edit.setText(s.high_risk_whitelist)
        self.high_risk_extra_blacklist_edit.setText(s.high_risk_extra_blacklist)

        self.theme_combo.setCurrentText(s.theme_name)
        self.theme_mode_combo.setCurrentText(s.theme)
        self.enable_systray_check.setChecked(s.enable_systray)
        self.enable_auto_start_check.setChecked(s.enable_auto_start)
        self.language_combo.setCurrentText(s.language)
        self.timezone_edit.setText(s.timezone)

        self.debug_check.setChecked(s.debug)
        self.log_level_combo.setCurrentText(s.log_level)
        self.enable_file_logging_check.setChecked(s.enable_file_logging)
        self.log_dir_edit.setText(s.log_dir)
        self.noui_check.setChecked(s.noui)
        self.noweb_check.setChecked(s.noweb)
        self.noeditor_check.setChecked(s.noeditor)
        self.nomonitor_check.setChecked(s.nomonitor)

    def accept(self):
        """保存按钮：写回 settings 并持久化到 .env"""
        try:
            self._save_to_settings()
            self._persist_env()
            QMessageBox.information(self, "设置", "设置已保存")
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _save_to_settings(self):
        s = settings
        s.app_name = self.app_name_edit.text()
        s.app_version = self.app_version_edit.text()
        s.max_calls_per_minute = self.max_calls_spin.value()
        s.max_iterations = self.max_iterations_spin.value()
        s.iteration_delay = self.iteration_delay_spin.value()
        s.max_history = self.max_history_spin.value()
        s.auto_save = self.auto_save_check.isChecked()
        s.auto_save_interval = self.auto_save_interval_spin.value()

        s.model_name = self.model_name_edit.text()
        s.temperature = self.temperature_spin.value()
        s.top_p = self.top_p_spin.value()
        s.max_tokens = self.max_tokens_spin.value()
        s.enable_thinking = self.enable_thinking_check.isChecked()
        s.clear_thinking = self.clear_thinking_check.isChecked()
        s.ai_provider = self.ai_provider_combo.currentText()
        s.ai_api_key = self.ai_api_key_edit.text() or None
        s.ai_base_url = self.ai_base_url_edit.text() or None

        s.host = self.host_edit.text()
        s.port = self.port_spin.value()
        s.websocket_port = self.websocket_port_spin.value()
        s.api_port = self.api_port_spin.value()
        s.screen_monitor_port = self.screen_monitor_port_spin.value()
        s.video_editor_port = self.video_editor_port_spin.value()
        s.proxy_enabled = self.proxy_enabled_check.isChecked()
        s.proxy_url = self.proxy_url_edit.text() or None

        s.permission_level = self.permission_combo.currentText()
        s.high_risk_confirmation = self.high_risk_check.isChecked()
        s.high_risk_timeout = self.high_risk_timeout_spin.value()
        s.high_risk_whitelist = self.high_risk_whitelist_edit.text()
        s.high_risk_extra_blacklist = self.high_risk_extra_blacklist_edit.text()

        s.theme_name = self.theme_combo.currentText()
        s.theme = self.theme_mode_combo.currentText()
        s.enable_systray = self.enable_systray_check.isChecked()
        s.enable_auto_start = self.enable_auto_start_check.isChecked()
        s.language = self.language_combo.currentText()
        s.timezone = self.timezone_edit.text()

        s.debug = self.debug_check.isChecked()
        s.log_level = self.log_level_combo.currentText()
        s.enable_file_logging = self.enable_file_logging_check.isChecked()
        s.log_dir = self.log_dir_edit.text()
        s.noui = self.noui_check.isChecked()
        s.noweb = self.noweb_check.isChecked()
        s.noeditor = self.noeditor_check.isChecked()
        s.nomonitor = self.nomonitor_check.isChecked()

    def _persist_env(self):
        """将关键配置写入 .env（仅覆盖已存在的键，其余保留）"""
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".env"
        )
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        updates = {
            "APP_NAME": settings.app_name,
            "MODEL_NAME": settings.model_name,
            "TEMPERATURE": str(settings.temperature),
            "TOP_P": str(settings.top_p),
            "MAX_TOKENS": str(settings.max_tokens),
            "ENABLE_THINKING": str(settings.enable_thinking).lower(),
            "CLEAR_THINKING": str(settings.clear_thinking).lower(),
            "AI_PROVIDER": settings.ai_provider,
            "AI_API_KEY": settings.ai_api_key or "",
            "AI_BASE_URL": settings.ai_base_url or "",
            "HOST": settings.host,
            "PORT": str(settings.port),
            "WEBSOCKET_PORT": str(settings.websocket_port),
            "API_PORT": str(settings.api_port),
            "SCREEN_MONITOR_PORT": str(settings.screen_monitor_port),
            "VIDEO_EDITOR_PORT": str(settings.video_editor_port),
            "PROXY_ENABLED": str(settings.proxy_enabled).lower(),
            "PROXY_URL": settings.proxy_url or "",
            "PERMISSION_LEVEL": settings.permission_level,
            "HIGH_RISK_CONFIRMATION": str(settings.high_risk_confirmation).lower(),
            "HIGH_RISK_TIMEOUT": str(settings.high_risk_timeout),
            "HIGH_RISK_WHITELIST": settings.high_risk_whitelist,
            "HIGH_RISK_EXTRA_BLACKLIST": settings.high_risk_extra_blacklist,
            "THEME_NAME": settings.theme_name,
            "THEME": settings.theme,
            "ENABLE_SYSTRAY": str(settings.enable_systray).lower(),
            "ENABLE_AUTO_START": str(settings.enable_auto_start).lower(),
            "LANGUAGE": settings.language,
            "TIMEZONE": settings.timezone,
            "DEBUG": str(settings.debug).lower(),
            "LOG_LEVEL": settings.log_level,
            "ENABLE_FILE_LOGGING": str(settings.enable_file_logging).lower(),
            "LOG_DIR": settings.log_dir,
            "NOUI": str(settings.noui).lower(),
            "NOWEB": str(settings.noweb).lower(),
            "NOEDITOR": str(settings.noeditor).lower(),
            "NOMONITOR": str(settings.nomonitor).lower(),
            "MAX_CALLS_PER_MINUTE": str(settings.max_calls_per_minute),
            "MAX_ITERATIONS": str(settings.max_iterations),
            "ITERATION_DELAY": str(settings.iteration_delay),
            "MAX_HISTORY": str(settings.max_history),
            "AUTO_SAVE": str(settings.auto_save).lower(),
            "AUTO_SAVE_INTERVAL": str(settings.auto_save_interval),
        }

        existing = {line.split("=", 1)[0].strip(): line for line in lines if "=" in line}
        written = set()
        new_lines = []
        for line in lines:
            if "=" in line:
                key = line.split("=", 1)[0].strip()
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}\n")
                    written.add(key)
                    continue
            new_lines.append(line)
        for key, val in updates.items():
            if key not in written:
                new_lines.append(f"{key}={val}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def _reset_defaults(self):
        reply = QMessageBox.question(self, "恢复默认", "确定要恢复所有设置为默认值吗？")
        if reply == QMessageBox.Yes:
            from src.config.settings import Settings
            defaults = Settings()
            self._load_from_settings_obj(defaults)

    def _test_api_connection(self):
        """测试当前 AI 提供方的 API 连通性"""
        from src.config.ai_providers import AIProvider
        from src.services.api_connectivity import check_api_connectivity

        # 用当前输入构建临时 provider（不修改全局配置）
        provider = AIProvider(
            name=self.ai_provider_combo.currentText(),
            base_url=self.ai_base_url_edit.text().strip(),
            api_key=self.ai_api_key_edit.text().strip(),
            default_model=self.model_name_edit.text().strip() or "gpt-3.5-turbo",
        )

        self.test_conn_btn.setEnabled(False)
        self.test_conn_label.setText("正在测试...")
        self.test_conn_label.setStyleSheet("color: #F59E0B;")
        # 强制刷新 UI
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            result = check_api_connectivity(provider, timeout=10)
            if result["success"]:
                self.test_conn_label.setStyleSheet("color: #10B981;")
                self.test_conn_label.setText(f"✓ {result['message']} ({result.get('response_time_ms', 0):.0f}ms)")
            else:
                self.test_conn_label.setStyleSheet("color: #EF4444;")
                self.test_conn_label.setText(f"✗ {result['message']}")
        except Exception as e:
            self.test_conn_label.setStyleSheet("color: #EF4444;")
            self.test_conn_label.setText(f"✗ 测试异常: {e}")
        finally:
            self.test_conn_btn.setEnabled(True)

    def _load_from_settings_obj(self, s):
        """从任意 Settings 对象加载（用于恢复默认）"""
        self.app_name_edit.setText(s.app_name)
        self.app_version_edit.setText(s.app_version)
        self.max_calls_spin.setValue(s.max_calls_per_minute)
        self.max_iterations_spin.setValue(s.max_iterations)
        self.iteration_delay_spin.setValue(s.iteration_delay)
        self.max_history_spin.setValue(s.max_history)
        self.auto_save_check.setChecked(s.auto_save)
        self.auto_save_interval_spin.setValue(s.auto_save_interval)
        self.model_name_edit.setText(s.model_name)
        self.temperature_spin.setValue(s.temperature)
        self.top_p_spin.setValue(s.top_p)
        self.max_tokens_spin.setValue(s.max_tokens)
        self.enable_thinking_check.setChecked(s.enable_thinking)
        self.clear_thinking_check.setChecked(s.clear_thinking)
        self.ai_provider_combo.setCurrentText(s.ai_provider)
        self.ai_api_key_edit.setText(s.ai_api_key or "")
        self.ai_base_url_edit.setText(s.ai_base_url or "")
        self.host_edit.setText(s.host)
        self.port_spin.setValue(s.port)
        self.websocket_port_spin.setValue(s.websocket_port)
        self.api_port_spin.setValue(s.api_port)
        self.screen_monitor_port_spin.setValue(s.screen_monitor_port)
        self.video_editor_port_spin.setValue(s.video_editor_port)
        self.proxy_enabled_check.setChecked(s.proxy_enabled)
        self.proxy_url_edit.setText(s.proxy_url or "")
        self.permission_combo.setCurrentText(s.permission_level)
        self.high_risk_check.setChecked(s.high_risk_confirmation)
        self.high_risk_timeout_spin.setValue(s.high_risk_timeout)
        self.high_risk_whitelist_edit.setText(s.high_risk_whitelist)
        self.high_risk_extra_blacklist_edit.setText(s.high_risk_extra_blacklist)
        self.theme_combo.setCurrentText(s.theme_name)
        self.theme_mode_combo.setCurrentText(s.theme)
        self.enable_systray_check.setChecked(s.enable_systray)
        self.enable_auto_start_check.setChecked(s.enable_auto_start)
        self.language_combo.setCurrentText(s.language)
        self.timezone_edit.setText(s.timezone)
        self.debug_check.setChecked(s.debug)
        self.log_level_combo.setCurrentText(s.log_level)
        self.enable_file_logging_check.setChecked(s.enable_file_logging)
        self.log_dir_edit.setText(s.log_dir)
        self.noui_check.setChecked(s.noui)
        self.noweb_check.setChecked(s.noweb)
        self.noeditor_check.setChecked(s.noeditor)
        self.nomonitor_check.setChecked(s.nomonitor)

    def _export_settings(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "导出设置", "settings_export.json", "JSON Files (*.json)")
        if path:
            import json
            data = settings.model_dump()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "导出", f"已导出到 {path}")


# ───────── 便捷入口 ─────────

def show_settings(parent=None) -> bool:
    """显示设置对话框，返回是否点击了保存"""
    dialog = SettingsDialog(parent)
    return dialog.exec() == QDialog.Accepted


def apply_qt_theme():
    """向主程序注册：在主题切换后调用，刷新 Qt 样式表"""
    # 主程序可在主题切换后调用此函数，但当前实现为每次打开窗口时动态读取，
    # 因此无需额外注册。保留接口以便后续扩展。
    pass
