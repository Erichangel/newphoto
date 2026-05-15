"""
时光印记 - 音乐 API 路由
"""
import os
from flask import request, jsonify
from services.music_service import (
    load_music_config, save_chapter_music_csv, get_music_list,
    serve_music_file, get_music_settings, save_music_settings,
)
from services.user_service import get_current_user_id
from config import config as app_config
from routes import music_api_bp


@music_api_bp.route('/music/list', methods=['GET'])
def api_music_list():
    """获取音乐列表"""
    musics = get_music_list()
    return jsonify({'ok': True, 'musics': musics, 'music_dir': musics and os.path.dirname(musics[0].get('name', '')) if musics else ''})


@music_api_bp.route('/music/serve')
def api_serve_music():
    """提供音乐文件下载/播放"""
    raw_filename = request.args.get('f', '')
    resp, error = serve_music_file(raw_filename)
    if error:
        return error, 404
    return resp


@music_api_bp.route('/music/upload', methods=['POST'])
def api_upload_music():
    """上传音乐文件"""
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    uploaded = request.files['file']
    if not uploaded.filename:
        return jsonify({'error': '文件名不能为空'}), 400
    
    # 安全检查：只允许音频文件
    ext = os.path.splitext(uploaded.filename)[1].lower()
    from config import SUPPORTED_AUDIO
    if ext not in SUPPORTED_AUDIO:
        return jsonify({'error': '只支持音频文件 (mp3, wav, ogg, flac, m4a, aac)'}), 400
    
    # 确保音乐目录存在
    os.makedirs(app_config.music_dir, exist_ok=True)
    
    # 保存文件
    dest = os.path.join(app_config.music_dir, uploaded.filename)
    
    # 处理文件名冲突
    if os.path.exists(dest):
        name, ex = os.path.splitext(uploaded.filename)
        counter = 1
        while os.path.exists(dest):
            dest = os.path.join(app_config.music_dir, f"{name}_{counter}{ex}")
            counter += 1
    
    uploaded.save(dest)
    return jsonify({'ok': True, 'name': os.path.basename(dest)})


@music_api_bp.route('/music/delete', methods=['POST'])
def api_delete_music():
    """删除音乐文件"""
    filename = request.json.get('name', '')
    if not filename:
        return jsonify({'error': '文件名不能为空'}), 400
    
    # 安全检查：只允许删除音乐目录中的文件
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(app_config.music_dir, safe_filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': '文件不存在'}), 404
    
    if not filepath.startswith(os.path.realpath(app_config.music_dir)):
        return jsonify({'error': '禁止访问'}), 403
    
    os.remove(filepath)
    return jsonify({'ok': True})


@music_api_bp.route('/chapter/music', methods=['GET', 'POST'])
def api_chapter_music():
    """获取/设置章节关联的音乐"""
    config = load_music_config()
    
    if request.method == 'GET':
        chapter = request.args.get('chapter', '')
        music_name = config['chapter_music'].get(chapter, '')
        return jsonify({'ok': True, 'music': music_name})
    
    chapter = request.json.get('chapter', '')
    music = request.json.get('music', '')
    if not chapter:
        return jsonify({'error': '章节名不能为空'}), 400
    
    if music == '__none__' or music == '' or music is None:
        # 清除指定音乐，恢复随机播放
        config['chapter_music'].pop(chapter, None)
    else:
        config['chapter_music'][chapter] = music
    
    save_chapter_music_csv(config.get('chapter_music', {}))
    return jsonify({'ok': True})


@music_api_bp.route('/music/settings', methods=['GET', 'POST'])
def api_music_settings():
    """获取/修改音乐播放设置"""
    user_id = get_current_user_id()
    
    if request.method == 'GET':
        settings = get_music_settings(user_id)
        return jsonify({'ok': True, 'settings': settings})
    
    settings = request.json.get('settings', {})
    save_music_settings(user_id, settings)
    return jsonify({'ok': True})
