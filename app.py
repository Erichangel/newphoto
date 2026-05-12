"""
时光印记 - 模块化版本
Thin entry point: creates Flask app, loads config, registers blueprints.
"""
import os
import sys
import io
from flask import Flask

# Set console encoding for UTF-8 support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Import config first (must load before services)
from config import config, load_config

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'time-imprint-secret-key-2024'

# Cache control middleware
@app.after_request
def set_cache_headers(response):
    path = request.path

    # HTML pages and API: no cache
    if ('/api/' in path or path == '/' or path == '/home'
            or path.endswith('.html')
            or (response.content_type and 'text/html' in response.content_type)):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    # Static assets: long cache
    elif any(path.endswith(ext) for ext in ['.css', '.js', '.woff', '.woff2', '.ttf']):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    # Images/videos: medium cache
    elif any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm']):
        response.headers['Cache-Control'] = 'public, max-age=3600'

    return response

# Import request for cache headers
from flask import request

# Register blueprints
from routes.page_routes import page_bp
from routes.user_api import user_api_bp
from routes.chapter_api import chapter_api_bp
from routes.file_api import file_api_bp
from routes.article_api import article_api_bp
from routes.music_api import music_api_bp
from routes.settings_api import settings_api_bp

app.register_blueprint(page_bp)
app.register_blueprint(user_api_bp)
app.register_blueprint(chapter_api_bp)
app.register_blueprint(file_api_bp)
app.register_blueprint(article_api_bp)
app.register_blueprint(music_api_bp)
app.register_blueprint(settings_api_bp)


def load_config():
    """从 config.txt 加载根目录和音乐目录"""
    cfg = os.path.join(os.path.dirname(__file__), 'config.txt')
    if os.path.exists(cfg):
        with open(cfg, 'r') as f:
            lines = f.read().strip().splitlines()
            if lines and os.path.isdir(lines[0].strip()):
                config.root_dir = lines[0].strip()
            if len(lines) > 1 and os.path.isdir(lines[1].strip()):
                config.music_dir = lines[1].strip()


if __name__ == '__main__':
    load_config()
    print(f'\n  时光印记（模块化版）')
    print(f'  照片目录：{config.root_dir}')
    print(f'  访问地址：http://localhost:5240\n')
    app.run(host='0.0.0.0', port=5240, debug=False)
