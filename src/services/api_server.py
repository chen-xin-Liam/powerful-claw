import asyncio
import websockets
import json
import threading
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings
from src.services.ai_service import AIService
from src.services.extension_manager import extension_manager
from src.services.screen_monitor import screen_monitor

class HTTPServerHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def __init__(self, web_dir, monitor_dir, *args, **kwargs):
        self.web_dir = web_dir
        self.monitor_dir = monitor_dir
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """禁用日志输出"""
        pass
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == "/" or self.path == "/index.html":
            file_path = os.path.join(self.web_dir, "index.html")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
                return
        
        if self.path == "/monitor" or self.path == "/monitor/":
            file_path = os.path.join(self.monitor_dir, "index.html")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
                return
        
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not Found")


class APIServer:
    """API服务器，提供设置功能和AI模型输出展示"""
    
    def __init__(self, host=None, port=None):
        self.host = host or settings.host
        self.port = port or settings.api_port
        self.http_server = None
        self.ws_server = None
        self.http_thread = None
        self.ws_thread = None
        self.is_running = False
        self.clients = set()
        
        # 初始化AI服务
        self.ai_service = AIService()
        
        # 创建网页目录
        self.web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_api")
        self._create_web_files()
    
    def _create_web_files(self):
        """创建API网页文件"""
        os.makedirs(self.web_dir, exist_ok=True)
        
        # 创建index.html
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI设置与控制台</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d9ff, #0066ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            color: #888;
            margin-top: 10px;
        }
        
        .status {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            margin-top: 10px;
        }
        
        .status.connected {
            background: #00c853;
            color: #fff;
        }
        
        .status.disconnected {
            background: #ff5252;
            color: #fff;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            overflow-x: auto;
        }
        
        .tab {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .tab:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .tab.active {
            background: #00d9ff;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .card h3 {
            margin-bottom: 15px;
            color: #00d9ff;
            font-size: 1.2rem;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        
        .toggle-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            font-weight: 500;
        }
        
        .toggle {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 34px;
        }
        
        .toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: 0.3s;
            border-radius: 34px;
        }
        
        .slider:before {
            position: absolute;
            content: "";
            height: 26px;
            width: 26px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
        }
        
        input:checked + .slider {
            background: linear-gradient(135deg, #00d9ff, #0066ff);
        }
        
        input:checked + .slider:before {
            transform: translateX(26px);
        }
        
        .status-text {
            font-size: 12px;
            margin-top: 10px;
            padding: 8px 12px;
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00d9ff, #0066ff);
            color: #fff;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 217, 255, 0.4);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff5252, #c62828);
            color: #fff;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #00c853, #008944);
            color: #fff;
        }
        
        .input-group {
            margin: 15px 0;
        }
        
        .input-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            color: #aaa;
        }
        
        .input-group input, .input-group select, .input-group textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 14px;
        }
        
        .input-group input:focus, .input-group select:focus, .input-group textarea:focus {
            outline: none;
            border-color: #00d9ff;
        }
        
        .input-group textarea {
            resize: vertical;
            min-height: 100px;
        }
        
        .checkbox-group {
            margin: 10px 0;
        }
        
        .checkbox-group label {
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
            color: #ccc;
        }
        
        .checkbox-group input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        
        .chat-area {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 500px;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        
        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-messages::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .chat-messages::-webkit-scrollbar-thumb {
            background: #00d9ff;
            border-radius: 3px;
        }
        
        .message {
            margin-bottom: 15px;
            max-width: 80%;
        }
        
        .message.user {
            margin-left: auto;
        }
        
        .message.ai {
            margin-right: auto;
        }
        
        .message-content {
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .message.user .message-content {
            background: #00d9ff;
            border-radius: 18px 18px 4px 18px;
        }
        
        .message.ai .message-content {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 18px 18px 18px 4px;
        }
        
        .message-time {
            font-size: 11px;
            color: #888;
            margin-top: 4px;
            text-align: right;
        }
        
        .chat-input {
            padding: 15px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            gap: 10px;
        }
        
        .chat-input input {
            flex: 1;
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 14px;
        }
        
        .chat-input input:focus {
            outline: none;
            border-color: #00d9ff;
        }
        
        .chat-input button {
            padding: 12px 24px;
            border: none;
            border-radius: 25px;
            background: #00d9ff;
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .chat-input button:hover {
            background: #0099cc;
        }
        
        .settings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .setting-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 15px;
        }
        
        .setting-item .label {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
        }
        
        .setting-item .value {
            font-size: 1rem;
            font-weight: bold;
            color: #00d9ff;
            word-break: break-all;
        }
        
        .log-area {
            background: #0d0d0d;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            color: #00ff00;
            overflow-y: auto;
            max-height: 400px;
            white-space: pre-wrap;
        }
        
        .slider-container {
            margin: 15px 0;
        }
        
        .slider-container label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            color: #aaa;
        }
        
        .slider {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.2);
            outline: none;
            -webkit-appearance: none;
        }
        
        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #00d9ff;
            cursor: pointer;
        }
        
        .slider-value {
            display: inline-block;
            margin-left: 10px;
            color: #00d9ff;
            font-weight: bold;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 1.8rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI设置与控制台</h1>
            <p>端口: 15002</p>
            <span id="connectionStatus" class="status disconnected">未连接</span>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('chat')">💬 AI对话</button>
            <button class="tab" onclick="showTab('settings')">⚙️ 设置管理</button>
            <button class="tab" onclick="showTab('logs')">📜 日志输出</button>
            <button class="tab" onclick="showTab('info')">ℹ️ 系统信息</button>
        </div>
        
        <!-- AI对话 -->
        <div id="chat" class="tab-content active">
            <div class="chat-area">
                <div id="chatMessages" class="chat-messages"></div>
                <div class="chat-input">
                    <input type="text" id="chatInput" placeholder="输入消息..." onkeydown="if(event.keyCode===13) sendChat()">
                    <button onclick="sendChat()">发送</button>
                </div>
            </div>
        </div>
        
        <!-- 设置管理 -->
        <div id="settings" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h3>AI模型设置</h3>
                    <div class="input-group">
                        <label>模型名称:</label>
                        <input type="text" id="modelName" placeholder="输入模型名称">
                    </div>
                    <div class="slider-container">
                        <label>温度: <span id="temperatureValue">0.7</span></label>
                        <input type="range" class="slider" id="temperature" min="0" max="2" step="0.1" value="0.7" oninput="updateTemperature(this.value)">
                    </div>
                    <div class="slider-container">
                        <label>最大Token: <span id="maxTokensValue">512</span></label>
                        <input type="range" class="slider" id="maxTokens" min="64" max="4096" step="64" value="512" oninput="updateMaxTokens(this.value)">
                    </div>
                    <button class="btn btn-primary" onclick="saveModelSettings()">保存模型设置</button>
                </div>
                
                <div class="card">
                    <h3>应用设置</h3>
                    <div class="input-group">
                        <label>应用名称:</label>
                        <input type="text" id="appName" placeholder="输入应用名称">
                    </div>
                    <div class="checkbox-group">
                        <label>
                            <input type="checkbox" id="enableThinking">
                            启用思考模式
                        </label>
                    </div>
                    <div class="checkbox-group">
                        <label>
                            <input type="checkbox" id="clearThinking">
                            清除思考内容
                        </label>
                    </div>
                    <button class="btn btn-primary" onclick="saveAppSettings()">保存应用设置</button>
                </div>
                
                <div class="card">
                    <h3>权限设置</h3>
                    <div class="input-group">
                        <label>权限等级:</label>
                        <select id="permissionLevel">
                            <option value="full">完整权限</option>
                            <option value="normal">普通权限</option>
                            <option value="limited">受限权限</option>
                        </select>
                    </div>
                    <div class="input-group">
                        <label>每分钟最大调用次数:</label>
                        <input type="number" id="maxCalls" value="40" min="1" max="100">
                    </div>
                    <button class="btn btn-primary" onclick="savePermissionSettings()">保存权限设置</button>
                </div>
                
                <div class="card">
                    <h3>服务器设置</h3>
                    <div class="input-group">
                        <label>主机地址:</label>
                        <input type="text" id="host" placeholder="输入主机地址">
                    </div>
                    <div class="input-group">
                        <label>WebSocket端口:</label>
                        <input type="number" id="wsPort" value="15000">
                    </div>
                    <div class="input-group">
                        <label>RCON端口:</label>
                        <input type="number" id="rconPort" value="15001">
                    </div>
                    <div class="input-group">
                        <label>API端口:</label>
                        <input type="number" id="apiPort" value="15002">
                    </div>
                    <div class="input-group">
                        <label class="toggle-label">
                            <span>启用桌面监控:</span>
                            <label class="toggle">
                                <input type="checkbox" id="monitorEnabled" onchange="toggleMonitor()">
                                <span class="slider"></span>
                            </label>
                        </label>
                    </div>
                    <div id="monitorStatus" class="status-text" style="color: #6b7280;">监控状态: 未知</div>
                    <button class="btn btn-primary" onclick="saveServerSettings()">保存服务器设置</button>
                </div>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <h3>配置操作</h3>
                <button class="btn btn-primary" onclick="loadSettings()">🔄 加载当前配置</button>
                <button class="btn btn-success" onclick="exportSettings()">📥 导出配置</button>
                <button class="btn btn-danger" onclick="resetSettings()">🔁 恢复默认</button>
            </div>
        </div>
        
        <!-- 日志输出 -->
        <div id="logs" class="tab-content">
            <div class="card">
                <h3>AI输出日志</h3>
                <div id="aiLog" class="log-area">等待AI输出...</div>
                <button class="btn btn-primary" onclick="clearLog()">清空日志</button>
            </div>
        </div>
        
        <!-- 系统信息 -->
        <div id="info" class="tab-content">
            <div class="card">
                <h3>当前配置</h3>
                <div class="settings-grid" id="currentSettings"></div>
            </div>
            <div class="card" style="margin-top: 20px;">
                <h3>连接信息</h3>
                <div class="settings-grid">
                    <div class="setting-item">
                        <div class="label">WebSocket端口</div>
                        <div class="value">15000</div>
                    </div>
                    <div class="setting-item">
                        <div class="label">RCON端口</div>
                        <div class="value">15001</div>
                    </div>
                    <div class="setting-item">
                        <div class="label">API端口</div>
                        <div class="value">15002</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws;
        let reconnectInterval;
        
        function connect() {
            const wsUrl = `ws://${window.location.hostname}:15003/api`;
            console.log('连接到:', wsUrl);
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                document.getElementById('connectionStatus').className = 'status connected';
                document.getElementById('connectionStatus').textContent = '已连接';
                clearInterval(reconnectInterval);
                loadSettings();
                console.log('API服务器连接成功');
            };
            
            ws.onclose = function() {
                document.getElementById('connectionStatus').className = 'status disconnected';
                document.getElementById('connectionStatus').textContent = '已断开';
                reconnectInterval = setInterval(connect, 3000);
                console.log('API服务器连接断开，正在重连...');
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket错误:', error);
            };
            
            ws.onmessage = function(event) {
                handleMessage(event.data);
            };
        }
        
        function handleMessage(data) {
            const message = JSON.parse(data);
            
            switch(message.type) {
                case 'chat_response':
                    addMessage('ai', message.content);
                    addToLog('AI响应: ' + message.content);
                    break;
                case 'settings_loaded':
                    populateSettings(message.data);
                    break;
                case 'settings_saved':
                    alert('设置已保存');
                    break;
                case 'log_message':
                    addToLog(message.content);
                    break;
                case 'error':
                    alert('错误: ' + message.message);
                    break;
                case 'success':
                    console.log('操作成功');
                    break;
                case 'monitor_status':
                    updateMonitorStatus(message.data);
                    break;
                case 'monitor_toggle':
                    updateMonitorToggle(message.enabled);
                    break;
            }
        }
        
        function sendMessage(type, data) {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type, data }));
            }
        }
        
        function showTab(tabId) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelector(`button[onclick="showTab('${tabId}')"]`).classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }
        
        function sendChat() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if(message) {
                addMessage('user', message);
                addToLog('用户输入: ' + message);
                sendMessage('chat', { message });
                input.value = '';
            }
        }
        
        function addMessage(sender, content) {
            const container = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = new Date().toLocaleTimeString();
            
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(timeDiv);
            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }
        
        function addToLog(message) {
            const logArea = document.getElementById('aiLog');
            const timestamp = new Date().toLocaleTimeString();
            logArea.textContent += `[${timestamp}] ${message}\n`;
            logArea.scrollTop = logArea.scrollHeight;
        }
        
        function clearLog() {
            document.getElementById('aiLog').textContent = '';
        }
        
        function loadSettings() {
            sendMessage('get_settings', {});
            sendMessage('get_monitor_status', {});
        }
        
        function populateSettings(settings) {
            document.getElementById('modelName').value = settings.model_name || '';
            document.getElementById('temperature').value = settings.temperature || 0.7;
            document.getElementById('temperatureValue').textContent = settings.temperature || 0.7;
            document.getElementById('maxTokens').value = settings.max_tokens || 512;
            document.getElementById('maxTokensValue').textContent = settings.max_tokens || 512;
            document.getElementById('appName').value = settings.app_name || '';
            document.getElementById('enableThinking').checked = settings.enable_thinking || false;
            document.getElementById('clearThinking').checked = settings.clear_thinking || false;
            document.getElementById('permissionLevel').value = settings.permission_level || 'normal';
            document.getElementById('maxCalls').value = settings.max_calls_per_minute || 40;
            document.getElementById('host').value = settings.host || '';
            document.getElementById('wsPort').value = settings.websocket_port || 15000;
            document.getElementById('rconPort').value = settings.rcon_port || 15001;
            document.getElementById('apiPort').value = settings.api_port || 15002;
            
            const infoHTML = `
                <div class="setting-item"><div class="label">模型名称</div><div class="value">${settings.model_name || '未设置'}</div></div>
                <div class="setting-item"><div class="label">温度</div><div class="value">${settings.temperature || 0.7}</div></div>
                <div class="setting-item"><div class="label">最大Token</div><div class="value">${settings.max_tokens || 512}</div></div>
                <div class="setting-item"><div class="label">应用名称</div><div class="value">${settings.app_name || '未设置'}</div></div>
                <div class="setting-item"><div class="label">权限等级</div><div class="value">${settings.permission_level || 'normal'}</div></div>
                <div class="setting-item"><div class="label">主机地址</div><div class="value">${settings.host || '0.0.0.0'}</div></div>
            `;
            document.getElementById('currentSettings').innerHTML = infoHTML;
        }
        
        function saveModelSettings() {
            const data = {
                model_name: document.getElementById('modelName').value,
                temperature: parseFloat(document.getElementById('temperature').value),
                max_tokens: parseInt(document.getElementById('maxTokens').value)
            };
            sendMessage('save_model_settings', data);
            addToLog('保存模型设置: ' + JSON.stringify(data));
        }
        
        function saveAppSettings() {
            const data = {
                app_name: document.getElementById('appName').value,
                enable_thinking: document.getElementById('enableThinking').checked,
                clear_thinking: document.getElementById('clearThinking').checked
            };
            sendMessage('save_app_settings', data);
            addToLog('保存应用设置: ' + JSON.stringify(data));
        }
        
        function savePermissionSettings() {
            const data = {
                permission_level: document.getElementById('permissionLevel').value,
                max_calls_per_minute: parseInt(document.getElementById('maxCalls').value)
            };
            sendMessage('save_permission_settings', data);
            addToLog('保存权限设置: ' + JSON.stringify(data));
        }
        
        function saveServerSettings() {
            const data = {
                host: document.getElementById('host').value,
                websocket_port: parseInt(document.getElementById('wsPort').value),
                rcon_port: parseInt(document.getElementById('rconPort').value),
                api_port: parseInt(document.getElementById('apiPort').value)
            };
            sendMessage('save_server_settings', data);
            addToLog('保存服务器设置: ' + JSON.stringify(data));
        }
        
        function toggleMonitor() {
            sendMessage('toggle_monitor', {});
            addToLog('切换监控状态');
        }
        
        function getMonitorStatus() {
            sendMessage('get_monitor_status', {});
        }
        
        function exportSettings() {
            sendMessage('export_settings', {});
        }
        
        function resetSettings() {
            if(confirm('确定要恢复默认设置吗？')) {
                sendMessage('reset_settings', {});
                loadSettings();
                addToLog('已恢复默认设置');
            }
        }
        
        function updateTemperature(value) {
            document.getElementById('temperatureValue').textContent = value;
        }
        
        function updateMaxTokens(value) {
            document.getElementById('maxTokensValue').textContent = value;
        }
        
        function updateMonitorStatus(data) {
            document.getElementById('monitorEnabled').checked = data.enabled;
            const statusText = document.getElementById('monitorStatus');
            if(data.enabled) {
                statusText.textContent = '监控状态: 运行中 | FPS: ' + data.fps + ' | 质量: ' + data.quality + '%';
                statusText.style.color = '#10b981';
            } else {
                statusText.textContent = '监控状态: 已停止';
                statusText.style.color = '#ef4444';
            }
        }
        
        function updateMonitorToggle(enabled) {
            document.getElementById('monitorEnabled').checked = enabled;
            const statusText = document.getElementById('monitorStatus');
            if(enabled) {
                statusText.textContent = '监控状态: 已启动';
                statusText.style.color = '#10b981';
            } else {
                statusText.textContent = '监控状态: 已停止';
                statusText.style.color = '#ef4444';
            }
        }
        
        window.addEventListener('load', connect);
    </script>
