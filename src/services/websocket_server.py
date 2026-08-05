import asyncio
import websockets
import json
import threading
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.system.controller import SystemController
from src.system.vision import VisionCapture
from src.config.settings import settings

from src.utils.logger import get_logger

logger = get_logger(__name__)

class RCONBroadcastServer:
    """RCON控制台信息广播服务器"""
    
    def __init__(self, host=None, port=None):
        self.host = host or settings.host
        self.port = port or settings.rcon_port
        self.server = None
        self.is_running = False
        self.clients = set()
        self.message_queue = asyncio.Queue()
    
    async def _broadcast_handler(self, websocket, path):
        """处理rcon客户端连接"""
        self.clients.add(websocket)
        logger.info(f"RCON客户端已连接: {websocket.remote_address}")
        
        try:
            # 发送欢迎消息
            await websocket.send(json.dumps({
                'type': 'welcome',
                'message': '欢迎连接RCON控制台广播服务器'
            }))
            
            # 持续监听消息队列并广播
            while self.is_running:
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                    await websocket.send(json.dumps(message))
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
        finally:
            self.clients.remove(websocket)
            logger.info(f"RCON客户端已断开: {websocket.remote_address}")
    
    def broadcast(self, message_type, content):
        """向所有客户端广播消息"""
        message = {
            'type': message_type,
            'content': content,
            'timestamp': time.time()
        }
        asyncio.run_coroutine_threadsafe(self.message_queue.put(message), self.loop)
    
    async def _start_server(self):
        """启动RCON广播服务器"""
        self.server = await websockets.serve(
            self._broadcast_handler,
            self.host,
            self.port
        )
        logger.info(f"RCON广播服务器已启动: ws://{self.host}:{self.port}/rcon")
        
        await self.server.wait_closed()
    
    def _run_server(self):
        """在子线程中运行服务器"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start_server())
    
    def start(self):
        """启动RCON广播服务器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(
            target=self._run_server,
            daemon=True
        )
        self.thread.start()
    
    def stop(self):
        """停止RCON广播服务器"""
        self.is_running = False
        if self.server:
            self.server.close()
        logger.info("RCON广播服务器已停止")


