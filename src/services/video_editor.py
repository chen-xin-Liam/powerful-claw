import asyncio
import websockets
import json
import threading
import time
import os
import sys
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import get_logger

logger = get_logger(__name__)

class VideoEditorHTTPServerHandler(BaseHTTPRequestHandler):
    def __init__(self, web_dir, *args, **kwargs):
        self.web_dir = web_dir
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
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
        
        if self.path.endswith(".css"):
            file_path = os.path.join(self.web_dir, self.path.lstrip("/"))
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/css; charset=utf-8")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
                return
        
        if self.path.endswith(".js"):
            file_path = os.path.join(self.web_dir, self.path.lstrip("/"))
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
                return
        
        if self.path == "/api/media":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps([]).encode())
            return
        
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not Found")

class VideoEditor:
    def __init__(self):
        self.port = 15010
        self.ws_port = 15012
        self._http_server = None
        self._http_thread = None
        self._ws_server = None
        self._ws_thread = None
        self._event_loop = None
        self.clients: List[websockets.WebSocketServerProtocol] = []
        self._lock = threading.RLock()
        self.is_running = False
        
        # 项目状态
        self.project = {
            'name': '未命名项目',
            'fps': 24,
            'resolution': '1920x1080',
            'duration': 3600,
            'tracks': [
                {'id': 'track_1', 'type': 'video', 'name': 'V1', 'height': 60, 'locked': False, 'solo': False, 'muted': False},
                {'id': 'track_2', 'type': 'video', 'name': 'V2', 'height': 60, 'locked': False, 'solo': False, 'muted': False},
                {'id': 'track_3', 'type': 'audio', 'name': 'A1', 'height': 60, 'locked': False, 'solo': False, 'muted': False},
                {'id': 'track_4', 'type': 'subtitle', 'name': 'T1', 'height': 40, 'locked': False, 'solo': False, 'muted': False},
                {'id': 'track_5', 'type': 'pip', 'name': 'PIP1', 'height': 60, 'locked': False, 'solo': False, 'muted': False}
            ],
            'markers': [],
            'clips': [],
            'effects': [],
            'transitions': []
        }
        
        # 媒体库
        self.media_library = [
            {'id': 'media_1', 'name': '风景视频.mp4', 'type': 'video', 'duration': 120, 'fps': 24, 'resolution': '1920x1080', 'codec': 'H.264', 'size': '50MB', 'thumbnail': 'https://picsum.photos/400/225?random=1'},
            {'id': 'media_2', 'name': '城市延时.mp4', 'type': 'video', 'duration': 180, 'fps': 30, 'resolution': '3840x2160', 'codec': 'ProRes', 'size': '200MB', 'thumbnail': 'https://picsum.photos/400/225?random=2'},
            {'id': 'media_3', 'name': '背景音乐.mp3', 'type': 'audio', 'duration': 300, 'codec': 'MP3', 'size': '5MB', 'thumbnail': '🎵'},
            {'id': 'media_4', 'name': '图片素材.jpg', 'type': 'image', 'duration': 30, 'resolution': '1920x1080', 'size': '2MB', 'thumbnail': 'https://picsum.photos/400/225?random=3'},
            {'id': 'media_5', 'name': '字幕文件.srt', 'type': 'subtitle', 'duration': 60, 'size': '1KB', 'thumbnail': '📝'},
            {'id': 'media_6', 'name': '动画GIF.gif', 'type': 'gif', 'duration': 5, 'fps': 15, 'size': '10MB', 'thumbnail': 'https://picsum.photos/400/225?random=4'}
        ]
        
        # 时间轴状态
        self.timeline_state = {
            'current_time': 0,
            'playhead_position': 0,
            'is_playing': False,
            'zoom': 1.0,
            'visible_range': [0, 300]
        }
    
    def start(self):
        if self.is_running:
            return
        
        self.is_running = True
        
        self._http_thread = threading.Thread(
            target=self._http_thread_func,
            daemon=True,
            name="VideoEditorHTTP"
        )
        self._http_thread.start()
        
        self._ws_thread = threading.Thread(
            target=self._ws_thread_func,
            daemon=True,
            name="VideoEditorWS"
        )
        self._ws_thread.start()
        
        logger.info(f"视频剪辑页面已启动：http://0.0.0.0:{self.port}")
        logger.info(f"WebSocket 服务器已启动：ws://0.0.0.0:{self.ws_port}")
    
    def stop(self):
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._http_server:
            self._http_server.shutdown()
            self._http_server.server_close()
        
        if self._ws_server:
            self._ws_server.close()
        
        logger.info("视频剪辑服务器已停止")
    
    def _http_thread_func(self):
        web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_editor")
        os.makedirs(web_dir, exist_ok=True)
        self._create_web_pages(web_dir)
        
        handler = lambda *args, **kwargs: VideoEditorHTTPServerHandler(web_dir, *args, **kwargs)
        self._http_server = HTTPServer(('0.0.0.0', self.port), handler)
        logger.info(f"HTTP 服务器已启动：http://0.0.0.0:{self.port}")
        self._http_server.serve_forever()
    
    def _ws_thread_func(self):
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        self._event_loop.run_until_complete(self._run_ws_server())
    
    async def _run_ws_server(self):
        self._ws_server = await websockets.serve(
            self._handle_client,
            '0.0.0.0',
            self.ws_port
        )
        await self._ws_server.wait_closed()
    
    async def _handle_client(self, websocket):
        with self._lock:
            self.clients.append(websocket)
        
        try:
            await websocket.send(json.dumps({
                'type': 'init',
                'project': self.project,
                'media_library': self.media_library,
                'timeline': self.timeline_state
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    command = data.get('command')
                    
                    # 素材管理
                    if command == 'import_media':
                        await self._handle_import_media(websocket, data)
                    elif command == 'get_media':
                        await self._handle_get_media(websocket, data)
                    elif command == 'delete_media':
                        await self._handle_delete_media(websocket, data)
                    elif command == 'rename_media':
                        await self._handle_rename_media(websocket, data)
                    elif command == 'tag_media':
                        await self._handle_tag_media(websocket, data)
                    
                    # 时间轴操作
                    elif command == 'add_clip':
                        await self._handle_add_clip(websocket, data)
                    elif command == 'edit_clip':
                        await self._handle_edit_clip(websocket, data)
                    elif command == 'delete_clip':
                        await self._handle_delete_clip(websocket, data)
                    elif command == 'move_clip':
                        await self._handle_move_clip(websocket, data)
                    elif command == 'trim_clip':
                        await self._handle_trim_clip(websocket, data)
                    elif command == 'split_clip':
                        await self._handle_split_clip(websocket, data)
                    elif command == 'copy_clip':
                        await self._handle_copy_clip(websocket, data)
                    
                    # 轨道操作
                    elif command == 'add_track':
                        await self._handle_add_track(websocket, data)
                    elif command == 'remove_track':
                        await self._handle_remove_track(websocket, data)
                    elif command == 'toggle_track':
                        await self._handle_toggle_track(websocket, data)
                    
                    # 标记
                    elif command == 'add_marker':
                        await self._handle_add_marker(websocket, data)
                    elif command == 'delete_marker':
                        await self._handle_delete_marker(websocket, data)
                    
                    # 播放控制
                    elif command == 'set_time':
                        await self._handle_set_time(websocket, data)
                    elif command == 'play':
                        await self._handle_play(websocket, data)
                    elif command == 'pause':
                        await self._handle_pause(websocket, data)
                    elif command == 'zoom':
                        await self._handle_zoom(websocket, data)
                    
                    # 调色与特效
                    elif command == 'color_correction':
                        await self._handle_color_correction(websocket, data)
                    elif command == 'add_effect':
                        await self._handle_add_effect(websocket, data)
                    elif command == 'add_transition':
                        await self._handle_add_transition(websocket, data)
                    
                    # 音频处理
                    elif command == 'audio_adjust':
                        await self._handle_audio_adjust(websocket, data)
                    elif command == 'add_audio_effect':
                        await self._handle_add_audio_effect(websocket, data)
                    
                    # 字幕
                    elif command == 'add_subtitle':
                        await self._handle_add_subtitle(websocket, data)
                    elif command == 'edit_subtitle':
                        await self._handle_edit_subtitle(websocket, data)
                    
                    # 导出
                    elif command == 'export':
                        await self._handle_export(websocket, data)
                    elif command == 'save_project':
                        await self._handle_save_project(websocket, data)
                    
                except Exception as e:
                    logger.error(f"处理消息失败：{e}", exc_info=True)
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            with self._lock:
                if websocket in self.clients:
                    self.clients.remove(websocket)
    
    # ========== 素材管理 ==========
    async def _handle_import_media(self, websocket, data):
        files = data.get('files', [])
        imported = []
        
        for f in files:
            media_item = {
                'id': f'media_{uuid.uuid4().hex[:8]}',
                'name': f.get('name', 'untitled'),
                'type': f.get('type', 'video'),
                'duration': f.get('duration', 30),
                'fps': f.get('fps', 24),
                'resolution': f.get('resolution', '1920x1080'),
                'codec': f.get('codec', 'H.264'),
                'size': f.get('size', '10MB'),
                'thumbnail': f.get('thumbnail', f'https://picsum.photos/400/225?random={len(self.media_library)}'),
                'tags': [],
                'rating': 0
            }
            self.media_library.append(media_item)
            imported.append(media_item)
        
        await self._broadcast({
            'type': 'media_imported',
            'items': imported
        })
    
    async def _handle_get_media(self, websocket, data):
        filter_type = data.get('type', 'all')
        search_query = data.get('search', '')
        
        filtered = self.media_library
        if filter_type != 'all':
            filtered = [m for m in filtered if m['type'] == filter_type]
        if search_query:
            filtered = [m for m in filtered if search_query.lower() in m['name'].lower()]
        
        await websocket.send(json.dumps({
            'type': 'media_list',
            'items': filtered
        }))
    
    async def _handle_delete_media(self, websocket, data):
        media_id = data.get('media_id')
        self.media_library = [m for m in self.media_library if m['id'] != media_id]
        
        await self._broadcast({
            'type': 'media_deleted',
            'media_id': media_id
        })
    
    async def _handle_rename_media(self, websocket, data):
        media_id = data.get('media_id')
        new_name = data.get('name')
        
        for media in self.media_library:
            if media['id'] == media_id:
                media['name'] = new_name
                break
        
        await self._broadcast({
            'type': 'media_renamed',
            'media_id': media_id,
            'name': new_name
        })
    
    async def _handle_tag_media(self, websocket, data):
        media_id = data.get('media_id')
        tags = data.get('tags', [])
        
        for media in self.media_library:
            if media['id'] == media_id:
                media['tags'] = tags
                break
        
        await self._broadcast({
            'type': 'media_tagged',
            'media_id': media_id,
            'tags': tags
        })
    
    # ========== 时间轴操作 ==========
    async def _handle_add_clip(self, websocket, data):
        clip = {
            'id': f'clip_{uuid.uuid4().hex[:8]}',
            'media_id': data.get('media_id'),
            'track': data.get('track', 0),
            'start_time': data.get('start_time', 0),
            'in_point': data.get('in_point', 0),
            'out_point': data.get('out_point', 100),
            'duration': data.get('duration', 100),
            'name': data.get('name', 'clip'),
            'effects': [],
            'color_correction': {},
            'audio_level': 1.0,
            'speed': 1.0,
            'enabled': True,
            'locked': False,
            'position': {'x': 0, 'y': 0},
            'scale': 1.0,
            'rotation': 0,
            'opacity': 1.0
        }
        self.project['clips'].append(clip)
        
        await self._broadcast({
            'type': 'clip_added',
            'clip': clip
        })
    
    async def _handle_edit_clip(self, websocket, data):
        clip_id = data.get('clip_id')
        updates = data.get('updates', {})
        
        for clip in self.project['clips']:
            if clip['id'] == clip_id:
                clip.update(updates)
                break
        
        await self._broadcast({
            'type': 'clip_updated',
            'clip_id': clip_id,
            'updates': updates
        })
    
    async def _handle_delete_clip(self, websocket, data):
        clip_id = data.get('clip_id')
        self.project['clips'] = [c for c in self.project['clips'] if c['id'] != clip_id]
        
        await self._broadcast({
            'type': 'clip_deleted',
            'clip_id': clip_id
        })
    
    async def _handle_move_clip(self, websocket, data):
        clip_id = data.get('clip_id')
        new_track = data.get('track')
        new_start = data.get('start_time')
        
        for clip in self.project['clips']:
            if clip['id'] == clip_id:
                clip['track'] = new_track
                clip['start_time'] = new_start
                break
        
        await self._broadcast({
            'type': 'clip_moved',
            'clip_id': clip_id,
            'track': new_track,
            'start_time': new_start
        })
    
    async def _handle_trim_clip(self, websocket, data):
        clip_id = data.get('clip_id')
        in_point = data.get('in_point')
        out_point = data.get('out_point')
        
        for clip in self.project['clips']:
            if clip['id'] == clip_id:
                if in_point is not None:
                    clip['in_point'] = in_point
                if out_point is not None:
                    clip['out_point'] = out_point
                clip['duration'] = clip['out_point'] - clip['in_point']
                break
        
        await self._broadcast({
            'type': 'clip_trimmed',
            'clip_id': clip_id,
            'in_point': in_point,
            'out_point': out_point
        })
    
    async def _handle_split_clip(self, websocket, data):
        clip_id = data.get('clip_id')
        split_time = data.get('split_time')
        
        for i, clip in enumerate(self.project['clips']):
            if clip['id'] == clip_id:
                # 创建第二个片段
                new_clip = clip.copy()
                new_clip['id'] = f'clip_{uuid.uuid4().hex[:8]}'
                new_clip['start_time'] = split_time
                new_clip['in_point'] = split_time - clip['start_time'] + clip['in_point']
                new_clip['duration'] = clip['out_point'] - new_clip['in_point']
                new_clip['out_point'] = clip['out_point']
                
                # 更新第一个片段
                clip['out_point'] = split_time - clip['start_time'] + clip['in_point']
                clip['duration'] = clip['out_point'] - clip['in_point']
                
                self.project['clips'].insert(i + 1, new_clip)
                break
        
        await self._broadcast({
            'type': 'clip_split',
            'clip_id': clip_id,
            'split_time': split_time
        })
    
    async def _handle_copy_clip(self, websocket, data):
        clip_id = data.get('clip_id')
        
        for clip in self.project['clips']:
            if clip['id'] == clip_id:
                new_clip = clip.copy()
                new_clip['id'] = f'clip_{uuid.uuid4().hex[:8]}'
                new_clip['start_time'] = clip['start_time'] + clip['duration'] + 10
                self.project['clips'].append(new_clip)
                break
        
        await self._broadcast({
            'type': 'clip_copied',
            'clip_id': clip_id
        })
    
    # ========== 轨道操作 ==========
    async def _handle_add_track(self, websocket, data):
        track_type = data.get('type', 'video')
        track_count = len([t for t in self.project['tracks'] if t['type'] == track_type]) + 1
        
        track = {
            'id': f'track_{uuid.uuid4().hex[:8]}',
            'type': track_type,
            'name': f'{track_type[0].upper()}{track_count}',
            'height': 60,
            'locked': False,
            'solo': False,
            'muted': False,
            'visible': True
        }
        self.project['tracks'].append(track)
        
        await self._broadcast({
            'type': 'track_added',
            'track': track
        })
    
    async def _handle_remove_track(self, websocket, data):
        track_id = data.get('track_id')
        self.project['tracks'] = [t for t in self.project['tracks'] if t['id'] != track_id]
        self.project['clips'] = [c for c in self.project['clips'] if c['track'] != track_id]
        
        await self._broadcast({
            'type': 'track_removed',
            'track_id': track_id
        })
    
    async def _handle_toggle_track(self, websocket, data):
        track_id = data.get('track_id')
        toggle_type = data.get('type', 'muted')
        
        for track in self.project['tracks']:
            if track['id'] == track_id:
                track[toggle_type] = not track[toggle_type]
                break
        
        await self._broadcast({
            'type': 'track_toggled',
            'track_id': track_id,
            'type': toggle_type,
            'value': track[toggle_type]
        })
    
    # ========== 标记 ==========
    async def _handle_add_marker(self, websocket, data):
        marker = {
            'id': f'marker_{uuid.uuid4().hex[:8]}',
            'time': data.get('time', 0),
            'color': data.get('color', 'red'),
            'comment': data.get('comment', ''),
            'type': data.get('type', 'comment')
        }
        self.project['markers'].append(marker)
        
        await self._broadcast({
            'type': 'marker_added',
            'marker': marker
        })
    
    async def _handle_delete_marker(self, websocket, data):
        marker_id = data.get('marker_id')
        self.project['markers'] = [m for m in self.project['markers'] if m['id'] != marker_id]
        
        await self._broadcast({
            'type': 'marker_deleted',
            'marker_id': marker_id
        })
    
    # ========== 播放控制 ==========
    async def _handle_set_time(self, websocket, data):
        self.timeline_state['current_time'] = data.get('time', 0)
        
        await self._broadcast({
            'type': 'time_updated',
            'time': self.timeline_state['current_time']
        })
    
    async def _handle_play(self, websocket, data):
        self.timeline_state['is_playing'] = True
        self._start_playback()
        
        await self._broadcast({
            'type': 'playing',
            'state': True
        })
    
    def _start_playback(self):
        import threading
        def playback_loop():
            while self.timeline_state['is_playing'] and self.timeline_state['current_time'] < self.project['duration']:
                import time
                time.sleep(0.05)  # 20fps 更新频率
                self.timeline_state['current_time'] += 5  # 每帧前进5个时间单位
                
                # 发送时间更新
                import asyncio
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({'type': 'time_updated', 'time': self.timeline_state['current_time']}),
                    self._event_loop
                )
                
                if self.timeline_state['current_time'] >= self.project['duration']:
                    self.timeline_state['is_playing'] = False
                    asyncio.run_coroutine_threadsafe(
                        self._broadcast({'type': 'playing', 'state': False}),
                        self._event_loop
                    )
        
        thread = threading.Thread(target=playback_loop, daemon=True)
        thread.start()
    
    async def _handle_pause(self, websocket, data):
        self.timeline_state['is_playing'] = False
        
        await self._broadcast({
            'type': 'playing',
            'state': False
        })
    
    async def _handle_zoom(self, websocket, data):
        self.timeline_state['zoom'] = data.get('zoom', 1.0)
        
        await self._broadcast({
            'type': 'zoom_updated',
            'zoom': self.timeline_state['zoom']
        })
    
    # ========== 调色与特效 ==========
    async def _handle_color_correction(self, websocket, data):
        clip_id = data.get('clip_id')
        correction = data.get('correction', {})
        
        for clip in self.project['clips']:
            if clip['id'] == clip_id:
                clip['color_correction'] = correction
                break
        
        await self._broadcast({
            'type': 'color_corrected',
            'clip_id': clip_id,
            'correction': correction
        })
    
    async def _handle_add_effect(self, websocket, data):
        clip_id = data.get('clip_id')
        effect = data.get('effect', {})
        
        for clip in self.project['clips']:
            if clip['id'] == clip_id:
                clip['effects'].append(effect)
                break
        
        await self._broadcast({
            'type': 'effect_added',
            'clip_id': clip_id,
            'effect': effect
        })
    
    async def _handle_add_transition(self, websocket, data):
        transition = {
            'id': f'transition_{uuid.uuid4().hex[:8]}',
            'type': data.get('type', 'fade'),
            'start_time': data.get('start_time', 0),
            'duration': data.get('duration', 30),
            'track': data.get('track', 0)
        }
        self.project['transitions'].append(transition)
        
        await self._broadcast({
            'type': 'transition_added',
            'transition': transition
        })
    
    # ========== 音频处理 ==========
    async def _handle_audio_adjust(self, websocket, data):
        clip_id = data.get('clip_id')
        level = data.get('level', 1.0)
        pan = data.get('pan', 0)
        
        for clip in self.project['clips']:
            if clip['id'] == clip_id:
                clip['audio_level'] = level
                clip['audio_pan'] = pan
                break
        
        await self._broadcast({
            'type': 'audio_adjusted',
            'clip_id': clip_id,
            'level': level,
            'pan': pan
        })
    
    async def _handle_add_audio_effect(self, websocket, data):
        clip_id = data.get('clip_id')
        effect_type = data.get('type')
        
        for clip in self.project['clips']:
            if clip['id'] == clip_id:
                clip['effects'].append({'type': effect_type})
                break
        
        await self._broadcast({
            'type': 'audio_effect_added',
            'clip_id': clip_id,
            'type': effect_type
        })
    
    # ========== 字幕 ==========
    async def _handle_add_subtitle(self, websocket, data):
        subtitle = {
            'id': f'sub_{uuid.uuid4().hex[:8]}',
            'track': data.get('track', 3),
            'start_time': data.get('start_time', 0),
            'end_time': data.get('end_time', 50),
            'text': data.get('text', ''),
            'style': data.get('style', {'font': 'Arial', 'size': 24, 'color': '#ffffff'})
        }
        
        clip = {
            'id': subtitle['id'],
            'media_id': subtitle['id'],
            'track': subtitle['track'],
            'start_time': subtitle['start_time'],
            'in_point': 0,
            'out_point': subtitle['end_time'] - subtitle['start_time'],
            'duration': subtitle['end_time'] - subtitle['start_time'],
            'name': '字幕',
            'effects': [],
            'color_correction': {},
            'audio_level': 1.0,
            'speed': 1.0,
            'enabled': True,
            'locked': False,
            'subtitle_data': subtitle
        }
        self.project['clips'].append(clip)
        
        await self._broadcast({
            'type': 'subtitle_added',
            'subtitle': subtitle
        })
    
    async def _handle_edit_subtitle(self, websocket, data):
        subtitle_id = data.get('subtitle_id')
        updates = data.get('updates', {})
        
        for clip in self.project['clips']:
            if clip['id'] == subtitle_id and 'subtitle_data' in clip:
                clip['subtitle_data'].update(updates)
                if 'start_time' in updates:
                    clip['start_time'] = updates['start_time']
                if 'end_time' in updates:
                    clip['out_point'] = updates['end_time'] - clip['start_time']
                    clip['duration'] = clip['out_point']
                break
        
        await self._broadcast({
            'type': 'subtitle_updated',
            'subtitle_id': subtitle_id,
            'updates': updates
        })
    
    # ========== 导出 ==========
    async def _handle_export(self, websocket, data):
        await websocket.send(json.dumps({
            'type': 'export_started',
            'progress': 0
        }))
        
        for i in range(101):
            await asyncio.sleep(0.05)
            await websocket.send(json.dumps({
                'type': 'export_progress',
                'progress': i
            }))
        
        await websocket.send(json.dumps({
            'type': 'export_complete',
            'path': '/exports/project.mp4'
        }))
    
    async def _handle_save_project(self, websocket, data):
        project_name = data.get('name', self.project['name'])
        self.project['name'] = project_name
        
        await websocket.send(json.dumps({
            'type': 'project_saved',
            'name': project_name
        }))
    
    async def _broadcast(self, message):
        with self._lock:
            clients = list(self.clients)
        
        for client in clients:
            try:
                await client.send(json.dumps(message))
            except Exception as e:
                logger.debug(f"广播消息失败，移除客户端: {e}")
                with self._lock:
                    if client in self.clients:
                        self.clients.remove(client)
    
    def _create_web_pages(self, web_dir):
        self._create_main_page(web_dir)
        self._create_css_file(web_dir)
        self._create_js_file(web_dir)
    
    def _create_main_page(self, web_dir):
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>专业视频剪辑 - Video Editor Pro</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header class="toolbar">
        <div class="toolbar-left">
            <button class="btn btn-icon" onclick="newProject()">📁 新建</button>
            <button class="btn btn-icon" onclick="openProject()">📂 打开</button>
            <button class="btn btn-icon" onclick="saveProject()">💾 保存</button>
            <button class="btn btn-icon" onclick="exportProject()">📤 导出</button>
        </div>
        <div class="toolbar-center">
            <span id="projectName">未命名项目</span>
        </div>
        <div class="toolbar-right">
            <button class="btn btn-icon" onclick="showSettings()">⚙️ 设置</button>
        </div>
    </header>

    <div class="main-container">
        <aside class="left-panel">
            <div class="panel-tabs">
                <button class="tab-btn active" onclick="showPanel('media')">📦 媒体库</button>
                <button class="tab-btn" onclick="showPanel('effects')">✨ 特效</button>
                <button class="tab-btn" onclick="showPanel('transitions')">🔄 转场</button>
                <button class="tab-btn" onclick="showPanel('text')">📝 文字</button>
                <button class="tab-btn" onclick="showPanel('audio')">🔊 音频</button>
            </div>
            
            <div id="mediaPanel" class="panel-content active">
                <div class="panel-header">
                    <button class="btn btn-small" onclick="importMedia()">📥 导入素材</button>
                    <div class="search-box">
                        <input type="text" id="mediaSearch" placeholder="搜索素材..." onkeyup="searchMedia()">
                    </div>
                </div>
                <div class="filter-bar">
                    <button class="filter-btn active" data-type="all">全部</button>
                    <button class="filter-btn" data-type="video">🎬 视频</button>
                    <button class="filter-btn" data-type="audio">🎵 音频</button>
                    <button class="filter-btn" data-type="image">🖼️ 图片</button>
                    <button class="filter-btn" data-type="subtitle">📑 字幕</button>
                    <button class="filter-btn" data-type="gif">🎞️ GIF</button>
                </div>
                <div id="mediaGrid" class="media-grid"></div>
            </div>
            
            <div id="effectsPanel" class="panel-content">
                <div class="effects-list">
                    <h4>视频特效</h4>
                    <div class="effect-items">
                        <button class="effect-btn" data-effect="blur">模糊</button>
                        <button class="effect-btn" data-effect="sharpen">锐化</button>
                        <button class="effect-btn" data-effect="brightness">亮度</button>
                        <button class="effect-btn" data-effect="contrast">对比度</button>
                        <button class="effect-btn" data-effect="saturation">饱和度</button>
                        <button class="effect-btn" data-effect="vintage">复古</button>
                        <button class="effect-btn" data-effect="glow">发光</button>
                        <button class="effect-btn" data-effect="noise">噪点</button>
                        <button class="effect-btn" data-effect="mosaic">马赛克</button>
                        <button class="effect-btn" data-effect="film">老电影</button>
                        <button class="effect-btn" data-effect="glitch">故障风</button>
                        <button class="effect-btn" data-effect="vignette">暗角</button>
                    </div>
                    <h4>LUT 预设</h4>
                    <div class="effect-items">
                        <button class="effect-btn" data-effect="cinematic">电影感</button>
                        <button class="effect-btn" data-effect="vivid">鲜艳</button>
                        <button class="effect-btn" data-effect="cool">冷色调</button>
                        <button class="effect-btn" data-effect="warm">暖色调</button>
                        <button class="effect-btn" data-effect="bw">黑白</button>
                        <button class="effect-btn" data-effect="teal">青橙</button>
                    </div>
                </div>
            </div>
            
            <div id="transitionsPanel" class="panel-content">
                <div class="effects-list">
                    <h4>常用转场</h4>
                    <div class="effect-items">
                        <button class="effect-btn" data-transition="fade">淡入淡出</button>
                        <button class="effect-btn" data-transition="crossfade">叠化</button>
                        <button class="effect-btn" data-transition="wipe">划像</button>
                        <button class="effect-btn" data-transition="zoom">缩放</button>
                        <button class="effect-btn" data-transition="slide">滑动</button>
                        <button class="effect-btn" data-transition="spin">旋转</button>
                        <button class="effect-btn" data-transition="flash">闪白</button>
                        <button class="effect-btn" data-transition="blur">模糊转场</button>
                        <button class="effect-btn" data-transition="push">推入</button>
                        <button class="effect-btn" data-transition="cube">3D立方体</button>
                    </div>
                </div>
            </div>
            
            <div id="textPanel" class="panel-content">
                <div class="text-tools">
                    <h4>文字样式</h4>
                    <input type="text" id="textInput" placeholder="输入文字..." class="text-input">
                    <div class="text-controls">
                        <select id="fontSelect">
                            <option>Arial</option>
                            <option>微软雅黑</option>
                            <option>宋体</option>
                            <option>黑体</option>
                        </select>
                        <input type="number" id="fontSize" value="24" min="12" max="72">
                        <input type="color" id="fontColor" value="#ffffff">
                    </div>
                    <button class="btn btn-primary" onclick="addText()">添加文字</button>
                    <h4>预设动画</h4>
                    <div class="effect-items">
                        <button class="effect-btn" data-animation="typewriter">打字机</button>
                        <button class="effect-btn" data-animation="fadeIn">渐显</button>
                        <button class="effect-btn" data-animation="bounce">弹跳</button>
                        <button class="effect-btn" data-animation="slideUp">上滑</button>
                    </div>
                </div>
            </div>
            
            <div id="audioPanel" class="panel-content">
                <div class="audio-tools">
                    <h4>音频效果</h4>
                    <div class="effect-items">
                        <button class="effect-btn" data-audio="denoise">降噪</button>
                        <button class="effect-btn" data-audio="reverb">混响</button>
                        <button class="effect-btn" data-audio="eq">均衡器</button>
                        <button class="effect-btn" data-audio="compressor">压缩器</button>
                        <button class="effect-btn" data-audio="pitch">变调</button>
                        <button class="effect-btn" data-audio="ducking">Ducking</button>
                    </div>
                    <h4>音频素材</h4>
                    <div class="audio-list">
                        <div class="audio-item" onclick="addAudioClip('music1')">🎵 背景音乐 1</div>
                        <div class="audio-item" onclick="addAudioClip('music2')">🎵 背景音乐 2</div>
                        <div class="audio-item" onclick="addAudioClip('sound1')">🔊 音效 1</div>
                        <div class="audio-item" onclick="addAudioClip('sound2')">🔊 音效 2</div>
                    </div>
                </div>
            </div>
        </aside>

        <section class="preview-area">
            <div class="preview-container">
                <canvas id="previewCanvas"></canvas>
                <div class="preview-overlay">
                    <div class="playback-controls">
                        <button class="control-btn" onclick="stepBackward()">⏪</button>
                        <button class="control-btn play-btn" id="playBtn" onclick="togglePlay()">▶</button>
                        <button class="control-btn" onclick="stepForward()">⏩</button>
                    </div>
                    <div class="timeline-slider">
                        <input type="range" id="timelineSlider" min="0" max="3600" value="0" 
                               oninput="seekTo(this.value)" onchange="seekTo(this.value)">
                    </div>
                    <div class="time-display">
                        <span id="currentTime">00:00:00.00</span> / <span id="totalTime">01:00:00.00</span>
                    </div>
                </div>
                <div class="preview-controls">
                    <button class="btn btn-small" onclick="toggleFullscreen()">⛶ 全屏</button>
                    <button class="btn btn-small" onclick="toggleCrop()">✂️ 裁剪</button>
                    <select id="speedSelect" onchange="changeSpeed()">
                        <option value="0.25">0.25x</option>
                        <option value="0.5">0.5x</option>
                        <option value="1" selected>1x</option>
                        <option value="1.5">1.5x</option>
                        <option value="2">2x</option>
                        <option value="4">4x</option>
                    </select>
                </div>
            </div>
        </section>

        <aside class="right-panel">
            <div class="panel-tabs">
                <button class="tab-btn active" onclick="showRightPanel('info')">📋 信息</button>
                <button class="tab-btn" onclick="showRightPanel('color')">🎨 调色</button>
                <button class="tab-btn" onclick="showRightPanel('transform')">🔄 变换</button>
                <button class="tab-btn" onclick="showRightPanel('effects')">✨ 特效</button>
                <button class="tab-btn" onclick="showRightPanel('audio')">🔊 音频</button>
                <button class="tab-btn" onclick="showRightPanel('subtitle')">📑 字幕</button>
            </div>
            
            <div id="infoPanel" class="panel-content active">
                <div class="info-section">
                    <h4>项目信息</h4>
                    <p><strong>名称:</strong> <span id="infoName">未命名项目</span></p>
                    <p><strong>帧率:</strong> <span id="infoFps">24 fps</span></p>
                    <p><strong>分辨率:</strong> <span id="infoRes">1920x1080</span></p>
                    <p><strong>时长:</strong> <span id="infoDuration">01:00:00</span></p>
                    <p><strong>轨道数:</strong> <span id="infoTracks">5</span></p>
                    <p><strong>片段数:</strong> <span id="infoClips">0</span></p>
                </div>
                <div class="info-section">
                    <h4>选中片段</h4>
                    <div id="clipInfo">
                        <p>请在时间轴上选择片段</p>
                    </div>
                </div>
            </div>
            
            <div id="colorPanel" class="panel-content">
                <div class="color-controls">
                    <div class="control-row">
                        <label>亮度</label>
                        <input type="range" id="brightness" min="-100" max="100" value="0">
                    </div>
                    <div class="control-row">
                        <label>对比度</label>
                        <input type="range" id="contrast" min="0" max="200" value="100">
                    </div>
                    <div class="control-row">
                        <label>饱和度</label>
                        <input type="range" id="saturation" min="0" max="200" value="100">
                    </div>
                    <div class="control-row">
                        <label>色温</label>
                        <input type="range" id="temperature" min="2000" max="10000" value="6500">
                    </div>
                    <div class="control-row">
                        <label>色调</label>
                        <input type="range" id="hue" min="-180" max="180" value="0">
                    </div>
                    <div class="control-row">
                        <label>锐化</label>
                        <input type="range" id="sharpen" min="0" max="100" value="0">
                    </div>
                    <button class="btn btn-primary" onclick="applyColorCorrection()">应用调色</button>
                </div>
            </div>
            
            <div id="transformPanel" class="panel-content">
                <div class="transform-controls">
                    <div class="control-row">
                        <label>位置 X</label>
                        <input type="number" id="posX" value="0">
                    </div>
                    <div class="control-row">
                        <label>位置 Y</label>
                        <input type="number" id="posY" value="0">
                    </div>
                    <div class="control-row">
                        <label>缩放</label>
                        <input type="range" id="scale" min="10" max="300" value="100">
                    </div>
                    <div class="control-row">
                        <label>旋转</label>
                        <input type="range" id="rotation" min="-180" max="180" value="0">
                    </div>
                    <div class="control-row">
                        <label>不透明度</label>
                        <input type="range" id="opacity" min="0" max="100" value="100">
                    </div>
                    <button class="btn btn-primary" onclick="applyTransform()">应用变换</button>
                </div>
            </div>
            
            <div id="rightEffectsPanel" class="panel-content">
                <div class="applied-effects">
                    <h4>已应用特效</h4>
                    <div id="effectsList"></div>
                </div>
            </div>
            
            <div id="rightAudioPanel" class="panel-content">
                <div class="audio-controls">
                    <div class="control-row">
                        <label>音量</label>
                        <input type="range" id="audioLevel" min="0" max="200" value="100">
                    </div>
                    <div class="control-row">
                        <label>平衡</label>
                        <input type="range" id="audioPan" min="-100" max="100" value="0">
                    </div>
                    <div class="control-row">
                        <label>淡入</label>
                        <input type="number" id="fadeIn" value="0">
                    </div>
                    <div class="control-row">
                        <label>淡出</label>
                        <input type="number" id="fadeOut" value="0">
                    </div>
                    <button class="btn btn-primary" onclick="applyAudioSettings()">应用音频设置</button>
                </div>
            </div>
            
            <div id="subtitlePanel" class="panel-content">
                <div class="subtitle-controls">
                    <input type="text" id="subtitleText" placeholder="输入字幕文本..." class="text-input">
                    <div class="control-row">
                        <label>开始时间</label>
                        <input type="number" id="subtitleStart" value="0">
                    </div>
                    <div class="control-row">
                        <label>持续时间</label>
                        <input type="number" id="subtitleDuration" value="200">
                    </div>
                    <button class="btn btn-primary" onclick="addSubtitle()">添加字幕</button>
                    <button class="btn btn-secondary" onclick="generateSubtitle()">🎙️ 自动生成字幕</button>
                </div>
            </div>
        </aside>
    </div>

    <footer class="timeline-container">
        <div class="timeline-header">
            <div class="zoom-controls">
                <button class="btn btn-small" onclick="zoomOut()">➖</button>
                <span id="zoomLevel">100%</span>
                <button class="btn btn-small" onclick="zoomIn()">➕</button>
                <button class="btn btn-small" onclick="zoomFit()">⟲ 适应</button>
            </div>
            <div class="timeline-tools">
                <button class="tool-btn active" data-tool="select" title="选择">👆</button>
                <button class="tool-btn" data-tool="cut" title="切割">✂️</button>
                <button class="tool-btn" data-tool="trim" title="修剪">🔪</button>
                <button class="tool-btn" data-tool="ripple" title="波纹删除">🌊</button>
                <button class="tool-btn" data-tool="marker" title="标记">🏷️</button>
                <button class="tool-btn" data-tool="split" title="分割">➗</button>
            </div>
            <div class="timecode-display">
                <span id="timecode">00:00:00:00</span>
            </div>
        </div>
        
        <div class="timeline-body">
            <div class="timeline-ruler" id="timelineRuler"></div>
            <div class="timeline-tracks" id="timelineTracks"></div>
        </div>
        
        <div class="timeline-footer">
            <div class="track-controls">
                <button class="btn btn-small" onclick="addTrack('video')">➕ 添加视频轨</button>
                <button class="btn btn-small" onclick="addTrack('audio')">➕ 添加音频轨</button>
                <button class="btn btn-small" onclick="addTrack('subtitle')">➕ 添加字幕轨</button>
            </div>
        </div>
    </footer>

    <div id="importModal" class="modal">
        <div class="modal-content">
            <h3>导入素材</h3>
            <div class="import-options">
                <div class="upload-area" id="uploadArea" ondragover="event.preventDefault()" ondrop="handleDrop(event)">
                    <input type="file" id="fileInput" multiple accept="video/*,audio/*,image/*,.srt,.ass,.vtt" style="display:none" onchange="handleFileSelect(event)">
                    <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">📁 选择本地文件</button>
                    <p style="margin-top:10px;color:#888;font-size:12px;">支持: MP4, MOV, MP3, WAV, JPG, PNG, GIF, SRT</p>
                </div>
                <button class="btn btn-secondary" onclick="importDemoFiles()" style="margin-top:10px">📋 导入示例素材</button>
                <button class="btn btn-secondary" onclick="closeModal()">取消</button>
            </div>
        </div>
    </div>

    <div id="exportModal" class="modal">
        <div class="modal-content">
            <h3>导出设置</h3>
            <div class="export-options">
                <div class="option-row">
                    <label>格式:</label>
                    <select id="exportFormat">
                        <option value="mp4">MP4</option>
                        <option value="mov">MOV</option>
                        <option value="gif">GIF</option>
                        <option value="webm">WebM</option>
                    </select>
                </div>
                <div class="option-row">
                    <label>分辨率:</label>
                    <select id="exportResolution">
                        <option value="720">720P</option>
                        <option value="1080">1080P</option>
                        <option value="2k">2K</option>
                        <option value="4k">4K</option>
                    </select>
                </div>
                <div class="option-row">
                    <label>帧率:</label>
                    <select id="exportFps">
                        <option value="24">24 fps</option>
                        <option value="25">25 fps</option>
                        <option value="30">30 fps</option>
                        <option value="60">60 fps</option>
                    </select>
                </div>
                <div class="option-row">
                    <label>质量:</label>
                    <input type="range" id="exportQuality" min="10" max="100" value="90">
                </div>
                <div class="progress-bar">
                    <div id="exportProgress"></div>
                </div>
                <button class="btn btn-primary" onclick="startExport()">开始导出</button>
                <button class="btn btn-secondary" onclick="closeExportModal()">取消</button>
            </div>
        </div>
    </div>

    <script src="app.js"></script>
</body>
</html>
"""
        
        with open(os.path.join(web_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _create_css_file(self, web_dir):
        css_content = """
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 100%; height: 100%; overflow: hidden; background: #1a1a2e; color: #fff; font-family: 'Segoe UI', sans-serif; }

.toolbar { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background: #16213e; border-bottom: 1px solid #0f3460; }
.toolbar-left, .toolbar-right { display: flex; gap: 10px; }
.toolbar-center { font-size: 16px; font-weight: 600; }

.btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s; background: #0f3460; color: #fff; }
.btn:hover { background: #1a5276; }
.btn-icon { display: flex; align-items: center; gap: 6px; }
.btn-small { padding: 6px 12px; font-size: 12px; }
.btn-primary { background: #00d4ff; color: #000; }
.btn-primary:hover { background: #00a8cc; }
.btn-secondary { background: #34495e; }

.main-container { display: flex; height: calc(100% - 80px); }

.left-panel { width: 280px; background: #0f3460; border-right: 1px solid #1a1a2e; display: flex; flex-direction: column; }
.panel-tabs { display: flex; flex-direction: column; border-bottom: 1px solid #1a1a2e; }
.tab-btn { padding: 12px 15px; background: transparent; border: none; color: #aaa; text-align: left; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.tab-btn:hover { background: rgba(255,255,255,0.1); }
.tab-btn.active { background: #1a5276; color: #fff; border-left: 3px solid #00d4ff; }

.panel-content { flex: 1; overflow-y: auto; display: none; padding: 10px; }
.panel-content.active { display: block; }

.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; gap: 10px; }
.search-box input { flex: 1; padding: 6px; border: 1px solid #34495e; border-radius: 4px; background: #1a1a2e; color: #fff; font-size: 12px; }

.filter-bar { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 15px; }
.filter-btn { padding: 6px 10px; background: #1a1a2e; border: none; border-radius: 4px; color: #aaa; font-size: 11px; cursor: pointer; transition: all 0.2s; }
.filter-btn.active { background: #00d4ff; color: #000; }

.media-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.media-item { aspect-ratio: 16/9; background: #1a1a2e; border-radius: 6px; overflow: hidden; cursor: pointer; position: relative; transition: transform 0.2s; }
.media-item:hover { transform: scale(1.02); }
.media-item img { width: 100%; height: 100%; object-fit: cover; }
.media-item .media-info { position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); padding: 5px; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; }
.media-item .media-meta { position: absolute; top: 5px; left: 5px; background: rgba(0,0,0,0.7); padding: 3px 6px; font-size: 9px; border-radius: 3px; }

.effects-list, .audio-tools, .text-tools { display: flex; flex-direction: column; gap: 15px; }
.effects-list h4, .audio-tools h4, .text-tools h4 { font-size: 12px; color: #00d4ff; margin-bottom: 8px; }
.effect-items { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; }
.effect-btn { padding: 8px; background: #1a1a2e; border: none; border-radius: 4px; color: #fff; font-size: 12px; cursor: pointer; transition: all 0.2s; }
.effect-btn:hover { background: #1a5276; }

.audio-list { display: flex; flex-direction: column; gap: 8px; }
.audio-item { padding: 10px; background: #1a1a2e; border-radius: 4px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.audio-item:hover { background: #1a5276; }

.text-input { width: 100%; padding: 8px; border: 1px solid #34495e; border-radius: 4px; background: #1a1a2e; color: #fff; margin-bottom: 10px; }
.text-controls { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; }
.text-controls select, .text-controls input[type="number"] { padding: 6px; border: 1px solid #34495e; border-radius: 4px; background: #1a1a2e; color: #fff; font-size: 12px; }
.text-controls input[type="color"] { width: 40px; height: 30px; border: none; cursor: pointer; }

.preview-area { flex: 1; display: flex; flex-direction: column; background: #000; }
.preview-container { flex: 1; position: relative; display: flex; flex-direction: column; }
#previewCanvas { flex: 1; width: 100%; height: 100%; object-fit: contain; background: #0a0a0a; }

.preview-overlay { position: absolute; bottom: 50px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; gap: 10px; background: rgba(0,0,0,0.8); padding: 15px 25px; border-radius: 15px; backdrop-filter: blur(10px); }
.playback-controls { display: flex; gap: 15px; align-items: center; }
.control-btn { width: 45px; height: 45px; border-radius: 50%; border: none; background: #0f3460; color: #fff; font-size: 18px; cursor: pointer; transition: all 0.2s; }
.control-btn:hover { background: #1a5276; }
.play-btn { width: 60px; height: 60px; background: #00d4ff; color: #000; font-size: 24px; }

.timeline-slider { width: 400px; }
.timeline-slider input { width: 100%; height: 6px; border-radius: 3px; background: #34495e; outline: none; cursor: pointer; }
.timeline-slider input::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%; background: #00d4ff; cursor: pointer; }

.timeline-header { height: 40px; background: #16213e; border-bottom: 1px solid #1a1a2e; position: relative; overflow: hidden; }
.timeline-ruler { position: absolute; top: 0; left: 0; height: 100%; display: flex; }
.ruler-mark { height: 100%; border-right: 1px solid #34495e; position: relative; }
.ruler-mark.major { border-right-color: #00d4ff; }
.ruler-label { position: absolute; bottom: 2px; left: 2px; font-size: 10px; color: #888; font-family: 'Courier New', monospace; }

.playhead { position: absolute; top: 0; width: 2px; height: 100%; background: #ff6b6b; z-index: 100; pointer-events: none; box-shadow: 0 0 10px rgba(255, 107, 107, 0.5); }
.playhead::after { content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 12px; height: 12px; background: #ff6b6b; border-radius: 50%; box-shadow: 0 0 10px rgba(255, 107, 107, 0.8); }

.time-display { font-family: 'Courier New', monospace; font-size: 14px; }

.preview-controls { position: absolute; top: 10px; right: 10px; display: flex; gap: 10px; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 10px; }
.preview-controls select { padding: 6px; border: 1px solid #34495e; border-radius: 4px; background: #1a1a2e; color: #fff; font-size: 12px; }

.right-panel { width: 320px; background: #0f3460; border-left: 1px solid #1a1a2e; display: flex; flex-direction: column; }

.info-section { padding: 15px; border-bottom: 1px solid #1a1a2e; }
.info-section h4 { margin-bottom: 15px; color: #00d4ff; }
.info-section p { margin-bottom: 8px; font-size: 13px; }

.color-controls, .transform-controls, .audio-controls, .subtitle-controls { padding: 15px; }
.control-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.control-row label { font-size: 12px; width: 60px; }
.control-row input[type="range"] { flex: 1; height: 4px; border-radius: 2px; background: #34495e; outline: none; cursor: pointer; }
.control-row input[type="number"] { width: 80px; padding: 4px; border: 1px solid #34495e; border-radius: 4px; background: #1a1a2e; color: #fff; font-size: 12px; }

.applied-effects { padding: 15px; }
.applied-effects h4 { margin-bottom: 15px; color: #00d4ff; }
.effect-item { display: flex; justify-content: space-between; padding: 8px; background: #1a1a2e; border-radius: 4px; margin-bottom: 8px; font-size: 12px; }
.effect-item button { background: transparent; border: none; color: #ff6b6b; cursor: pointer; }

.timeline-container { height: 220px; background: #16213e; border-top: 1px solid #0f3460; display: flex; flex-direction: column; }
.timeline-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 15px; border-bottom: 1px solid #0f3460; }

.zoom-controls { display: flex; align-items: center; gap: 8px; }
.timeline-tools { display: flex; gap: 5px; }
.tool-btn { width: 32px; height: 32px; border-radius: 4px; border: none; background: #0f3460; color: #fff; cursor: pointer; font-size: 14px; transition: all 0.2s; }
.tool-btn:hover { background: #1a5276; }
.tool-btn.active { background: #00d4ff; color: #000; }

.timecode-display { font-family: 'Courier New', monospace; font-size: 14px; }

.timeline-body { flex: 1; overflow-x: auto; overflow-y: auto; }
.timeline-ruler { height: 25px; background: #1a1a2e; border-bottom: 1px solid #0f3460; display: flex; position: sticky; top: 0; }
.ruler-mark { border-left: 1px solid #34495e; position: relative; }
.ruler-mark.major { border-left-color: #666; }
.ruler-label { position: absolute; top: 2px; font-size: 10px; color: #666; }

.timeline-tracks { display: flex; flex-direction: column; }
.track { height: 60px; border-bottom: 1px solid #0f3460; display: flex; position: relative; }
.track-header { width: 60px; background: #0f3460; display: flex; align-items: center; justify-content: center; border-right: 1px solid #1a1a2e; font-size: 11px; }
.track-content { flex: 1; background: #1a1a2e; display: flex; align-items: center; }

.clip { position: absolute; height: 40px; background: linear-gradient(135deg, #00d4ff, #0066ff); border-radius: 4px; cursor: pointer; display: flex; align-items: center; padding: 0 8px; font-size: 11px; overflow: hidden; white-space: nowrap; transition: background 0.2s; }
.clip:hover { background: linear-gradient(135deg, #00a8cc, #0055cc); }
.clip.selected { box-shadow: 0 0 0 2px #00d4ff; }

.subtitle-clip { background: linear-gradient(135deg, #ff6b6b, #ee5a5a); }
.audio-clip { background: linear-gradient(135deg, #4ecdc4, #44a08d); }

.timeline-footer { padding: 5px 15px; border-top: 1px solid #0f3460; }
.track-controls { display: flex; gap: 10px; }

.modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); justify-content: center; align-items: center; z-index: 1000; }
.modal-content { background: #16213e; padding: 30px; border-radius: 10px; min-width: 320px; }
.modal-content h3 { margin-bottom: 20px; color: #00d4ff; }
.option-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.option-row label { width: 80px; font-size: 13px; }
.option-row select { padding: 6px; border: 1px solid #34495e; border-radius: 4px; background: #1a1a2e; color: #fff; }
.progress-bar { height: 8px; background: #1a1a2e; border-radius: 4px; margin: 15px 0; overflow: hidden; }
.progress-bar div { height: 100%; background: linear-gradient(90deg, #00d4ff, #0066ff); transition: width 0.1s; }
"""
        
        with open(os.path.join(web_dir, "style.css"), "w", encoding="utf-8") as f:
            f.write(css_content)
    
    def _create_js_file(self, web_dir):
        js_content = """
let ws;
let project = { name: '未命名项目', fps: 24, resolution: '1920x1080', duration: 3600, tracks: [], clips: [], markers: [] };
let mediaLibrary = [];
let timelineState = { currentTime: 0, isPlaying: false, zoom: 1.0 };
let selectedClip = null;
let selectedTool = 'select';

function init() {
    connectWebSocket();
    loadDemoMedia();
    drawTimeline();
    drawRuler();
}

function connectWebSocket() {
    ws = new WebSocket('ws://localhost:15012');
    
    ws.onopen = function() {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = function(event) {
        let data = JSON.parse(event.data);
        handleMessage(data);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = function() {
        console.log('WebSocket closed, reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };
}

function sendCommand(command, data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ command, ...data }));
    }
}

function handleMessage(data) {
    switch(data.type) {
        case 'init':
            project = data.project;
            mediaLibrary = data.media_library;
            timelineState = data.timeline;
            updateUI();
            break;
        case 'media_imported':
            mediaLibrary.push(...data.items);
            updateMediaGrid();
            break;
        case 'media_list':
            mediaLibrary = data.items;
            updateMediaGrid();
            break;
        case 'clip_added':
            project.clips.push(data.clip);
            drawTimeline();
            break;
        case 'clip_deleted':
            project.clips = project.clips.filter(c => c.id !== data.clip_id);
            drawTimeline();
            break;
        case 'clip_updated':
            let clip = project.clips.find(c => c.id === data.clip_id);
            if (clip) Object.assign(clip, data.updates);
            drawTimeline();
            break;
        case 'track_added':
            project.tracks.push(data.track);
            drawTimeline();
            break;
        case 'time_updated':
            timelineState.currentTime = data.time;
            updateTimeDisplay();
            break;
        case 'playing':
            timelineState.isPlaying = data.state;
            updatePlayButton();
            break;
        case 'export_progress':
            updateExportProgress(data.progress);
            break;
        case 'export_complete':
            alert('导出完成!');
            closeExportModal();
            break;
    }
}

function loadDemoMedia() {
    mediaLibrary = [
        { id: 'm1', name: '风景视频.mp4', type: 'video', duration: 120, fps: 24, resolution: '1920x1080', codec: 'H.264', size: '50MB', thumbnail: 'https://picsum.photos/400/225?random=1' },
        { id: 'm2', name: '城市延时.mp4', type: 'video', duration: 180, fps: 30, resolution: '3840x2160', codec: 'ProRes', size: '200MB', thumbnail: 'https://picsum.photos/400/225?random=2' },
        { id: 'm3', name: '背景音乐.mp3', type: 'audio', duration: 300, codec: 'MP3', size: '5MB', thumbnail: '🎵' },
        { id: 'm4', name: '图片素材.jpg', type: 'image', duration: 30, resolution: '1920x1080', size: '2MB', thumbnail: 'https://picsum.photos/400/225?random=3' },
        { id: 'm5', name: '字幕文件.srt', type: 'subtitle', duration: 60, size: '1KB', thumbnail: '📝' },
        { id: 'm6', name: '动画GIF.gif', type: 'gif', duration: 5, fps: 15, size: '10MB', thumbnail: 'https://picsum.photos/400/225?random=4' }
    ];
    updateMediaGrid();
    
    project.tracks = [
        { id: 't1', type: 'video', name: 'V1', height: 60, locked: false, solo: false, muted: false },
        { id: 't2', type: 'video', name: 'V2', height: 60, locked: false, solo: false, muted: false },
        { id: 't3', type: 'audio', name: 'A1', height: 60, locked: false, solo: false, muted: false },
        { id: 't4', type: 'subtitle', name: 'T1', height: 40, locked: false, solo: false, muted: false },
        { id: 't5', type: 'pip', name: 'PIP1', height: 60, locked: false, solo: false, muted: false }
    ];
}

function updateUI() {
    document.getElementById('projectName').textContent = project.name;
    document.getElementById('infoName').textContent = project.name;
    document.getElementById('infoFps').textContent = project.fps + ' fps';
    document.getElementById('infoRes').textContent = project.resolution;
    document.getElementById('infoDuration').textContent = formatTime(project.duration);
    document.getElementById('infoTracks').textContent = project.tracks.length;
    document.getElementById('infoClips').textContent = project.clips.length;
}

function showPanel(panel) {
    document.querySelectorAll('.left-panel .panel-content').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.left-panel .tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(panel + 'Panel').classList.add('active');
    event.target.classList.add('active');
}

function showRightPanel(panel) {
    document.querySelectorAll('.right-panel .panel-content').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.right-panel .tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(panel === 'effects' ? 'rightEffectsPanel' : panel === 'audio' ? 'rightAudioPanel' : panel + 'Panel').classList.add('active');
    event.target.classList.add('active');
}

function importMedia() {
    document.getElementById('importModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('importModal').style.display = 'none';
}

function importDemoFiles() {
    sendCommand('import_media', {
        files: [
            { name: '导入视频.mp4', type: 'video', duration: 150, fps: 24, resolution: '1920x1080', codec: 'H.264', size: '80MB' },
            { name: '导入音频.mp3', type: 'audio', duration: 200, codec: 'MP3', size: '8MB' },
            { name: '导入图片.png', type: 'image', duration: 20, resolution: '1920x1080', size: '3MB' },
            { name: '动画GIF.gif', type: 'gif', duration: 5, fps: 15, size: '15MB' },
            { name: '字幕文件.srt', type: 'subtitle', duration: 60, size: '2KB' }
        ]
    });
    closeModal();
}

function handleFileSelect(event) {
    processFiles(event.target.files);
}

function handleDrop(event) {
    event.preventDefault();
    processFiles(event.dataTransfer.files);
}

function processFiles(files) {
    let importFiles = [];
    
    for (let i = 0; i < files.length; i++) {
        let file = files[i];
        let fileInfo = {
            name: file.name,
            type: getFileType(file.name),
            size: formatFileSize(file.size),
            duration: getDefaultDuration(file.name),
            fps: 24,
            resolution: '1920x1080',
            codec: 'H.264'
        };
        importFiles.push(fileInfo);
    }
    
    sendCommand('import_media', { files: importFiles });
    closeModal();
}

function getFileType(filename) {
    let ext = filename.split('.').pop().toLowerCase();
    if (['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv'].includes(ext)) return 'video';
    if (['mp3', 'wav', 'ogg', 'flac', 'aac'].includes(ext)) return 'audio';
    if (['jpg', 'jpeg', 'png', 'bmp', 'webp'].includes(ext)) return 'image';
    if (['gif'].includes(ext)) return 'gif';
    if (['srt', 'ass', 'vtt'].includes(ext)) return 'subtitle';
    return 'video';
}

function getDefaultDuration(filename) {
    let ext = filename.split('.').pop().toLowerCase();
    if (['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv'].includes(ext)) return 60;
    if (['mp3', 'wav', 'ogg', 'flac', 'aac'].includes(ext)) return 120;
    if (['jpg', 'jpeg', 'png', 'bmp', 'webp'].includes(ext)) return 10;
    if (['gif'].includes(ext)) return 5;
    if (['srt', 'ass', 'vtt'].includes(ext)) return 60;
    return 30;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function searchMedia() {
    let query = document.getElementById('mediaSearch').value.toLowerCase();
    let items = document.querySelectorAll('.media-item');
    items.forEach(item => {
        let name = item.querySelector('.media-info').textContent.toLowerCase();
        item.style.display = name.includes(query) ? 'block' : 'none';
    });
}

function updateMediaGrid() {
    let grid = document.getElementById('mediaGrid');
    grid.innerHTML = '';
    
    mediaLibrary.forEach(media => {
        let item = document.createElement('div');
        item.className = 'media-item';
        item.onclick = () => addMediaToTimeline(media);
        
        if (media.thumbnail && media.thumbnail.startsWith('http')) {
            item.innerHTML = `<img src="${media.thumbnail}"><div class="media-meta">${media.type === 'video' ? '🎬' : media.type === 'audio' ? '🎵' : media.type === 'image' ? '🖼️' : '📑'}</div><div class="media-info">${media.name}</div>`;
        } else {
            item.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;font-size:32px;">${media.thumbnail || '📄'}</div><div class="media-info">${media.name}</div>`;
        }
        grid.appendChild(item);
    });
}

function addMediaToTimeline(media) {
    let trackIndex = media.type === 'audio' ? 2 : media.type === 'subtitle' ? 3 : 0;
    
    sendCommand('add_clip', {
        media_id: media.id,
        track: trackIndex,
        start_time: project.clips.length * 100,
        duration: media.duration * 10,
        name: media.name,
        type: media.type
    });
}

function drawTimeline() {
    let tracks = document.getElementById('timelineTracks');
    tracks.innerHTML = '';
    
    if (project.tracks.length === 0) {
        loadDemoMedia();
    }
    
    project.tracks.forEach((track, index) => {
        let trackDiv = document.createElement('div');
        trackDiv.className = 'track';
        trackDiv.innerHTML = `<div class="track-header">${track.name}</div><div class="track-content"></div>`;
        
        let clips = project.clips.filter(c => c.track === index);
        clips.forEach(clip => {
            let clipDiv = document.createElement('div');
            clipDiv.className = `clip ${clip.type === 'subtitle' ? 'subtitle-clip' : clip.type === 'audio' ? 'audio-clip' : ''} ${selectedClip === clip.id ? 'selected' : ''}`;
            clipDiv.style.left = clip.start_time * timelineState.zoom + 'px';
            clipDiv.style.width = clip.duration * timelineState.zoom + 'px';
            clipDiv.textContent = clip.name;
            clipDiv.onclick = () => selectClip(clip);
            clipDiv.oncontextmenu = (e) => { showClipMenu(e, clip); return false; };
            trackDiv.querySelector('.track-content').appendChild(clipDiv);
        });
        
        tracks.appendChild(trackDiv);
    });
}

function drawRuler() {
    let ruler = document.getElementById('timelineRuler');
    ruler.innerHTML = '';
    
    let totalWidth = project.duration * timelineState.zoom;
    ruler.style.width = totalWidth + 'px';
    
    for (let i = 0; i <= project.duration; i += 50) {
        let mark = document.createElement('div');
        mark.className = 'ruler-mark' + (i % 200 === 0 ? ' major' : '');
        mark.style.width = 50 * timelineState.zoom + 'px';
        
        if (i % 200 === 0) {
            let label = document.createElement('div');
            label.className = 'ruler-label';
            label.textContent = formatTimecode(i);
            mark.appendChild(label);
        }
        ruler.appendChild(mark);
    }
}

function selectClip(clip) {
    selectedClip = clip.id;
    drawTimeline();
    updateClipInfo(clip);
}

function updateClipInfo(clip) {
    let info = document.getElementById('clipInfo');
    info.innerHTML = `
        <p><strong>名称:</strong> ${clip.name}</p>
        <p><strong>轨道:</strong> ${project.tracks[clip.track]?.name || '未知'}</p>
        <p><strong>开始:</strong> ${formatTimecode(clip.start_time)}</p>
        <p><strong>时长:</strong> ${formatTimecode(clip.duration)}</p>
        <button class="btn btn-small" onclick="deleteClip('${clip.id}')">🗑️ 删除</button>
    `;
}

function deleteClip(clipId) {
    sendCommand('delete_clip', { clip_id: clipId });
    selectedClip = null;
}

function addTrack(type) {
    sendCommand('add_track', { type });
}

function zoomIn() {
    timelineState.zoom = Math.min(timelineState.zoom + 0.2, 5);
    updateZoomDisplay();
    drawTimeline();
    drawRuler();
}

function zoomOut() {
    timelineState.zoom = Math.max(timelineState.zoom - 0.2, 0.1);
    updateZoomDisplay();
    drawTimeline();
    drawRuler();
}

function zoomFit() {
    let container = document.querySelector('.timeline-body');
    timelineState.zoom = container.clientWidth / project.duration;
    updateZoomDisplay();
    drawTimeline();
    drawRuler();
}

function updateZoomDisplay() {
    document.getElementById('zoomLevel').textContent = Math.round(timelineState.zoom * 100) + '%';
}

function formatTime(frames) {
    let seconds = Math.floor(frames / 100);
    let h = Math.floor(seconds / 3600);
    let m = Math.floor((seconds % 3600) / 60);
    let s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function formatTimecode(frames) {
    let fps = project.fps;
    let totalSeconds = Math.floor(frames / 100);
    let f = Math.floor((frames % 100) * fps / 100);
    let h = Math.floor(totalSeconds / 3600);
    let m = Math.floor((totalSeconds % 3600) / 60);
    let s = totalSeconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}:${f.toString().padStart(2, '0')}`;
}

function updateTimeDisplay() {
    document.getElementById('currentTime').textContent = formatTime(timelineState.currentTime);
    document.getElementById('timecode').textContent = formatTimecode(timelineState.currentTime);
    document.getElementById('timelineSlider').value = timelineState.currentTime;
}

function togglePlay() {
    if (timelineState.isPlaying) {
        sendCommand('pause');
        stopPlaybackLoop();
    } else {
        sendCommand('play');
        startPlaybackLoop();
    }
}

function updatePlayButton() {
    let btn = document.getElementById('playBtn');
    btn.textContent = timelineState.isPlaying ? '⏸' : '▶';
}

let playbackInterval = null;

function startPlaybackLoop() {
    if (playbackInterval) clearInterval(playbackInterval);
    
    let speed = parseFloat(document.getElementById('speedSelect').value);
    let interval = 50 / speed;  // 基础50ms，根据速度调整
    
    playbackInterval = setInterval(() => {
        if (!timelineState.isPlaying) {
            stopPlaybackLoop();
            return;
        }
        
        timelineState.currentTime += 5 * speed;
        
        if (timelineState.currentTime >= project.duration) {
            timelineState.currentTime = project.duration;
            timelineState.isPlaying = false;
            updatePlayButton();
            stopPlaybackLoop();
        }
        
        updateTimeDisplay();
        updatePlayhead();
        updatePreview();
    }, interval);
}

function stopPlaybackLoop() {
    if (playbackInterval) {
        clearInterval(playbackInterval);
        playbackInterval = null;
    }
}

function updatePlayhead() {
    let ruler = document.getElementById('timelineRuler');
    let playhead = document.getElementById('playhead');
    if (!playhead) {
        playhead = document.createElement('div');
        playhead.id = 'playhead';
        playhead.className = 'playhead';
        ruler.parentNode.appendChild(playhead);
    }
    
    playhead.style.left = timelineState.currentTime * timelineState.zoom + 'px';
}

function updatePreview() {
    let canvas = document.getElementById('previewCanvas');
    let ctx = canvas.getContext('2d');
    
    // 清空画布
    ctx.fillStyle = '#2a2a4a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // 绘制时间码
    ctx.fillStyle = '#fff';
    ctx.font = '24px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(formatTimecode(timelineState.currentTime), canvas.width / 2, canvas.height / 2);
    
    // 绘制当前时间的片段信息
    let currentClips = project.clips.filter(c => 
        timelineState.currentTime >= c.start_time && 
        timelineState.currentTime < c.start_time + c.duration
    );
    
    if (currentClips.length > 0) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.font = '14px Arial';
        currentClips.forEach((clip, i) => {
            ctx.fillText(clip.name, canvas.width / 2, canvas.height / 2 + 30 + i * 20);
        });
    }
}

function stepBackward() {
    timelineState.currentTime = Math.max(0, timelineState.currentTime - 10);
    sendCommand('set_time', { time: timelineState.currentTime });
}

function stepForward() {
    timelineState.currentTime = Math.min(project.duration, timelineState.currentTime + 10);
    sendCommand('set_time', { time: timelineState.currentTime });
}

function changeSpeed() {
    let speed = document.getElementById('speedSelect').value;
    console.log('Speed changed to:', speed + 'x');
    
    // 如果正在播放，重新启动播放循环以应用新速度
    if (timelineState.isPlaying) {
        stopPlaybackLoop();
        startPlaybackLoop();
    }
}

function seekTo(time) {
    timelineState.currentTime = parseInt(time);
    updateTimeDisplay();
    updatePlayhead();
    updatePreview();
    sendCommand('set_time', { time: timelineState.currentTime });
}

function toggleFullscreen() {
    if (document.fullscreenElement) {
        document.exitFullscreen();
    } else {
        document.documentElement.requestFullscreen();
    }
}

function toggleCrop() {
    console.log('Crop mode toggled');
}

function applyColorCorrection() {
    if (!selectedClip) { alert('请先选择片段'); return; }
    
    let correction = {
        brightness: document.getElementById('brightness').value,
        contrast: document.getElementById('contrast').value,
        saturation: document.getElementById('saturation').value,
        temperature: document.getElementById('temperature').value,
        hue: document.getElementById('hue').value,
        sharpen: document.getElementById('sharpen').value
    };
    
    sendCommand('color_correction', { clip_id: selectedClip, correction });
}

function applyTransform() {
    if (!selectedClip) { alert('请先选择片段'); return; }
    
    let updates = {
        position: { x: parseInt(document.getElementById('posX').value), y: parseInt(document.getElementById('posY').value) },
        scale: document.getElementById('scale').value / 100,
        rotation: parseInt(document.getElementById('rotation').value),
        opacity: document.getElementById('opacity').value / 100
    };
    
    sendCommand('edit_clip', { clip_id: selectedClip, updates });
}

function applyAudioSettings() {
    if (!selectedClip) { alert('请先选择片段'); return; }
    
    sendCommand('audio_adjust', {
        clip_id: selectedClip,
        level: document.getElementById('audioLevel').value / 100,
        pan: document.getElementById('audioPan').value
    });
}

function addSubtitle() {
    let text = document.getElementById('subtitleText').value;
    let start = parseInt(document.getElementById('subtitleStart').value);
    let duration = parseInt(document.getElementById('subtitleDuration').value);
    
    sendCommand('add_subtitle', {
        text,
        start_time: start,
        end_time: start + duration,
        style: { font: 'Arial', size: 24, color: '#ffffff' }
    });
}

function generateSubtitle() {
    alert('🎙️ 自动字幕生成功能即将推出!');
}

function addText() {
    let text = document.getElementById('textInput').value;
    let font = document.getElementById('fontSelect').value;
    let size = document.getElementById('fontSize').value;
    let color = document.getElementById('fontColor').value;
    
    sendCommand('add_clip', {
        media_id: 'text_' + Date.now(),
        track: 1,
        start_time: project.clips.length * 100,
        duration: 200,
        name: '文字: ' + text,
        type: 'text',
        text_data: { text, font, size, color }
    });
}

function addAudioClip(type) {
    sendCommand('add_clip', {
        media_id: 'audio_' + type,
        track: 2,
        start_time: project.clips.length * 100,
        duration: 300,
        name: type,
        type: 'audio'
    });
}

document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.onclick = function() {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        let type = this.dataset.type;
        sendCommand('get_media', { type });
    };
});

document.querySelectorAll('.effect-btn[data-effect]').forEach(btn => {
    btn.onclick = function() {
        if (!selectedClip) { alert('请先选择片段'); return; }
        sendCommand('add_effect', { clip_id: selectedClip, effect: { type: this.dataset.effect } });
        alert('特效已应用: ' + this.textContent);
    };
});

document.querySelectorAll('.effect-btn[data-transition]').forEach(btn => {
    btn.onclick = function() {
        sendCommand('add_transition', { type: this.dataset.transition, start_time: timelineState.currentTime, duration: 30 });
        alert('转场已添加: ' + this.textContent);
    };
});

document.querySelectorAll('.effect-btn[data-audio]').forEach(btn => {
    btn.onclick = function() {
        if (!selectedClip) { alert('请先选择片段'); return; }
        sendCommand('add_audio_effect', { clip_id: selectedClip, type: this.dataset.audio });
        alert('音频效果已应用: ' + this.textContent);
    };
});

document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.onclick = function() {
        document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        selectedTool = this.dataset.tool;
    };
});

document.getElementById('timelineSlider').addEventListener('input', function() {
    timelineState.currentTime = parseInt(this.value);
    sendCommand('set_time', { time: timelineState.currentTime });
});

function exportProject() {
    document.getElementById('exportModal').style.display = 'flex';
}

function closeExportModal() {
    document.getElementById('exportModal').style.display = 'none';
    document.getElementById('exportProgress').style.width = '0%';
}

function startExport() {
    let format = document.getElementById('exportFormat').value;
    let resolution = document.getElementById('exportResolution').value;
    let fps = document.getElementById('exportFps').value;
    let quality = document.getElementById('exportQuality').value;
    
    sendCommand('export', { format, resolution, fps, quality });
}

function updateExportProgress(progress) {
    document.getElementById('exportProgress').style.width = progress + '%';
}

function newProject() {
    project = { name: '未命名项目', fps: 24, resolution: '1920x1080', duration: 3600, tracks: [], clips: [], markers: [] };
    timelineState.currentTime = 0;
    selectedClip = null;
    loadDemoMedia();
    updateUI();
    drawTimeline();
    drawRuler();
    updateTimeDisplay();
}

function saveProject() {
    let name = prompt('输入项目名称:', project.name);
    if (name) {
        sendCommand('save_project', { name });
    }
}

function openProject() {
    alert('打开项目功能即将推出!');
}

function showSettings() {
    alert('设置功能即将推出!');
}

document.addEventListener('DOMContentLoaded', init);
"""
        
        with open(os.path.join(web_dir, "app.js"), "w", encoding="utf-8") as f:
            f.write(js_content)


if __name__ == "__main__":
    editor = VideoEditor()
    editor.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        editor.stop()