</body>
</html>
"""
        
        with open(os.path.join(self.web_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"API网页文件已创建: {os.path.join(self.web_dir, 'index.html')}")
    
    def _http_thread_func(self):
        """HTTP服务器线程函数"""
        monitor_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_monitor")
        handler = lambda *args, **kwargs: HTTPServerHandler(self.web_dir, monitor_dir, *args, **kwargs)
        self.http_server = HTTPServer((self.host, self.port), handler)
        print(f"HTTP服务器已启动: http://{self.host}:{self.port}")
        self.http_server.serve_forever()
    
    async def _handle_client(self, websocket):
        """处理单个WebSocket客户端连接"""
        self.clients.add(websocket)
        print(f"API客户端已连接: {websocket.remote_address}")
        
        try:
            await websocket.send(json.dumps({
                'type': 'welcome',
                'message': '欢迎连接AI设置与控制台API'
            }))
            
            async for message in websocket:
                await self._process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"API客户端已断开: {websocket.remote_address}")
    
    async def _process_message(self, websocket, message):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            message_data = data.get('data', {})
            
            response = await self._handle_command(message_type, message_data)
            
            if response:
                await websocket.send(json.dumps(response))
                
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': '无效的JSON格式'
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def _handle_command(self, command_type, data):
        """处理各种命令"""
        commands = {
            'chat': self._handle_chat,
            'get_settings': self._handle_get_settings,
            'save_model_settings': self._handle_save_model_settings,
            'save_app_settings': self._handle_save_app_settings,
            'save_permission_settings': self._handle_save_permission_settings,
            'save_server_settings': self._handle_save_server_settings,
            'export_settings': self._handle_export_settings,
            'reset_settings': self._handle_reset_settings,
            'get_extensions': self._handle_get_extensions,
            'get_extension_status': self._handle_get_extension_status,
            'add_mcp_server': self._handle_add_mcp_server,
            'remove_mcp_server': self._handle_remove_mcp_server,
            'enable_extension': self._handle_enable_extension,
            'disable_extension': self._handle_disable_extension,
            'reload_extension': self._handle_reload_extension,
            'get_monitor_status': self._handle_get_monitor_status,
            'toggle_monitor': self._handle_toggle_monitor,
            'set_monitor_fps': self._handle_set_monitor_fps,
        }
        
        handler = commands.get(command_type)
        if handler:
            return await handler(data)
        
        return {'type': 'error', 'message': f'未知命令: {command_type}'}
    
    async def _handle_chat(self, data):
        """处理AI对话"""
        message = data.get('message', '')
        if not message:
            return {'type': 'error', 'message': '消息不能为空'}
        
        try:
            response = await asyncio.to_thread(
                self.ai_service.generate_response,
                message
            )
            return {'type': 'chat_response', 'content': response}
        except Exception as e:
            return {'type': 'error', 'message': str(e)}
    
    async def _handle_get_settings(self, data):
        """获取当前设置"""
        settings_data = {
            'model_name': settings.model_name,
            'temperature': settings.temperature,
            'max_tokens': settings.max_tokens,
            'app_name': settings.app_name,
            'app_version': settings.app_version,
            'enable_thinking': settings.enable_thinking,
            'clear_thinking': settings.clear_thinking,
            'permission_level': getattr(settings, 'permission_level', 'normal'),
            'max_calls_per_minute': settings.max_calls_per_minute,
            'host': settings.host,
            'port': settings.port,
            'websocket_port': settings.websocket_port,
            'rcon_port': settings.rcon_port,
            'api_port': settings.api_port,
        }
        return {'type': 'settings_loaded', 'data': settings_data}
    
    async def _handle_save_model_settings(self, data):
        """保存模型设置"""
        if 'model_name' in data:
            settings.model_name = data['model_name']
        if 'temperature' in data:
            settings.temperature = data['temperature']
        if 'max_tokens' in data:
            settings.max_tokens = data['max_tokens']
        await self._save_settings_to_file()
        return {'type': 'success', 'message': '模型设置已保存'}
    
    async def _handle_save_app_settings(self, data):
        """保存应用设置"""
        if 'app_name' in data:
            settings.app_name = data['app_name']
        if 'enable_thinking' in data:
            settings.enable_thinking = data['enable_thinking']
        if 'clear_thinking' in data:
            settings.clear_thinking = data['clear_thinking']
        await self._save_settings_to_file()
        return {'type': 'success', 'message': '应用设置已保存'}
    
    async def _handle_save_permission_settings(self, data):
        """保存权限设置"""
        if 'permission_level' in data:
            self._update_env_file('PERMISSION_LEVEL', data['permission_level'])
        if 'max_calls_per_minute' in data:
            settings.max_calls_per_minute = data['max_calls_per_minute']
        await self._save_settings_to_file()
        return {'type': 'success', 'message': '权限设置已保存'}
    
    async def _handle_save_server_settings(self, data):
        """保存服务器设置"""
        if 'host' in data:
            settings.host = data['host']
            self._update_env_file('HOST', data['host'])
        if 'websocket_port' in data:
            settings.websocket_port = data['websocket_port']
            self._update_env_file('WEBSOCKET_PORT', str(data['websocket_port']))
        if 'rcon_port' in data:
            settings.rcon_port = data['rcon_port']
            self._update_env_file('RCON_PORT', str(data['rcon_port']))
        if 'api_port' in data:
            settings.api_port = data['api_port']
            self._update_env_file('API_PORT', str(data['api_port']))
        await self._save_settings_to_file()
        return {'type': 'success', 'message': '服务器设置已保存'}
    
    async def _handle_export_settings(self, data):
        """导出设置"""
        settings_data = {
            'model_name': settings.model_name,
            'temperature': settings.temperature,
            'max_tokens': settings.max_tokens,
            'app_name': settings.app_name,
            'app_version': settings.app_version,
            'enable_thinking': settings.enable_thinking,
            'clear_thinking': settings.clear_thinking,
            'max_calls_per_minute': settings.max_calls_per_minute,
            'host': settings.host,
            'port': settings.port,
            'websocket_port': settings.websocket_port,
            'rcon_port': settings.rcon_port,
            'api_port': settings.api_port,
        }
        
        export_path = os.path.join(self.web_dir, 'settings_backup.json')
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=2, ensure_ascii=False)
        
        return {'type': 'success', 'message': f'设置已导出到 {export_path}'}
    
    async def _handle_reset_settings(self, data):
        """重置设置为默认值"""
        settings.model_name = "z-ai/glm4.7"
        settings.temperature = 1.0
        settings.max_tokens = 16384
        settings.app_name = "AI Computer Control"
        settings.enable_thinking = True
        settings.clear_thinking = False
        settings.max_calls_per_minute = 40
        settings.host = "0.0.0.0"
        settings.port = 8000
        settings.websocket_port = 15000
        settings.rcon_port = 15001
        settings.api_port = 15002
        
        await self._save_settings_to_file()
        return {'type': 'success', 'message': '已恢复默认设置'}
    
    async def _save_settings_to_file(self):
        """保存设置到文件"""
        pass
    
    def _update_env_file(self, key, value):
        """更新.env文件"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            new_lines = []
            found = False
            
            for line in lines:
                if line.startswith(f'{key}:') or line.startswith(f'{key}='):
                    if ':' in line:
                        new_lines.append(f'{key}: str = "{value}"')
                    else:
                        new_lines.append(f'{key}={value}')
                    found = True
                else:
                    new_lines.append(line)
            
            if not found:
                new_lines.append(f'{key}: str = "{value}"')
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
    
    async def _ws_process_request(self, path, request_headers):
        """处理WebSocket升级请求前的HTTP请求"""
        # 允许所有请求
        return None
        
    async def _ws_run_server(self):
        """运行WebSocket服务器"""
        self.ws_server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port + 1,  # WebSocket使用端口+1
            process_request=self._ws_process_request
        )
        print(f"API WebSocket服务器已启动: ws://{self.host}:{self.port + 1}/api")
        
        await self.ws_server.wait_closed()
    
    def _ws_thread_func(self):
        """WebSocket服务器线程函数"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ws_run_server())
    
    def start(self):
        """启动服务器"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动HTTP服务器
        self.http_thread = threading.Thread(
            target=self._http_thread_func,
            daemon=True
        )
        self.http_thread.start()
        
        # 启动WebSocket服务器
        self.ws_thread = threading.Thread(
            target=self._ws_thread_func,
            daemon=True
        )
        self.ws_thread.start()
    
    def stop(self):
        """停止服务器"""
        self.is_running = False
        
        # 停止HTTP服务器
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            print("HTTP服务器已停止")
        
        # 停止WebSocket服务器
        if self.ws_server:
            self.ws_server.close()
            print("WebSocket服务器已停止")
    
    async def _handle_get_extensions(self, data):
        """获取所有扩展"""
        extensions = extension_manager.get_all_extensions()
        return {
            'type': 'extensions_list',
            'data': [
                {
                    'type': ext.type,
                    'name': ext.name,
                    'version': ext.version,
                    'description': ext.description,
                    'state': ext.state,
                    'enabled': ext.enabled
                } for ext in extensions
            ]
        }
    
    async def _handle_get_extension_status(self, data):
        """获取扩展系统状态"""
        status = extension_manager.get_status()
        return {'type': 'extension_status', 'data': status}
    
    async def _handle_add_mcp_server(self, data):
        """添加MCP服务器"""
        name = data.get('name')
        command = data.get('command')
        args = data.get('args', [])
        env = data.get('env', {})
        enabled = data.get('enabled', True)
        
        if not name or not command:
            return {'type': 'error', 'message': 'name和command是必需的'}
        
        if extension_manager.add_mcp_server(name, command, args, env, enabled):
            return {'type': 'success', 'message': f'MCP服务器 {name} 添加成功'}
        return {'type': 'error', 'message': f'MCP服务器 {name} 添加失败'}
    
    async def _handle_remove_mcp_server(self, data):
        """移除MCP服务器"""
        name = data.get('name')
        if not name:
            return {'type': 'error', 'message': 'name是必需的'}
        
        if extension_manager.remove_mcp_server(name):
            return {'type': 'success', 'message': f'MCP服务器 {name} 移除成功'}
        return {'type': 'error', 'message': f'MCP服务器 {name} 移除失败'}
    
    async def _handle_enable_extension(self, data):
        """启用扩展"""
        name = data.get('name')
        if not name:
            return {'type': 'error', 'message': 'name是必需的'}
        
        if extension_manager.enable_extension(name):
            return {'type': 'success', 'message': f'扩展 {name} 启用成功'}
        return {'type': 'error', 'message': f'扩展 {name} 启用失败'}
    
    async def _handle_disable_extension(self, data):
        """禁用扩展"""
        name = data.get('name')
        if not name:
            return {'type': 'error', 'message': 'name是必需的'}
        
        if extension_manager.disable_extension(name):
            return {'type': 'success', 'message': f'扩展 {name} 禁用成功'}
        return {'type': 'error', 'message': f'扩展 {name} 禁用失败'}
    
    async def _handle_reload_extension(self, data):
        """热重载扩展"""
        name = data.get('name')
        if not name:
            return {'type': 'error', 'message': 'name是必需的'}
        
        if extension_manager.reload_extension(name):
            return {'type': 'success', 'message': f'扩展 {name} 热重载成功'}
        return {'type': 'error', 'message': f'扩展 {name} 热重载失败'}
    
    async def _handle_get_monitor_status(self, data):
        """获取监控状态"""
        status = screen_monitor.get_status()
        return {'type': 'monitor_status', 'data': status}
    
    async def _handle_toggle_monitor(self, data):
        """切换监控状态"""
        enabled = screen_monitor.toggle()
        return {'type': 'monitor_toggle', 'enabled': enabled}
    
    async def _handle_set_monitor_fps(self, data):
        """设置监控帧率"""
        fps = data.get('fps', 10)
        screen_monitor.set_fps(fps)
        return {'type': 'success', 'message': f'帧率已设置为 {fps} FPS'}

if __name__ == "__main__":
    server = APIServer()
    server.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()