class WebSocketServer:
    """WebSocket服务器，提供网站控制端功能"""
    
    def __init__(self, host=None, port=None):
        # 使用settings中的配置，如果没有传入参数
        self.host = host or settings.host
        self.port = port or settings.websocket_port
        self.server = None
        self.http_server = None
        self.is_running = False
        self.clients = set()
        
        # 初始化系统控制器和视觉捕获
        self.system_controller = SystemController()
        self.vision_capture = VisionCapture()
        
        # 创建RCON广播服务器
        self.rcon_server = RCONBroadcastServer()
        
        # 创建网页目录
        self.web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
        self._create_web_files()
    
    def _create_web_files(self):
        """创建网页文件"""
        os.makedirs(self.web_dir, exist_ok=True)
        
        # 创建index.html
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI电脑控制 - Web控制端</title>
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
            max-width: 1200px;
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
            background: linear-gradient(90deg, #4a90d9, #2d5a8a);
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
            background: #4a90d9;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
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
            color: #4a90d9;
        }
        
        .btn {
            display: block;
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #4a90d9, #2d5a8a);
            color: #fff;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(74, 144, 217, 0.4);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff5252, #c62828);
            color: #fff;
        }
        
        .btn-danger:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 82, 82, 0.4);
        }
        
        .btn-warning {
            background: linear-gradient(135deg, #ff9800, #e65100);
            color: #fff;
        }
        
        .btn-info {
            background: linear-gradient(135deg, #00bcd4, #00838f);
            color: #fff;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #00c853, #008944);
            color: #fff;
        }
        
        .slider-container {
            margin: 15px 0;
        }
        
        .slider-container label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
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
            background: #4a90d9;
            cursor: pointer;
        }
        
        .slider-value {
            display: inline-block;
            margin-left: 10px;
            color: #4a90d9;
            font-weight: bold;
        }
        
        .input-group {
            margin: 15px 0;
        }
        
        .input-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        .input-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 14px;
        }
        
        .input-group input:focus {
            outline: none;
            border-color: #4a90d9;
        }
        
        .checkbox-group {
            margin: 10px 0;
        }
        
        .checkbox-group label {
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
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
            background: #4a90d9;
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
            background: #4a90d9;
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
            border-color: #4a90d9;
        }
        
        .chat-input button {
            padding: 12px 24px;
            border: none;
            border-radius: 25px;
            background: #4a90d9;
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .chat-input button:hover {
            background: #3a7bc8;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }
        
        .status-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        
        .status-item .label {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
        }
        
        .status-item .value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #4a90d9;
        }
        
        .screenshot-preview {
            max-width: 100%;
            border-radius: 8px;
            margin-top: 10px;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8rem;
            }
            
            .tab {
                padding: 10px 16px;
                font-size: 12px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI电脑控制</h1>
            <p>WebSocket远程控制端</p>
            <span id="connectionStatus" class="status disconnected">未连接</span>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('chat')">💬 AI对话</button>
            <button class="tab" onclick="showTab('mouse')">🖱️ 鼠标控制</button>
            <button class="tab" onclick="showTab('keyboard')">⌨️ 键盘控制</button>
            <button class="tab" onclick="showTab('system')">⚙️ 系统控制</button>
            <button class="tab" onclick="showTab('vision')">📷 视觉捕获</button>
            <button class="tab" onclick="showTab('status')">📊 电脑状态</button>
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
        
        <!-- 鼠标控制 -->
        <div id="mouse" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h3>鼠标移动</h3>
                    <div class="input-group">
                        <label>X坐标: <span id="mouseX">0</span></label>
                        <input type="range" class="slider" min="0" max="1920" value="960" oninput="updateMouseX(this.value)">
                    </div>
                    <div class="input-group">
                        <label>Y坐标: <span id="mouseY">0</span></label>
                        <input type="range" class="slider" min="0" max="1080" value="540" oninput="updateMouseY(this.value)">
                    </div>
                    <button class="btn btn-primary" onclick="moveMouse()">移动鼠标</button>
                    <button class="btn btn-info" onclick="moveMouseRelative()">相对移动</button>
                </div>
                
                <div class="card">
                    <h3>鼠标点击</h3>
                    <button class="btn btn-primary" onclick="clickMouse('left')">左键单击</button>
                    <button class="btn btn-primary" onclick="clickMouse('right')">右键单击</button>
                    <button class="btn btn-warning" onclick="clickMouse('double')">双击</button>
                    <button class="btn btn-info" onclick="scrollMouse('up')">向上滚动</button>
                    <button class="btn btn-info" onclick="scrollMouse('down')">向下滚动</button>
                </div>
                
                <div class="card">
                    <h3>拖拽控制</h3>
                    <button class="btn btn-danger" onclick="dragMouse('start')">开始拖拽</button>
                    <button class="btn btn-success" onclick="dragMouse('stop')">停止拖拽</button>
                </div>
            </div>
        </div>
        
        <!-- 键盘控制 -->
        <div id="keyboard" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h3>输入文本</h3>
                    <div class="input-group">
                        <label>输入内容:</label>
                        <input type="text" id="keyboardInput" placeholder="输入要输入的文本">
                    </div>
                    <button class="btn btn-primary" onclick="typeText()">输入文本</button>
                </div>
                
                <div class="card">
                    <h3>快捷键</h3>
                    <button class="btn btn-info" onclick="pressHotkey('ctrl+c')">Ctrl+C</button>
                    <button class="btn btn-info" onclick="pressHotkey('ctrl+v')">Ctrl+V</button>
                    <button class="btn btn-info" onclick="pressHotkey('ctrl+x')">Ctrl+X</button>
                    <button class="btn btn-danger" onclick="pressHotkey('alt+f4')">Alt+F4</button>
                    <button class="btn btn-warning" onclick="pressHotkey('win+d')">Win+D</button>
                    <button class="btn btn-success" onclick="pressHotkey('ctrl+s')">Ctrl+S</button>
                </div>
                
                <div class="card">
                    <h3>特殊按键</h3>
                    <button class="btn btn-primary" onclick="pressKey('enter')">Enter</button>
                    <button class="btn btn-primary" onclick="pressKey('tab')">Tab</button>
                    <button class="btn btn-primary" onclick="pressKey('backspace')">Backspace</button>
                    <button class="btn btn-primary" onclick="pressKey('delete')">Delete</button>
                    <button class="btn btn-primary" onclick="pressKey('esc')">Esc</button>
                    <button class="btn btn-primary" onclick="pressKey('space')">Space</button>
                </div>
            </div>
        </div>
        
        <!-- 系统控制 -->
        <div id="system" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h3>窗口控制</h3>
                    <button class="btn btn-info" onclick="minimizeWindow()">最小化窗口</button>
                    <button class="btn btn-info" onclick="maximizeWindow()">最大化窗口</button>
                    <button class="btn btn-info" onclick="restoreWindow()">还原窗口</button>
                    <button class="btn btn-danger" onclick="closeWindow()">关闭窗口</button>
                </div>
                
                <div class="card">
                    <h3>系统操作</h3>
                    <button class="btn btn-warning" onclick="lockScreen()">锁定屏幕</button>
                    <button class="btn btn-danger" onclick="shutdownPC()">关机</button>
                    <button class="btn btn-danger" onclick="restartPC()">重启</button>
                    <button class="btn btn-info" onclick="sleepPC()">睡眠</button>
                </div>
                
                <div class="card">
                    <h3>音量控制</h3>
                    <div class="slider-container">
                        <label>音量: <span id="volumeValue">50</span>%</label>
                        <input type="range" class="slider" id="volumeSlider" min="0" max="100" value="50" oninput="updateVolume(this.value)">
                    </div>
                    <button class="btn btn-primary" onclick="setVolume()">设置音量</button>
                    <button class="btn btn-info" onclick="muteVolume()">静音/取消静音</button>
                </div>
            </div>
        </div>
        
        <!-- 视觉捕获 -->
        <div id="vision" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h3>截图功能</h3>
                    <button class="btn btn-primary" onclick="takeScreenshot()">📸 截取全屏</button>
                    <button class="btn btn-info" onclick="takeScreenshot('region')">🖼️ 截取区域</button>
                    <button class="btn btn-success" onclick="saveScreenshot()">💾 保存截图</button>
                </div>
                
                <div class="card">
                    <h3>摄像头</h3>
                    <button class="btn btn-primary" onclick="toggleCamera()">📹 开启/关闭摄像头</button>
                    <button class="btn btn-info" onclick="capturePhoto()">📷 拍照</button>
                </div>
                
                <div class="card">
                    <h3>截图预览</h3>
                    <div id="screenshotPreview"></div>
                </div>
            </div>
        </div>
        
        <!-- 电脑状态 -->
        <div id="status" class="tab-content">
            <div class="card">
                <h3>系统状态</h3>
                <div class="status-grid">
                    <div class="status-item">
                        <div class="label">CPU使用率</div>
                        <div class="value" id="cpuUsage">--</div>
                    </div>
                    <div class="status-item">
                        <div class="label">内存使用率</div>
                        <div class="value" id="memoryUsage">--</div>
                    </div>
                    <div class="status-item">
                        <div class="label">磁盘使用率</div>
                        <div class="value" id="diskUsage">--</div>
                    </div>
                    <div class="status-item">
                        <div class="label">网络速度</div>
                        <div class="value" id="networkSpeed">--</div>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="refreshStatus()">🔄 刷新状态</button>
            </div>
        </div>
    </div>
    
    <script>
        let ws;
        let reconnectInterval;
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.hostname}:15000/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                document.getElementById('connectionStatus').className = 'status connected';
                document.getElementById('connectionStatus').textContent = '已连接';
                clearInterval(reconnectInterval);
                console.log('WebSocket连接成功');
            };
            
            ws.onclose = function() {
                document.getElementById('connectionStatus').className = 'status disconnected';
                document.getElementById('connectionStatus').textContent = '已断开';
                reconnectInterval = setInterval(connect, 3000);
                console.log('WebSocket连接断开，正在重连...');
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
                    break;
                case 'system_status':
                    updateSystemStatus(message.data);
                    break;
                case 'screenshot':
                    displayScreenshot(message.data);
                    break;
                case 'error':
                    alert('错误: ' + message.message);
                    break;
                case 'success':
                    console.log('操作成功');
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
        
        // AI对话
        function sendChat() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if(message) {
                addMessage('user', message);
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
        
        // 鼠标控制
        let mouseX = 960;
        let mouseY = 540;
        
        function updateMouseX(value) {
            mouseX = parseInt(value);
            document.getElementById('mouseX').textContent = value;
        }
        
        function updateMouseY(value) {
            mouseY = parseInt(value);
            document.getElementById('mouseY').textContent = value;
        }
        
        function moveMouse() {
            sendMessage('mouse_move', { x: mouseX, y: mouseY });
        }
        
        function moveMouseRelative() {
            sendMessage('mouse_move_relative', { dx: 50, dy: 50 });
        }
        
        function clickMouse(button) {
            sendMessage('mouse_click', { button });
        }
        
        function scrollMouse(direction) {
            sendMessage('mouse_scroll', { direction });
        }
        
        function dragMouse(action) {
            sendMessage('mouse_drag', { action });
        }
        
        // 键盘控制
        function typeText() {
            const text = document.getElementById('keyboardInput').value;
            sendMessage('keyboard_type', { text });
        }
        
        function pressHotkey(hotkey) {
            sendMessage('keyboard_hotkey', { hotkey });
        }
        
        function pressKey(key) {
            sendMessage('keyboard_press', { key });
        }
        
        // 系统控制
        function minimizeWindow() {
            sendMessage('system_minimize', {});
        }
        
        function maximizeWindow() {
            sendMessage('system_maximize', {});
        }
        
        function restoreWindow() {
            sendMessage('system_restore', {});
        }
        
        function closeWindow() {
            sendMessage('system_close', {});
        }
        
        function lockScreen() {
            sendMessage('system_lock', {});
        }
        
        function shutdownPC() {
            if(confirm('确定要关机吗？')) {
                sendMessage('system_shutdown', {});
            }
        }
        
        function restartPC() {
            if(confirm('确定要重启吗？')) {
                sendMessage('system_restart', {});
            }
        }
        
        function sleepPC() {
            sendMessage('system_sleep', {});
        }
        
        // 音量控制
        let volume = 50;
        
        function updateVolume(value) {
            volume = parseInt(value);
            document.getElementById('volumeValue').textContent = value;
        }
        
        function setVolume() {
            sendMessage('system_volume', { volume });
        }
        
        function muteVolume() {
            sendMessage('system_mute', {});
        }
        
        // 视觉捕获
        function takeScreenshot(region) {
            sendMessage('vision_screenshot', { region: region || 'full' });
        }
        
        function saveScreenshot() {
            sendMessage('vision_save_screenshot', {});
        }
        
        function toggleCamera() {
            sendMessage('vision_camera_toggle', {});
        }
        
        function capturePhoto() {
            sendMessage('vision_camera_capture', {});
        }
        
        function displayScreenshot(base64Data) {
            const preview = document.getElementById('screenshotPreview');
            preview.innerHTML = `<img src="data:image/png;base64,${base64Data}" class="screenshot-preview" alt="截图">`;
        }
        
        // 系统状态
        function refreshStatus() {
            sendMessage('system_status', {});
        }
        
        function updateSystemStatus(status) {
            document.getElementById('cpuUsage').textContent = status.cpu + '%';
            document.getElementById('memoryUsage').textContent = status.memory + '%';
            document.getElementById('diskUsage').textContent = status.disk + '%';
            document.getElementById('networkSpeed').textContent = status.network;
        }
        
        // 页面加载时连接
        window.addEventListener('load', connect);
    </script>
</body>
</html>
"""
        
        with open(os.path.join(self.web_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"网页文件已创建: {os.path.join(self.web_dir, 'index.html')}")
    
    async def _handle_client(self, websocket, path):
        """处理单个客户端连接"""
        self.clients.add(websocket)
        logger.info(f"客户端已连接: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            logger.info(f"客户端已断开: {websocket.remote_address}")
    
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
            'mouse_move': self._handle_mouse_move,
            'mouse_move_relative': self._handle_mouse_move_relative,
            'mouse_click': self._handle_mouse_click,
            'mouse_scroll': self._handle_mouse_scroll,
            'mouse_drag': self._handle_mouse_drag,
            'keyboard_type': self._handle_keyboard_type,
            'keyboard_hotkey': self._handle_keyboard_hotkey,
            'keyboard_press': self._handle_keyboard_press,
            'system_minimize': self._handle_system_minimize,
            'system_maximize': self._handle_system_maximize,
            'system_restore': self._handle_system_restore,
            'system_close': self._handle_system_close,
            'system_lock': self._handle_system_lock,
            'system_shutdown': self._handle_system_shutdown,
            'system_restart': self._handle_system_restart,
            'system_sleep': self._handle_system_sleep,
            'system_volume': self._handle_system_volume,
            'system_mute': self._handle_system_mute,
            'system_status': self._handle_system_status,
            'vision_screenshot': self._handle_vision_screenshot,
            'vision_save_screenshot': self._handle_vision_save_screenshot,
            'vision_camera_toggle': self._handle_vision_camera_toggle,
            'vision_camera_capture': self._handle_vision_camera_capture,
        }
        
        handler = commands.get(command_type)
        if handler:
            return await handler(data)
        
        return {'type': 'error', 'message': f'未知命令: {command_type}'}
    
    async def _handle_chat(self, data):
        """处理聊天消息"""
        message = data.get('message', '')
        if not message:
            return {'type': 'error', 'message': '消息不能为空'}
        
        # 这里应该调用AI服务，但由于是演示，返回模拟响应
        response = f"收到消息: {message}\n\n这是一个模拟响应。在实际应用中，这里会调用AI服务生成回复。"
        return {'type': 'chat_response', 'content': response}
    
    async def _handle_mouse_move(self, data):
        """处理鼠标移动"""
        x = data.get('x', 0)
        y = data.get('y', 0)
        self.system_controller.move_mouse(x, y)
        return {'type': 'success', 'message': f'鼠标已移动到 ({x}, {y})'}
    
    async def _handle_mouse_move_relative(self, data):
        """处理鼠标相对移动"""
        dx = data.get('dx', 0)
        dy = data.get('dy', 0)
        self.system_controller.move_mouse_relative(dx, dy)
        return {'type': 'success', 'message': f'鼠标相对移动 ({dx}, {dy})'}
    
    async def _handle_mouse_click(self, data):
        """处理鼠标点击"""
        button = data.get('button', 'left')
        self.system_controller.click_mouse(button)
        return {'type': 'success', 'message': f'{button}键点击'}
    
    async def _handle_mouse_scroll(self, data):
        """处理鼠标滚动"""
        direction = data.get('direction', 'up')
        self.system_controller.scroll_mouse(direction)
        return {'type': 'success', 'message': f'鼠标{direction}滚动'}
    
    async def _handle_mouse_drag(self, data):
        """处理鼠标拖拽"""
        action = data.get('action', 'start')
        if action == 'start':
            self.system_controller.start_drag()
        else:
            self.system_controller.stop_drag()
        return {'type': 'success', 'message': f'拖拽{action}'}
    
    async def _handle_keyboard_type(self, data):
        """处理键盘输入"""
        text = data.get('text', '')
        self.system_controller.type_text(text)
        return {'type': 'success', 'message': f'已输入: {text}'}
    
    async def _handle_keyboard_hotkey(self, data):
        """处理快捷键"""
        hotkey = data.get('hotkey', '')
        self.system_controller.press_hotkey(hotkey)
        return {'type': 'success', 'message': f'已执行: {hotkey}'}
    
    async def _handle_keyboard_press(self, data):
        """处理按键"""
        key = data.get('key', '')
        self.system_controller.press_key(key)
        return {'type': 'success', 'message': f'已按下: {key}'}
    
    async def _handle_system_minimize(self, data):
        """处理窗口最小化"""
        self.system_controller.minimize_window()
        return {'type': 'success', 'message': '窗口已最小化'}
    
    async def _handle_system_maximize(self, data):
        """处理窗口最大化"""
        self.system_controller.maximize_window()
        return {'type': 'success', 'message': '窗口已最大化'}
    
    async def _handle_system_restore(self, data):
        """处理窗口还原"""
        self.system_controller.restore_window()
        return {'type': 'success', 'message': '窗口已还原'}
    
    async def _handle_system_close(self, data):
        """处理窗口关闭"""
        self.system_controller.close_window()
        return {'type': 'success', 'message': '窗口已关闭'}
    
    async def _handle_system_lock(self, data):
        """处理锁屏"""
        self.system_controller.lock_screen()
        return {'type': 'success', 'message': '屏幕已锁定'}
    
    async def _handle_system_shutdown(self, data):
        """处理关机"""
        self.system_controller.shutdown()
        return {'type': 'success', 'message': '系统即将关机'}
    
    async def _handle_system_restart(self, data):
        """处理重启"""
        self.system_controller.restart()
        return {'type': 'success', 'message': '系统即将重启'}
    
    async def _handle_system_sleep(self, data):
        """处理睡眠"""
        self.system_controller.sleep()
        return {'type': 'success', 'message': '系统即将进入睡眠'}
    
    async def _handle_system_volume(self, data):
        """处理音量设置"""
        volume = data.get('volume', 50)
        self.system_controller.set_volume(volume)
        return {'type': 'success', 'message': f'音量已设置为 {volume}%'}
    
    async def _handle_system_mute(self, data):
        """处理静音"""
        self.system_controller.toggle_mute()
        return {'type': 'success', 'message': '静音状态已切换'}
    
    async def _handle_system_status(self, data):
        """处理系统状态查询"""
        status = self.system_controller.get_system_status()
        return {'type': 'system_status', 'data': status}
    
    async def _handle_vision_screenshot(self, data):
        """处理截图"""
        region = data.get('region', 'full')
        screenshot_data = self.vision_capture.take_screenshot(region)
        return {'type': 'screenshot', 'data': screenshot_data}
    
    async def _handle_vision_save_screenshot(self, data):
        """处理保存截图"""
        self.vision_capture.save_screenshot()
        return {'type': 'success', 'message': '截图已保存'}
    
    async def _handle_vision_camera_toggle(self, data):
        """处理摄像头开关"""
        self.vision_capture.toggle_camera()
        return {'type': 'success', 'message': '摄像头状态已切换'}
    
    async def _handle_vision_camera_capture(self, data):
        """处理拍照"""
        photo_data = self.vision_capture.capture_photo()
        return {'type': 'screenshot', 'data': photo_data}
    
    async def _http_handler(self, path, request_headers):
        """处理HTTP请求，提供静态文件服务"""
        if path == "/" or path == "/index.html":
            file_path = os.path.join(self.web_dir, "index.html")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    content = f.read()
                return (
                    200,
                    [("Content-Type", "text/html; charset=utf-8")],
                    content,
                )
        return (404, [("Content-Type", "text/plain")], b"Not Found")
    
    async def _start_server(self):
        """启动WebSocket服务器（同时支持HTTP静态文件服务）"""
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            process_request=self._http_handler
        )
        logger.info(f"WebSocket服务器已启动: ws://{self.host}:{self.port}/ws")
        logger.info(f"网页控制端: http://{self.host}:{self.port}")
        
        await self.server.wait_closed()
    
    def _run_server(self):
        """在子线程中运行服务器"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._start_server())
    
    def start(self):
        """在后台线程中启动服务器"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动RCON广播服务器
        self.rcon_server.start()
        
        # 启动主WebSocket服务器
        self.thread = threading.Thread(
            target=self._run_server,
            daemon=True
        )
        self.thread.start()
    
    def stop(self):
        """停止服务器"""
        self.is_running = False
        
        # 停止RCON广播服务器
        self.rcon_server.stop()
        
        # 停止主WebSocket服务器
        if self.server:
            self.server.close()
        logger.info("WebSocket服务器已停止")
    
    def broadcast_rcon(self, message_type, content):
        """向RCON客户端广播消息"""
        self.rcon_server.broadcast(message_type, content)

if __name__ == "__main__":
    server = WebSocketServer()
    server.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()