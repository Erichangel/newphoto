"""
时光印记 - 设置 API 路由
"""
import os
from flask import request, jsonify
from config import config as app_config
from routes import settings_api_bp


@settings_api_bp.route('/settings', methods=['GET', 'POST'])
def api_settings():
    """获取/修改根目录和音乐目录设置"""
    from services.chapter_service import invalidate_chapter_cache
    
    if request.method == 'GET':
        return jsonify({'root_dir': app_config.root_dir, 'music_dir': app_config.music_dir})
    
    data = request.json
    errors = []
    new_root = data.get('root_dir', '').strip()
    new_music = data.get('music_dir', '').strip()
    
    if new_root:
        if os.path.isdir(new_root):
            app_config.root_dir = new_root
        else:
            errors.append('照片目录不存在')
    if new_music:
        if os.path.isdir(new_music):
            app_config.music_dir = new_music
        else:
            errors.append('音乐目录不存在')
    
    if errors:
        return jsonify({'error': ', '.join(errors)}), 400
    
    app_config.save_to_file()
    invalidate_chapter_cache()
    return jsonify({'ok': True, 'root_dir': app_config.root_dir, 'music_dir': app_config.music_dir})


@settings_api_bp.route('/browsefolders', methods=['GET'])
def api_browse_folders():
    """浏览指定路径下的子文件夹"""
    req_path = request.args.get('path', '').strip()
    if not req_path:
        parent = os.path.dirname(app_config.root_dir)
        if os.path.isdir(parent):
            req_path = parent
        else:
            req_path = os.path.splitdrive(app_config.root_dir)[0] + '\\'
    
    if not os.path.isdir(req_path):
        return jsonify({'error': '路径不存在', 'folders': []})
    
    try:
        entries = []
        for name in sorted(os.listdir(req_path)):
            full = os.path.join(req_path, name)
            if os.path.isdir(full) and not name.startswith('.'):
                entries.append({'name': name, 'full_path': full})
        return jsonify({'ok': True, 'current_path': req_path, 'folders': entries})
    except Exception as e:
        return jsonify({'error': str(e), 'folders': []})
