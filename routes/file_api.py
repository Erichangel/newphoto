"""
时光印记 - 文件 API 路由
"""
from flask import request, jsonify
from config import config as app_config
from services.chapter_service import get_chapter_folder, invalidate_chapter_cache
from services.file_service import upload_files, delete_file, rename_file, move_file
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
