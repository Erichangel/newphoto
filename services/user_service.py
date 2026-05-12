"""
时光印记 - 用户服务
负责用户管理、会话等
"""
import os
import json
import time
import uuid
from flask import session
from config import USER_DATA_FILE


def load_users():
    """加载所有用户数据"""
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_users(users):
    """保存用户数据"""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_current_user_id():
    """从 session 获取当前用户 ID"""
    return session.get('user_id')


def set_current_user_id(user_id):
    """设置当前用户 ID 到 session"""
    session['user_id'] = user_id


def get_current_user():
    """获取当前用户完整信息"""
    user_id = get_current_user_id()
    if not user_id:
        return None
    users = load_users()
    return users.get(user_id)


def create_user(name):
    """创建新用户"""
    users = load_users()
    user_id = str(uuid.uuid4())[:8]
    users[user_id] = {
        'name': name,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'last_chapter': None,
        'scroll_position': 0,
    }
    save_users(users)
    set_current_user_id(user_id)
    return user_id, name


def select_user(user_id):
    """选择当前用户"""
    users = load_users()
    if user_id not in users:
        return False
    set_current_user_id(user_id)
    return True


def delete_user(user_id):
    """删除用户"""
    users = load_users()
    if user_id not in users:
        return None
    deleted_name = users[user_id]['name']
    del users[user_id]
    save_users(users)
    
    # 如果删除的是当前用户，清除 session
    current = get_current_user_id()
    if current == user_id:
        session.pop('user_id', None)
    
    return deleted_name


def save_last_chapter(user_id, chapter_name, scroll_position=0):
    """保存用户最后访问的章节"""
    users = load_users()
    if user_id in users:
        users[user_id]['last_chapter'] = chapter_name
        users[user_id]['scroll_position'] = scroll_position
        save_users(users)


def get_last_chapter(user_id):
    """获取用户最后访问的章节"""
    users = load_users()
    if user_id in users:
        return users[user_id].get('last_chapter'), users[user_id].get('scroll_position', 0)
    return None, 0


def list_users():
    """获取所有用户列表"""
    users = load_users()
    return [
        {'id': uid, 'name': uinfo['name'], 'created_at': uinfo.get('created_at', '')}
        for uid, uinfo in users.items()
    ]
