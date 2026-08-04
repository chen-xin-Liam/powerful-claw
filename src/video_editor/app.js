
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
