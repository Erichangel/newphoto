"""
时光印记 - 文件 API 路由
"""
from flask import request, jsonify
from config import config as app_config
from services.chapter_service import get_chapter_folder, invalidate_chapter_cache
from services.file_service import upload_files, delete_file, rename_file, move_file, rotate_image, get_files
from routes import file_api_bp


@file_api_bp.route('/upload', methods=['POST'])
def api_upload_file():
    """上传图片/视频到章节"""
    chapter = request.form.get('chapter')
    folder = get_chapter_folder(chapter)
    if not __import__('os').path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    
    uploaded = request.files.getlist('files')
    saved = upload_files(folder, uploaded)
    invalidate_chapter_cache()
    return jsonify({'ok': True, 'saved': saved})


@file_api_bp.route('/delete', methods=['POST'])
def api_delete_file():
    """删除文件"""
    fpath = request.json.get('path')
    success, error = delete_file(fpath, app_config.root_dir)
    if not success:
        return jsonify({'error': error}), 403
    invalidate_chapter_cache()
    return jsonify({'ok': True})


@file_api_bp.route('/rename', methods=['POST'])
def api_rename_file():
    """重命名文件"""
    old_path = request.json.get('old_path')
    new_name = request.json.get('new_name')
    success, error, new_path = rename_file(old_path, new_name, app_config.root_dir)
    if not success:
        return jsonify({'error': error}), 400 if '名称' in error else 404
    invalidate_chapter_cache()
    return jsonify({'ok': True, 'new_path': new_path})


@file_api_bp.route('/move', methods=['POST'])
def api_move_file():
    """将文件移动到另一个章节"""
    file_path = request.json.get('path', '')
    target_chapter = request.json.get('target_chapter', '').strip()
    
    if not file_path or not target_chapter:
        return jsonify({'error': '参数不完整'}), 400
    
    success, error, new_path = move_file(file_path, target_chapter, app_config.root_dir)
    if not success:
        return jsonify({'error': error}), 404 if '不存在' in error else 403
    invalidate_chapter_cache()
    return jsonify({
        'ok': True,
        'new_path': new_path,
        'target_chapter': target_chapter,
        'filename': __import__('os').path.basename(new_path),
    })


@file_api_bp.route('/rotate', methods=['POST'])
def api_rotate_image():
    """旋转图片并覆盖原文件"""
    import os as _os
    import hashlib
    from config import THUMB_DIR
    
    file_path = request.json.get('path', '')
    degrees = request.json.get('degrees', 90)
    
    if not file_path:
        return jsonify({'error': '参数不完整'}), 400
    if degrees not in [90, 180, 270]:
        return jsonify({'error': '旋转角度无效'}), 400
    
    success, error = rotate_image(file_path, degrees, app_config.root_dir)
    if not success:
        return jsonify({'error': error}), 400 if '禁止' in error else 404
    
    # 删除该图片对应的缩略图缓存，使首页章节封面能显示旋转后的图片
    try:
        img_path_for_hash = file_path.replace('\\', '/')
        thumb_name = hashlib.md5(img_path_for_hash.encode('utf-8')).hexdigest() + '.jpg'
        thumb_path = _os.path.join(THUMB_DIR, thumb_name)
        if _os.path.exists(thumb_path):
            _os.remove(thumb_path)
    except Exception:
        pass  # 缩略图删除失败不影响主流程
    
    invalidate_chapter_cache()
    return jsonify({'ok': True})


@file_api_bp.route('/list', methods=['GET'])
def api_list_files():
    """获取当前章节的文件列表"""
    chapter = request.args.get('chapter')
    if not chapter:
        return jsonify({'error': '参数不完整'}), 400
    folder = get_chapter_folder(chapter)
    if not __import__('os').path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    
    # 传递章节名称以支持自定义排序
    files = get_files(folder, chapter_name=chapter)
    
    # 获取当前封面信息
    from services.thumb_service import get_chapter_cover
    cover_path = get_chapter_cover(chapter)
    
    invalidate_chapter_cache()
    return jsonify({
        'ok': True,
        'files': [{'name': f['name'], 'path': f['path'], 'type': f['type'], 'mtime': f.get('mtime')} for f in files],
        'cover': cover_path,
        'chapter': chapter,
    })


@file_api_bp.route('/set-cover', methods=['POST'])
def api_set_chapter_cover():
    """设置当前图片为章节封面"""
    import os as _os
    from services.thumb_service import set_chapter_cover, remove_chapter_cover, get_chapter_cover
    
    chapter = request.json.get('chapter', '')
    file_path = request.json.get('path', '')
    action = request.json.get('action', 'set')  # 'set' or 'remove'
    
    if not chapter or not file_path:
        return jsonify({'error': '参数不完整'}), 400
    
    if action == 'remove':
        # 移除自定义封面，恢复为默认第一张
        success, error = remove_chapter_cover(chapter)
    else:
        # 设置封面 - 直接使用 API 返回的 path 字段
        full_path = _os.path.join(app_config.root_dir, file_path)
        real_path = _os.path.realpath(full_path)
        root_real = _os.path.realpath(app_config.root_dir)
        # 调试日志
        import sys
        print(f'[DEBUG] file_path={file_path}', file=sys.stderr)
        print(f'[DEBUG] full_path={full_path}', file=sys.stderr)
        print(f'[DEBUG] real_path={real_path}', file=sys.stderr)
        print(f'[DEBUG] root_real={root_real}', file=sys.stderr)
        print(f'[DEBUG] starts_with={real_path.startswith(root_real)}', file=sys.stderr)
        print(f'[DEBUG] exists={_os.path.exists(real_path)}', file=sys.stderr)
        if not real_path.startswith(root_real):
            return jsonify({'error': '禁止访问 (real_path={} root={})'.format(real_path, root_real)}), 403
        if not _os.path.exists(real_path):
            return jsonify({'error': '文件不存在'}), 404
        success, error = set_chapter_cover(chapter, real_path)
    
    if not success:
        return jsonify({'error': error}), 400
    
    invalidate_chapter_cache()
    return jsonify({'ok': True})


@file_api_bp.route('/order', methods=['POST'])
def api_set_file_order():
    """保存章节文件排序"""
    from services.file_service import save_chapter_file_order
    
    chapter = request.json.get('chapter', '')
    file_order = request.json.get('order', [])
    
    if not chapter:
        return jsonify({'error': '参数不完整'}), 400
    
    success, error = save_chapter_file_order(chapter, file_order)
    if not success:
        return jsonify({'error': error}), 400
    
    invalidate_chapter_cache()
    return jsonify({'ok': True})


@file_api_bp.route('/order', methods=['GET'])
def api_get_file_order():
    """获取章节文件排序"""
    from services.file_service import load_chapter_file_order
    
    chapter = request.args.get('chapter', '')
    if not chapter:
        return jsonify({'error': '参数不完整'}), 400
    
    file_order = load_chapter_file_order(chapter)
    return jsonify({'ok': True, 'order': file_order})
