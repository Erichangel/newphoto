"""
时光印记 - 页面路由
负责 HTML 页面渲染
"""
import time
from flask import request, render_template, make_response, send_from_directory
from config import config as app_config
from services.chapter_service import get_chapters, get_chapter_folder
from services.article_service import get_legacy_article
from services.file_service import get_files
from utils.markdown_utils import simple_markdown
from routes import page_bp


@page_bp.route('/')
def shell():
    """Shell 页面 - 音乐播放器 + iframe（永不刷新）"""
    return render_template('shell.html')


@page_bp.route('/home')
def home():
    """首页内容 - 章节列表（在 iframe 中加载）"""
    chapters = get_chapters()
    version_ts = '04/19 14:30'
    return render_template('index.html', chapters=chapters, root_dir=app_config.root_dir, version_ts=version_ts, is_iframe=True)


@page_bp.route('/chapter/<path:name>')
def chapter(name):
    """章节详情 - 图片/视频/文章"""
    try:
        from urllib.parse import unquote
        raw_name = request.path.split('/chapter/')[-1]
        name = unquote(raw_name)
    except Exception:
        pass
    
    folder_path = get_chapter_folder(name)
    if not folder_path:
        return '章节不存在', 404
    
    files = get_files(folder_path)
    md_name, md_content = get_legacy_article(folder_path)
    chapters = get_chapters()
    
    chapter_names = [c['name'] for c in chapters]
    idx = chapter_names.index(name) if name in chapter_names else -1
    prev_chapter = chapter_names[idx - 1] if idx > 0 else None
    next_chapter = chapter_names[idx + 1] if idx < len(chapter_names) - 1 else None
    
    response = make_response(render_template('chapter.html',
        chapter_name=name,
        files=files,
        md_name=md_name,
        md_content=md_content,
        md_html=simple_markdown(md_content),
        chapters=chapters,
        prev_chapter=prev_chapter,
        next_chapter=next_chapter,
        is_iframe=True))
    return response


@page_bp.route('/thumb/<filename>')
def thumb(filename):
    """缩略图"""
    from config import THUMB_DIR
    response = send_from_directory(THUMB_DIR, filename)
    response.headers['Cache-Control'] = 'public, max-age=86400'
    response.headers['Expires'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(time.time() + 86400))
    return response


@page_bp.route('/favicon.ico')
def favicon():
    """网站图标"""
    import base64
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
      <path fill="#E91E63" d="M16 28s-12-7.5-12-15c0-3.5 2.5-6 6-6 2 0 4 1 6 3.5C18 8 20 7 22 7c3.5 0 6 2.5 6 6 0 7.5-12 15-12 15z"/>
    </svg>'''
    response = make_response(base64.b64decode(base64.b64encode(svg.encode())))
    response.headers['Content-Type'] = 'image/svg+xml'
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@page_bp.route('/file/<path:fpath>')
def serve_file(fpath):
    """直接访问文件（图片/视频）"""
    from flask import send_file
    from urllib.parse import unquote
    fpath = unquote(fpath)
    real = __import__('os').path.realpath(fpath)
    if not real.startswith(__import__('os').path.realpath(app_config.root_dir)):
        return '禁止访问', 403
    if not __import__('os').path.exists(real):
        return '文件不存在', 404
    
    response = make_response(send_file(real, as_attachment=False, conditional=True))
    response.headers['Cache-Control'] = 'public, max-age=3600'
    response.headers['Expires'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(time.time() + 3600))
    
    ext = __import__('os').path.splitext(real)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
        '.gif': 'image/gif', '.webp': 'image/webp',
        '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo', '.mkv': 'video/x-matroska',
    }
    if ext in mime_types:
        response.headers['Content-Type'] = mime_types[ext]
    
    return response
