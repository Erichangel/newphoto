"""
时光印记 - 缩略图服务
负责生成和管理缩略图
"""
import os
import hashlib
from PIL import Image
from config import THUMB_DIR, SUPPORTED_IMAGE


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


def get_cover_thumb(folder_path, images=None):
    """
    获取章节封面缩略图
    
    Args:
        folder_path: 章节文件夹路径
        images: 图片文件列表（可选）
    
    Returns:
        缩略图 URL，失败返回 None
    """
    if images is None:
        if not os.path.exists(folder_path):
            return None
        files = os.listdir(folder_path)
        images = [f for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_IMAGE]
    
    if not images:
        return None
    
    img_path = os.path.join(folder_path, images[0])
    return generate_thumb(img_path)
