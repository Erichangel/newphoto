"""
时光印记 - 音乐服务
负责音乐配置、章节-音乐关联、文件服务
"""
import os
import json
import csv
from urllib.parse import unquote
from flask import make_response
from config import (
    SUPPORTED_AUDIO,
    get_chapter_music_file,
    get_music_config_file,
    config as app_config,
)


def _get_chapter_music_path():
    """获取当前根目录的章节音乐CSV路径"""
    return get_chapter_music_file(app_config.root_dir)


def _get_music_config_path():
    """获取当前根目录的音乐播放器配置路径"""
    return get_music_config_file(app_config.root_dir)


def load_chapter_music_csv():
    """从 CSV 文件加载章节音乐映射"""
    chapter_music = {}
    csv_path = _get_chapter_music_path()
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    chapter = row.get('chapter', '').strip()
                    music = row.get('music', '').strip()
                    if chapter:
                        chapter_music[chapter] = music
        except Exception as e:
            print(f'加载 CSV 文件失败: {e}')
    return chapter_music


def save_chapter_music_csv(chapter_music):
    """保存章节音乐映射到 CSV 文件"""
    try:
        csv_path = _get_chapter_music_path()
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['chapter', 'music'])
            writer.writeheader()
            for chapter, music in chapter_music.items():
                if music:
                    writer.writerow({'chapter': chapter, 'music': music})
    except Exception as e:
        print(f'保存 CSV 文件失败: {e}')


def load_music_config():
    """加载音乐配置（章节-音乐关联 + 用户设置）"""
    chapter_music = load_chapter_music_csv()
    
    return {'chapter_music': chapter_music, 'settings': {'auto_switch': True}}


def get_music_list():
    """获取音乐文件夹中的所有音频文件"""
    musics = []
    if not os.path.exists(app_config.music_dir):
        return musics
    
    for name in sorted(os.listdir(app_config.music_dir)):
        ext = os.path.splitext(name)[1].lower()
        if ext in SUPPORTED_AUDIO:
            fpath = os.path.join(app_config.music_dir, name)
            if not os.path.isfile(fpath):
                continue
            try:
                size = os.path.getsize(fpath)
                musics.append({
                    'name': name,
                    'size': size,
                    'size_display': f'{size / 1024 / 1024:.1f}MB' if size > 1024 * 1024 else f'{size / 1024:.0f}KB'
                })
            except (OSError, IOError):
                continue
    return musics


def serve_music_file(raw_filename):
    """提供音乐文件流"""
    safe_filename = os.path.basename(raw_filename)
    filepath = os.path.join(app_config.music_dir, safe_filename)
    
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        safe_filename = unquote(raw_filename)
        filepath = os.path.join(app_config.music_dir, safe_filename)
    
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        return None, '文件不存在: ' + repr(safe_filename)
    
    ext = os.path.splitext(safe_filename)[1].lower()
    mime_types = {
        '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4', '.flac': 'audio/flac', '.aac': 'audio/aac'
    }
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    resp = make_response(data)
    resp.headers['Content-Type'] = mime_types.get(ext, 'application/octet-stream')
    resp.headers['Content-Length'] = len(data)
    resp.headers['Accept-Ranges'] = 'bytes'
    return resp, None


def get_music_settings(user_id):
    """获取用户的音乐设置"""
    if user_id:
        settings_file = os.path.join(os.path.dirname(app_config.root_dir), f'user_{user_id}_music_settings.json')
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    return {'auto_switch': True, 'auto_play': True}


def save_music_settings(user_id, settings):
    """保存用户的音乐设置"""
    if user_id:
        settings_file = os.path.join(os.path.dirname(app_config.root_dir), f'user_{user_id}_music_settings.json')
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        else:
            existing = {'auto_switch': True, 'auto_play': True}
        existing.update(settings)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    else:
        config = load_music_config()
        config.setdefault('settings', {}).update(settings)
        save_chapter_music_csv(config.get('chapter_music', {}))
