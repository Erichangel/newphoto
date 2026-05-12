"""
时光印记 - 用户 API 路由
"""
from flask import request, jsonify
from services.user_service import (
    list_users, create_user, select_user, get_current_user,
    save_last_chapter, get_last_chapter, delete_user,
)
from routes import user_api_bp


@user_api_bp.route('/list', methods=['GET'])
def api_list_users():
    """获取所有用户列表"""
    user_list = list_users()
    return jsonify({'ok': True, 'users': user_list})


@user_api_bp.route('/create', methods=['POST'])
def api_create_user():
    """创建新用户"""
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'error': '用户名不能为空'}), 400
    
    user_id, user_name = create_user(name)
    return jsonify({'ok': True, 'user_id': user_id, 'name': user_name})


@user_api_bp.route('/select', methods=['POST'])
def api_select_user():
    """选择当前用户"""
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'error': '用户 ID 不能为空'}), 400
    if not select_user(user_id):
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({'ok': True})


@user_api_bp.route('/current', methods=['GET'])
def api_get_current_user():
    """获取当前用户信息"""
    user = get_current_user()
    if user:
        return jsonify({'ok': True, 'user': user})
    return jsonify({'ok': True, 'user': None})


@user_api_bp.route('/last-chapter', methods=['POST'])
def api_save_last_chapter():
    """保存用户最后访问的章节"""
    try:
        from services.user_service import get_current_user_id
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': '未登录'}), 401
        
        chapter_name = request.json.get('chapter_name')
        scroll_position = request.json.get('scroll_position', 0)
        save_last_chapter(user_id, chapter_name, scroll_position)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@user_api_bp.route('/last-chapter', methods=['GET'])
def api_get_last_chapter():
    """获取用户最后访问的章节"""
    try:
        from services.user_service import get_current_user_id
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'ok': True, 'chapter': None, 'scroll_position': 0})
        
        chapter, scroll_pos = get_last_chapter(user_id)
        return jsonify({'ok': True, 'chapter': chapter, 'scroll_position': scroll_pos})
    except Exception:
        return jsonify({'ok': True, 'chapter': None, 'scroll_position': 0})


@user_api_bp.route('/delete', methods=['POST'])
def api_delete_user():
    """删除用户"""
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'error': '用户 ID 不能为空'}), 400
    
    deleted_name = delete_user(user_id)
    if deleted_name is None:
        return jsonify({'error': '用户不存在'}), 404
    
    return jsonify({'ok': True, 'deleted_name': deleted_name})
