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
from routes import music_api_bp


@music_api_bp.route('/list', methods=['GET'])
def api_music_list():
    """获取音乐列表"""
    musics = get_music_list()
    return jsonify({'ok': True, 'musics': musics, 'music_dir': musics and os.path.dirname(musics[0].get('name', '')) if musics else ''})


@music_api_bp.route('/serve')
def api_serve_music():
    """提供音乐文件下载/播放"""
    raw_filename = request.args.get('f', '')
    resp, error = serve_music_file(raw_filename)
    if error:
        return error, 404
    return resp


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
    
    if music == '__none__':
        config['chapter_music'][chapter] = '__none__'
    elif music:
        config['chapter_music'][chapter] = music
    else:
        config['chapter_music'].pop(chapter, None)
    
    save_chapter_music_csv(config.get('chapter_music', {}))
    return jsonify({'ok': True})


@music_api_bp.route('/settings', methods=['GET', 'POST'])
def api_music_settings():
    """获取/修改音乐播放设置"""
    user_id = get_current_user_id()
    
    if request.method == 'GET':
        settings = get_music_settings(user_id)
        return jsonify({'ok': True, 'settings': settings})
    
    settings = request.json.get('settings', {})
    save_music_settings(user_id, settings)
    return jsonify({'ok': True})
