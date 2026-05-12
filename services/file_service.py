"""
时光印记 - 文件服务
负责媒体文件（图片/视频）的增删改查
"""
import os
import re
import uuid
from config import SUPPORTED_IMAGE, SUPPORTED_VIDEO


def get_files(folder_path):
    """获取文件夹中的图片和视频列表"""
    files = []
    if not os.path.exists(folder_path):
        return files
    
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
        files.append({
            'name': name,
            'path': fpath.replace('\\', '/'),
            'type': ftype,
            'size': os.path.getsize(fpath),
        })
    return files


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
    real = os.path.realpath(file_path)
    if not real.startswith(os.path.realpath(root_dir)):
        return False, '禁止访问'
    if os.path.exists(real):
        os.remove(real)
    return True, None


def rename_file(old_path, new_name, root_dir):
    """重命名文件（安全检查）"""
    real = os.path.realpath(old_path)
    if not real.startswith(os.path.realpath(root_dir)):
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
    real = os.path.realpath(file_path)
    if not real.startswith(os.path.realpath(root_dir)):
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
