"""
时光印记 - 文件服务
负责媒体文件（图片/视频）的增删改查
"""
import os
import re
import json
import uuid
from config import SUPPORTED_IMAGE, SUPPORTED_VIDEO, get_chapter_file_order_file
from config import config as app_config


def _get_file_order_path():
    """获取当前根目录的文件排序配置路径"""
    return get_chapter_file_order_file(app_config.root_dir)


def _resolve_path(file_path, root_dir):
    """统一路径解析，兼容前端传来的正斜杠路径
    
    Returns:
        (real_path, real_root_dir) 统一后的绝对路径，失败返回 None
    """
    normalized = file_path.replace('/', '\\')
    real = os.path.realpath(normalized)
    real_root = os.path.realpath(root_dir)
    if not real.startswith(real_root + '\\') and real != real_root:
        return None, None
    return real, real_root


def rotate_image(file_path, degrees, root_dir):
    """旋转图片并覆盖原文件
    
    Args:
        file_path: 图片文件路径
        degrees: 旋转角度（90, 180, 270）
        root_dir: 根目录（安全检查）
    
    Returns:
        (success, error_message)
    """
    real, _ = _resolve_path(file_path, root_dir)
    if real is None:
        return False, '禁止访问'
    if not os.path.exists(real):
        return False, '文件不存在'
    
    ext = os.path.splitext(real)[1].lower()
    if ext not in SUPPORTED_IMAGE:
        return False, '仅支持图片文件'
    
    try:
        from PIL import Image
        with Image.open(real) as img:
            img = img.copy()
        
        ext = ext.lower()
        
        # 获取原始 EXIF 数据
        original_exif = None
        try:
            original_exif = img.info.get('exif', None)
        except Exception:
            pass
        
        # 处理 EXIF 方向信息 - 应用旋转并重置方向为 1
        has_orientation_fix = False
        try:
            exif_data = img.getexif()
            if exif_data:
                orientation = exif_data.get(274, 1)
                if orientation != 1:
                    rotate_methods = {
                        2: Image.FLIP_LEFT_RIGHT,
                        3: Image.ROTATE_180,
                        4: Image.FLIP_TOP_BOTTOM,
                        5: Image.TRANSPOSE,
                        6: Image.ROTATE_270,
                        7: Image.TRANSVERSE,
                        8: Image.ROTATE_90,
                    }
                    if orientation in rotate_methods:
                        img = img.transpose(rotate_methods[orientation])
                        exif_data[274] = 1
                        has_orientation_fix = True
        except Exception:
            pass
        
        # 旋转
        if degrees == 90:
            img = img.rotate(270, expand=True)
        elif degrees == 180:
            img = img.rotate(180, expand=True)
        elif degrees == 270:
            img = img.rotate(90, expand=True)
        
        # 根据原图格式保存
        if ext in ('.jpg', '.jpeg'):
            save_img = img.convert('RGB') if img.mode in ('P', 'PA', 'RGBA', 'LA') else img
            if has_orientation_fix:
                # 保存时带上修改后的 EXIF 数据
                try:
                    save_img.save(real, 'JPEG', quality=95, optimize=True, exif=img.getexif().tobytes())
                except Exception:
                    # 如果 EXIF 保存失败，不带 EXIF 保存
                    save_img.save(real, 'JPEG', quality=95, optimize=True)
            else:
                save_img.save(real, 'JPEG', quality=95, optimize=True)
        elif ext == '.png':
            save_img = img if img.mode in ('RGB', 'RGBA') else img.convert('RGBA')
            save_img.save(real, 'PNG', optimize=True)
        elif ext == '.gif':
            save_img = img if img.mode == 'P' else img.convert('P')
            save_img.save(real, 'GIF')
        elif ext == '.bmp':
            save_img = img if img.mode == 'RGB' else img.convert('RGB')
            save_img.save(real, 'BMP')
        elif ext == '.webp':
            save_img = img.convert('RGB') if img.mode in ('P', 'PA', 'RGBA', 'LA') else img
            save_img.save(real, 'WEBP', quality=95)
        else:
            save_img = img.convert('RGB') if img.mode in ('P', 'PA', 'RGBA', 'LA') else img
            save_img.save(real, 'JPEG', quality=95, optimize=True)
        
        return True, None
    except ImportError:
        return False, '缺少 PIL 库'
    except Exception as e:
        return False, f'旋转失败: {str(e)}'


