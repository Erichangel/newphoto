"""
时光印记 - 章节 API 路由
"""
from flask import request, jsonify
from services.chapter_service import (
    get_chapters, create_chapter, delete_chapter, rename_chapter,
    invalidate_chapter_cache,
)
from routes import chapter_api_bp


@chapter_api_bp.route('', methods=['GET'])
def api_chapters():
    """获取所有章节列表"""
    chapters = get_chapters()
    return jsonify({'ok': True, 'chapters': [{'name': c['name'], 'year': c.get('year', '')} for c in chapters]})


@chapter_api_bp.route('/rename', methods=['POST'])
def api_rename_chapter():
    """重命名章节文件夹"""
    old_name = request.json.get('old_name')
    new_name = request.json.get('new_name')
    
    success, result = rename_chapter(old_name, new_name)
    if not success:
        return jsonify({'error': result}), 400 if '名称' in result else 404
    return jsonify({'ok': True, 'new_name': result})


@chapter_api_bp.route('/create', methods=['POST'])
def api_create_chapter():
    """新建章节文件夹"""
    year = request.json.get('year', '')
    month = request.json.get('month', '')
    custom_name = request.json.get('custom_name', '').strip()
    old_name = request.json.get('name', '').strip()
    
    if year and month and custom_name:
        name = f"{year}.{month}{custom_name}"
    elif old_name:
        name = old_name
    else:
        return jsonify({'error': '请填写完整信息'}), 400
    
    success, result = create_chapter(name)
    if not success:
        return jsonify({'error': result}), 400
    return jsonify({'ok': True, 'name': result})


@chapter_api_bp.route('/delete', methods=['POST'])
def api_delete_chapter():
    """删除章节文件夹"""
    name = request.json.get('name')
    success, error = delete_chapter(name)
    if not success:
        return jsonify({'error': error}), 404
    return jsonify({'ok': True})
