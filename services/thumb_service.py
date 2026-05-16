"""
时光印记 - 缩略图服务
负责生成和管理缩略图
"""
import os
import hashlib
import json
from PIL import Image
from config import THUMB_DIR, SUPPORTED_IMAGE, get_chapter_covers_file
from config import config as app_config


def _load_covers():
    """加载章节封面配置"""
    covers_file = get_chapter_covers_file(app_config.root_dir)
    if os.path.exists(covers_file):
        try:
            with open(covers_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_covers(covers):
    """保存章节封面配置"""
    covers_file = get_chapter_covers_file(app_config.root_dir)
    with open(covers_file, 'w', encoding='utf-8') as f:
        json.dump(covers, f, ensure_ascii=False)


def set_chapter_cover(chapter_name, image_path):
    """设置章节封面图片"""
    covers = _load_covers()
    covers[chapter_name] = image_path
    _save_covers(covers)
    return True, None


def get_chapter_cover(chapter_name):
    """获取章节自定义封面，返回图片路径或None（未设置）"""
    covers = _load_covers()
    return covers.get(chapter_name)


def remove_chapter_cover(chapter_name):
    """移除章节自定义封面（恢复为默认第一张）"""
    covers = _load_covers()
    if chapter_name in covers:
        del covers[chapter_name]
        _save_covers(covers)
    return True, None


def generate_thumb(image_path, size=(400, 300), quality=75):
    """
    生成图片缩略图
    
    Args:
        image_path: 原图路径
        size: 缩略图最大尺寸 (width, height)
        quality: JPEG 质量 (1-100)
    
    Returns:
        缩略图 URL 路径，失败返回 None
    """
    if not os.path.exists(image_path):
        return None
    
    # 使用稳定的 MD5 哈希方法
    img_path_for_hash = image_path.replace('\\', '/')
    thumb_name = hashlib.md5(img_path_for_hash.encode('utf-8')).hexdigest() + '.jpg'
    thumb_path = os.path.join(THUMB_DIR, thumb_name)
    
    if os.path.exists(thumb_path):
        return f'/thumb/{thumb_name}'
    
    try:
        with Image.open(image_path) as img:
            if img.mode in ('P', 'PA', 'RGBA', 'LA'):
                img = img.convert('RGB')
            img.thumbnail(size, Image.BICUBIC)
            img.save(thumb_path, 'JPEG', quality=quality, optimize=True)
        return f'/thumb/{thumb_name}'
    except Exception:
        return None


def get_cover_thumb(chapter_name, folder_path, images=None):
    """
    获取章节封面缩略图
    
    Args:
        chapter_name: 章节名称（用于查找自定义封面）
        folder_path: 章节文件夹路径
        images: 图片文件列表（可选）
    
    Returns:
        缩略图 URL，失败返回 None
    """
    # 优先使用自定义封面
    custom_cover = get_chapter_cover(chapter_name)
    if custom_cover and os.path.exists(custom_cover):
        return generate_thumb(custom_cover)
    
    # 自定义封面不存在（可能被删除/移动），清除配置
    if custom_cover:
        remove_chapter_cover(chapter_name)
    
    # 加载自定义排序，始终优先使用自定义排序的第一张图片
    from services.file_service import load_chapter_file_order
    custom_order = load_chapter_file_order(chapter_name)
    
    if custom_order and len(custom_order) > 1:
        # 有自定义排序，取排序后的第一个图片
        for name in custom_order:
            fpath = os.path.join(folder_path, name)
            if os.path.isfile(fpath) and os.path.splitext(name)[1].lower() in SUPPORTED_IMAGE:
                return generate_thumb(fpath)
    
    # 无自定义排序或排序列表中没有图片，使用传入的 images 或文件夹中第一个图片
    if images is None:
        if not os.path.exists(folder_path):
            return None
        files = os.listdir(folder_path)
        images = [f for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_IMAGE]
    
    if not images:
        return None
    
    img_path = os.path.join(folder_path, images[0])
    return generate_thumb(img_path)
