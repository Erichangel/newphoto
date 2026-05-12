"""
时光印记 - 路由模块
负责所有 Flask 路由注册
"""
from flask import Blueprint

# HTML 页面路由
page_bp = Blueprint('page', __name__)

# API 路由
user_api_bp = Blueprint('user_api', __name__, url_prefix='/api/user')
chapter_api_bp = Blueprint('chapter_api', __name__, url_prefix='/api/chapter')
file_api_bp = Blueprint('file_api', __name__, url_prefix='/api/file')
article_api_bp = Blueprint('article_api', __name__, url_prefix='/api')
music_api_bp = Blueprint('music_api', __name__, url_prefix='/api')
settings_api_bp = Blueprint('settings_api', __name__, url_prefix='/api')