def get_files(folder_path, chapter_name=None):
    """获取文件夹中的图片和视频列表
    
    Args:
        folder_path: 文件夹路径
        chapter_name: 章节名称（用于加载自定义排序）
    """
    files = []
    if not os.path.exists(folder_path):
        return files
    
    # 加载自定义排序
    custom_order = []
    if chapter_name:
        custom_order = load_chapter_file_order(chapter_name)
    
    for name in sorted(os.listdir(folder_path)):
        ext = os.path.splitext(name)[1].lower()
        fpath = os.path.join(folder_path, name)
        if not os.path.isfile(fpath):
            continue
        ftype = None
        if ext in SUPPORTED_IMAGE:
            ftype = 'image'
        elif ext in SUPPORTED_VIDEO:
            ftype = 'video'
        else:
            continue
        # 获取文件修改时间，用于前端生成缓存破坏参数
        mtime = int(os.path.getmtime(fpath))
        files.append({
            'name': name,
            'path': fpath.replace('\\', '/'),
            'type': ftype,
            'size': os.path.getsize(fpath),
            'mtime': mtime,
        })
    
    # 如果有自定义排序，按自定义顺序重新排列
    if custom_order and len(custom_order) > 1:
        # 创建文件名到索引的映射
        name_to_idx = {f['name']: i for i, f in enumerate(files)}
        # 按照自定义顺序排序，未出现在自定义顺序中的文件追加到末尾
        ordered_files = []
        seen = set()
        for name in custom_order:
            if name in name_to_idx and name_to_idx[name] < len(files):
                ordered_files.append(files[name_to_idx[name]])
                seen.add(name)
        # 追加未在自定义顺序中的文件（按原顺序）
        for f in files:
            if f['name'] not in seen:
                ordered_files.append(f)
        files = ordered_files
    
    return files


def load_chapter_file_order(chapter_name):
    """加载章节文件排序"""
    order_file = _get_file_order_path()
    if os.path.exists(order_file):
        try:
            with open(order_file, 'r', encoding='utf-8') as f:
                orders = json.load(f)
                return orders.get(chapter_name, [])
        except Exception:
            pass
    return []


def save_chapter_file_order(chapter_name, file_order):
    """保存章节文件排序"""
    orders = {}
    order_file = _get_file_order_path()
    if os.path.exists(order_file):
        try:
            with open(order_file, 'r', encoding='utf-8') as f:
                orders = json.load(f)
        except Exception:
            pass
    
    orders[chapter_name] = file_order
    with open(order_file, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    return True, None


def upload_files(folder_path, file_list):
    """上传文件到章节文件夹"""
    saved = []
    for f in file_list:
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext in SUPPORTED_IMAGE or ext in SUPPORTED_VIDEO:
                dest = os.path.join(folder_path, f.filename)
                if os.path.exists(dest):
                    name, ex = os.path.splitext(f.filename)
                    dest = os.path.join(folder_path, f"{name}_{uuid.uuid4().hex[:6]}{ex}")
                f.save(dest)
                saved.append(os.path.basename(dest))
    return saved


def delete_file(file_path, root_dir):
    """删除文件（安全检查）"""
    real, _ = _resolve_path(file_path, root_dir)
    if real is None:
        return False, '禁止访问'
    if os.path.exists(real):
        os.remove(real)
    return True, None


def rename_file(old_path, new_name, root_dir):
    """重命名文件（安全检查）"""
    real, _ = _resolve_path(old_path, root_dir)
    if real is None:
        return False, '禁止访问', None
    if not os.path.exists(real):
        return False, '文件不存在', None
    
    new_name = re.sub(r'[<>:"/\\|?*]', '', new_name)
    new_path = os.path.join(os.path.dirname(real), new_name)
    if os.path.exists(new_path):
        return False, '名称已存在', None
    
    os.rename(real, new_path)
    return True, None, new_path


def move_file(file_path, target_chapter, root_dir):
    """移动文件到另一个章节"""
    real, _ = _resolve_path(file_path, root_dir)
    if real is None:
        return False, '禁止访问', None
    
    target_folder = os.path.join(root_dir, target_chapter)
    if not os.path.exists(target_folder):
        return False, '目标章节不存在', None
    
    filename = os.path.basename(real)
    dest_path = os.path.join(target_folder, filename)
    
    # 处理文件名冲突
    if os.path.exists(dest_path) and real != dest_path:
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(target_folder, f"{name}_{counter}{ext}")
            counter += 1
    
    import shutil
    shutil.move(real, dest_path)
    return True, None, dest_path.replace('\\', '/')
