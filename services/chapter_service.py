"""
时光印记 - 章节服务
负责章节扫描、缓存、CRUD
"""
import os
import re
from config import (
    SUPPORTED_IMAGE, SUPPORTED_VIDEO, CACHE_DURATION,
    config as app_config,
)
from services.thumb_service import get_cover_thumb


def get_chapters():
    """扫描根目录获取所有章节（带缓存）"""
    current_time = __import__('time').time()
    
    if app_config.chapter_cache and (current_time - app_config.cache_timestamp) < CACHE_DURATION:
        return app_config.chapter_cache
    
    chapters = []
    if not os.path.exists(app_config.root_dir):
        return chapters
    
    for name in sorted(os.listdir(app_config.root_dir)):
        path = os.path.join(app_config.root_dir, name)
        if os.path.isdir(path):
            files = os.listdir(path)
            images = [f for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_IMAGE]
            videos = [f for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_VIDEO]
            md_file = next((f for f in files if f.lower().endswith('.md')), None)
            chapters.append({
                'name': name,
                'year': name[:4] if len(name) >= 4 and name[:4].isdigit() else '',
                'path': path,
                'image_count': len(images),
                'video_count': len(videos),
                'has_article': md_file is not None,
                'cover': get_cover_thumb(path, images),
            })
    
    app_config.chapter_cache = chapters
    app_config.cache_timestamp = current_time
    return chapters


def invalidate_chapter_cache():
    """清除章节缓存"""
    app_config.chapter_cache = {}
    app_config.cache_timestamp = 0


def get_chapter_folder(chapter_name):
    """获取章节文件夹路径"""
    return os.path.join(app_config.root_dir, chapter_name)


def chapter_exists(chapter_name):
    """检查章节是否存在"""
    return os.path.exists(get_chapter_folder(chapter_name))


def create_chapter(name):
    """创建新章节文件夹"""
    name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    if not name:
        return False, '名称无效'
    path = get_chapter_folder(name)
    if os.path.exists(path):
        return False, '章节已存在'
    os.makedirs(path, exist_ok=True)
    invalidate_chapter_cache()
    return True, name


def delete_chapter(chapter_name):
    """删除章节文件夹"""
    import shutil
    path = get_chapter_folder(chapter_name)
    if not os.path.exists(path):
        return False, '章节不存在'
    shutil.rmtree(path)
    invalidate_chapter_cache()
    return True, None


def rename_chapter(old_name, new_name):
    """重命名章节文件夹"""
    old_path = get_chapter_folder(old_name)
    if not os.path.exists(old_path):
        return False, '章节不存在'
    
    new_name = re.sub(r'[<>:"/\\|?*]', '', new_name).strip()
    if not new_name:
        return False, '名称无效'
    
    new_path = get_chapter_folder(new_name)
    if os.path.exists(new_path):
        return False, '名称已存在'
    
    os.rename(old_path, new_path)
    invalidate_chapter_cache()
    return True, new_name
