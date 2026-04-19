"""
时光印记 - 精简版
直接读取本地文件夹作为章节，MD 文件作为文章，支持图片/视频管理。
"""
import os
import re
import shutil
import uuid
import time
import json
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, make_response
from PIL import Image

app = Flask(__name__)
app.secret_key = 'time-imprint-secret-key-2024'

# 缓存策略：HTML/API 无缓存，静态资源长缓存
@app.after_request
def set_cache_headers(response):
    path = request.path
    
    # HTML 页面和 API：禁止缓存
    if '/api/' in path or path == '/' or path.endswith('.html'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    # 静态资源：长期缓存（通过版本参数 ?v=xxx 破缓存）
    elif any(path.endswith(ext) for ext in ['.css', '.js', '.woff', '.woff2', '.ttf']):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    # 图片/视频：中等缓存
    elif any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm']):
        response.headers['Cache-Control'] = 'public, max-age=3600'
    
    return response

# ============ 配置 ============
ROOT_DIR = r'K:\Pictures\照片库'  # ← 改成你的照片总文件夹路径
MUSIC_DIR = r'K:\Pictures\音乐'   # ← 音乐文件夹路径
SUPPORTED_IMAGE = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
SUPPORTED_VIDEO = {'.mp4', '.webm', '.mov', '.avi', '.mkv'}
SUPPORTED_AUDIO = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
THUMB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_thumbs')
os.makedirs(THUMB_DIR, exist_ok=True)

# 用户数据文件
USER_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')

def load_users():
    """加载用户数据"""
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """保存用户数据"""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_current_user():
    """获取当前用户（从 session）"""
    from flask import session
    return session.get('user_id')

def set_current_user(user_id):
    """设置当前用户"""
    from flask import session
    session['user_id'] = user_id

# 缓存配置
CACHE_DURATION = 3600  # 缓存时间（秒）
chapter_cache = {}
cache_timestamp = 0


def get_chapters():
    """扫描根目录，每个子文件夹是一个章节，按名称排序"""
    global chapter_cache, cache_timestamp
    current_time = time.time()
    
    # 检查缓存是否有效
    if chapter_cache and (current_time - cache_timestamp) < CACHE_DURATION:
        return chapter_cache
    
    chapters = []
    if not os.path.exists(ROOT_DIR):
        chapter_cache = chapters
        cache_timestamp = current_time
        return chapters
    
    for name in sorted(os.listdir(ROOT_DIR)):
        path = os.path.join(ROOT_DIR, name)
        if os.path.isdir(path):
            files = os.listdir(path)
            images = [f for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_IMAGE]
            videos = [f for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_VIDEO]
            md_file = next((f for f in files if f.lower().endswith('.md')), None)
            chapters.append({
                'name': name,
                'year': name[:4] if len(name) >= 4 and name[:4].isdigit() else '',
                'path': path,
                'image_count': len(images),
                'video_count': len(videos),
                'has_article': md_file is not None,
                'cover': get_cover(path, images),
            })
    
    # 更新缓存
    chapter_cache = chapters
    cache_timestamp = current_time
    return chapters


def get_cover(folder_path, images=None):
    """获取章节封面（第一张图片的缩略图）"""
    if images is None:
        files = os.listdir(folder_path)
        images = [f for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_IMAGE]
    if not images:
        return None
    img_path = os.path.join(folder_path, images[0])
    # 使用稳定的 MD5 哈希方法
    import hashlib
    # 确保路径使用正斜杠，避免哈希值不一致
    img_path_for_hash = img_path.replace('\\', '/')
    thumb_name = hashlib.md5(img_path_for_hash.encode('utf-8')).hexdigest() + '.jpg'
    thumb_path = os.path.join(THUMB_DIR, thumb_name)
    if not os.path.exists(thumb_path):
        try:
            os.makedirs(THUMB_DIR, exist_ok=True)
            with Image.open(img_path) as img:
                if img.mode in ('P', 'PA', 'RGBA', 'LA'):
                    img = img.convert('RGB')
                # 优化：使用更快的缩放方法
                img.thumbnail((400, 300), Image.BICUBIC)
                img.save(thumb_path, 'JPEG', quality=75, optimize=True)
        except:
            return None
    return f'/thumb/{thumb_name}'


def get_files(folder_path):
    """获取文件夹中的图片和视频"""
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


def get_article(folder_path):
    """读取章节的 MD 文章，如果没有则自动创建"""
    if not os.path.exists(folder_path):
        return None, None
    for name in os.listdir(folder_path):
        if name.lower().endswith('.md'):
            fpath = os.path.join(folder_path, name)
            with open(fpath, 'r', encoding='utf-8') as f:
                return name, f.read()
    # 没有 MD 文件，自动创建一个（以章节文件夹名命名）
    chapter_name = os.path.basename(folder_path)
    md_name = chapter_name + '.md'
    md_path = os.path.join(folder_path, md_name)
    default_content = f'# {chapter_name}\n\n在这里写下你的回忆...\n'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(default_content)
    return md_name, default_content
    return None, None


# ============ 多文章系统 ============

def get_articles_dir(folder_path):
    """获取或创建章节的文章目录"""
    articles_dir = os.path.join(folder_path, '_articles')
    if not os.path.exists(articles_dir):
        os.makedirs(articles_dir)
    return articles_dir


def get_articles_meta_file(folder_path):
    """获取文章元数据文件路径"""
    return os.path.join(get_articles_dir(folder_path), 'articles.json')


def load_articles_meta(folder_path):
    """加载文章元数据"""
    meta_file = get_articles_meta_file(folder_path)
    if os.path.exists(meta_file):
        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_articles_meta(folder_path, meta):
    """保存文章元数据"""
    meta_file = get_articles_meta_file(folder_path)
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def migrate_old_article(folder_path):
    """将旧的单文件文章迁移到多文章系统"""
    articles_dir = get_articles_dir(folder_path)
    meta = load_articles_meta(folder_path)
    if len(meta) > 0:
        return False
    
    old_article = None
    for name in os.listdir(folder_path):
        if name.lower().endswith('.md') and not name.startswith('_'):
            fpath = os.path.join(folder_path, name)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            old_article = {'name': name, 'content': content}
            break
    
    if old_article:
        safe_name = old_article['name'].replace('.md', '').replace('/', '_').replace('\\', '_')
        target_path = os.path.join(articles_dir, old_article['name'])
        shutil.move(os.path.join(folder_path, old_article['name']), target_path)
        
        meta[safe_name] = {
            'title': safe_name,
            'file': old_article['name'],
            'author': '',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        save_articles_meta(folder_path, meta)
    
    return bool(old_article)


def list_articles(folder_path):
    """列出章节所有文章"""
    migrate_old_article(folder_path)
    meta = load_articles_meta(folder_path)
    articles_dir = get_articles_dir(folder_path)
    
    result = []
    for key, info in meta.items():
        filepath = os.path.join(articles_dir, info.get('file', key + '.md'))
        exists = os.path.exists(filepath)
        size = os.path.getsize(filepath) if exists else 0
        preview = ''
        if exists:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
                preview = lines[0][:60] if lines else ''
        
        result.append({
            'key': key,
            'title': info.get('title', key),
            'file': info.get('file', key + '.md'),
            'author': info.get('author', ''),
            'created_at': info.get('created_at', ''),
            'updated_at': info.get('updated_at', ''),
            'exists': exists,
            'size': size,
            'preview': preview
        })
    
    result.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return result


def create_new_article(folder_path, title, author=''):
    """创建新文章"""
    articles_dir = get_articles_dir(folder_path)
    meta = load_articles_meta(folder_path)
    
    safe_key = re.sub(r'[<>:"/\\|?*]', '', title).strip()
    if not safe_key:
        safe_key = 'untitled'
    
    counter = 1
    original_key = safe_key
    while safe_key in meta:
        safe_key = f'{original_key}_{counter}'
        counter += 1
    
    filename = safe_key + '.md'
    filepath = os.path.join(articles_dir, filename)
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    default_content = f'# {title}\n\n在这里写下你的回忆...\n'
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(default_content)
    
    meta[safe_key] = {
        'title': title,
        'file': filename,
        'author': author,
        'created_at': now,
        'updated_at': now
    }
    save_articles_meta(folder_path, meta)
    
    return safe_key, filename, default_content


def get_article_content(folder_path, article_key):
    """获取指定文章内容"""
    meta = load_articles_meta(folder_path)
    if article_key not in meta:
        return None, None
    
    articles_dir = get_articles_dir(folder_path)
    filename = meta[article_key].get('file', article_key + '.md')
    filepath = os.path.join(articles_dir, filename)
    
    if not os.path.exists(filepath):
        return None, None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return filename, content


def delete_article(folder_path, article_key):
    """删除文章"""
    meta = load_articles_meta(folder_path)
    if article_key not in meta:
        return False
    
    articles_dir = get_articles_dir(folder_path)
    filename = meta[article_key].get('file', article_key + '.md')
    filepath = os.path.join(articles_dir, filename)
    
    if os.path.exists(filepath):
        os.remove(filepath)
    
    del meta[article_key]
    save_articles_meta(folder_path, meta)
    return True


def simple_markdown(text):
    """简单的 Markdown 转 HTML（不依赖外部库）"""
    if not text:
        return ''
    html = text
    # 标题
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    # 粗体、斜体
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # 引用
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    # 图片
    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', html)
    # 链接
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    # 分割线
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    # 换行
    html = html.replace('\n', '<br>')
    return html


# ============ 背景音乐系统 ============

MUSIC_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'music_config.json')

def load_music_config():
    """加载音乐配置（章节-音乐关联 + 用户设置）"""
    if os.path.exists(MUSIC_CONFIG_FILE):
        with open(MUSIC_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'chapter_music': {}, 'settings': {'auto_switch': True}}

def save_music_config(config):
    """保存音乐配置"""
    with open(MUSIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_music_list():
    """获取音乐文件夹中的所有音频文件"""
    musics = []
    if not os.path.exists(MUSIC_DIR):
        return musics
    for name in sorted(os.listdir(MUSIC_DIR)):
        ext = os.path.splitext(name)[1].lower()
        if ext in SUPPORTED_AUDIO:
            fpath = os.path.join(MUSIC_DIR, name)
            if not os.path.isfile(fpath):
                continue
            try:
                size = os.path.getsize(fpath)
                musics.append({
                    'name': name,
                    'size': size,
                    'size_display': f'{size / 1024 / 1024:.1f}MB' if size > 1024 * 1024 else f'{size / 1024:.0f}KB'
                })
            except (OSError, IOError):
                continue
    return musics


@app.route('/api/music/list', methods=['GET'])
def api_music_list():
    """获取音乐列表"""
    musics = get_music_list()
    return jsonify({'ok': True, 'musics': musics, 'music_dir': MUSIC_DIR})

@app.route('/api/music/serve')
def api_serve_music():
    """提供音乐文件下载/播放"""
    from urllib.parse import unquote
    raw_filename = request.args.get('f', '')
    safe_filename = os.path.basename(raw_filename)
    filepath = os.path.join(MUSIC_DIR, safe_filename)
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        safe_filename = unquote(raw_filename)
        filepath = os.path.join(MUSIC_DIR, safe_filename)
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        return '文件不存在: ' + repr(safe_filename), 404
    ext = os.path.splitext(safe_filename)[1].lower()
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        '.flac': 'audio/flac',
        '.aac': 'audio/aac'
    }
    with open(filepath, 'rb') as f:
        data = f.read()
    resp = make_response(data)
    resp.headers['Content-Type'] = mime_types.get(ext, 'application/octet-stream')
    resp.headers['Content-Length'] = len(data)
    resp.headers['Accept-Ranges'] = 'bytes'
    return resp

@app.route('/api/chapter/music', methods=['GET', 'POST'])
def api_chapter_music():
    """获取/设置章节关联的音乐"""
    config = load_music_config()
    if request.method == 'GET':
        chapter = request.args.get('chapter', '')
        music_name = config['chapter_music'].get(chapter, '')
        return jsonify({'ok': True, 'music': music_name})
    elif request.method == 'POST':
        chapter = request.json.get('chapter', '')
        music = request.json.get('music', '')
        if not chapter:
            return jsonify({'error': '章节名不能为空'}), 400
        if music:
            config['chapter_music'][chapter] = music
        else:
            config['chapter_music'].pop(chapter, None)
        save_music_config(config)
        return jsonify({'ok': True})

@app.route('/api/music/settings', methods=['GET', 'POST'])
def api_music_settings():
    """获取/修改音乐播放设置"""
    config = load_music_config()
    if request.method == 'GET':
        return jsonify({'ok': True, 'settings': config.get('settings', {'auto_switch': True})})
    elif request.method == 'POST':
        settings = request.json.get('settings', {})
        config.setdefault('settings', {}).update(settings)
        save_music_config(config)
        return jsonify({'ok': True})


# ============ 路由 ============

@app.route('/')
def index():
    """首页 - 章节列表"""
    chapters = get_chapters()
    version_ts = '04/19 14:30'
    return render_template('index.html', chapters=chapters, root_dir=ROOT_DIR, version_ts=version_ts)


@app.route('/chapter/<path:name>')
def chapter(name):
    """章节详情 - 图片/视频/文章"""
    folder_path = os.path.join(ROOT_DIR, name)
    if not os.path.exists(folder_path):
        return '章节不存在', 404
    files = get_files(folder_path)
    md_name, md_content = get_article(folder_path)
    chapters = get_chapters()
    # 找到当前章节的索引
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
                           next_chapter=next_chapter))
    return response


@app.route('/thumb/<filename>')
def thumb(filename):
    """缩略图"""
    response = send_from_directory(THUMB_DIR, filename)
    # 添加缓存头
    response.headers['Cache-Control'] = 'public, max-age=86400'
    response.headers['Expires'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(time.time() + 86400))
    return response


@app.route('/favicon.ico')
def favicon():
    """网站图标"""
    import base64
    # 粉色心形 SVG 图标
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
      <path fill="#E91E63" d="M16 28s-12-7.5-12-15c0-3.5 2.5-6 6-6 2 0 4 1 6 3.5C18 8 20 7 22 7c3.5 0 6 2.5 6 6 0 7.5-12 15-12 15z"/>
    </svg>'''
    response = make_response(base64.b64decode(base64.b64encode(svg.encode())))
    response.headers['Content-Type'] = 'image/svg+xml'
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@app.route('/file/<path:fpath>')
def serve_file(fpath):
    """直接访问文件（图片/视频）"""
    from urllib.parse import unquote
    fpath = unquote(fpath)
    # 安全检查：确保路径在 ROOT_DIR 下
    real = os.path.realpath(fpath)
    if not real.startswith(os.path.realpath(ROOT_DIR)):
        return '禁止访问', 403
    
    if not os.path.exists(real):
        return '文件不存在', 404
    
    # 优化：使用 send_file 替代 send_from_directory
    response = make_response(send_file(
        real,
        as_attachment=False,
        conditional=True
    ))
    
    # 添加缓存头
    response.headers['Cache-Control'] = 'public, max-age=3600'
    response.headers['Expires'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(time.time() + 3600))
    
    # 优化：设置适当的 Content-Type
    ext = os.path.splitext(real)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska'
    }
    if ext in mime_types:
        response.headers['Content-Type'] = mime_types[ext]
    
    return response


# ============ 用户管理 API ============

@app.route('/api/user/list', methods=['GET'])
def api_list_users():
    """获取所有用户列表"""
    users = load_users()
    user_list = [{'id': uid, 'name': uinfo['name'], 'created_at': uinfo.get('created_at', '')} 
                 for uid, uinfo in users.items()]
    return jsonify({'ok': True, 'users': user_list})

@app.route('/api/user/create', methods=['POST'])
def api_create_user():
    """创建新用户"""
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'error': '用户名不能为空'}), 400
    
    users = load_users()
    user_id = str(uuid.uuid4())[:8]
    users[user_id] = {
        'name': name,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'last_chapter': None,
        'scroll_position': 0
    }
    save_users(users)
    
    # 设置当前用户
    set_current_user(user_id)
    
    return jsonify({'ok': True, 'user_id': user_id, 'name': name})

@app.route('/api/user/select', methods=['POST'])
def api_select_user():
    """选择当前用户"""
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'error': '用户 ID 不能为空'}), 400
    
    users = load_users()
    if user_id not in users:
        return jsonify({'error': '用户不存在'}), 404
    
    set_current_user(user_id)
    return jsonify({'ok': True})

@app.route('/api/user/current', methods=['GET'])
def api_get_current_user():
    """获取当前用户信息"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'ok': True, 'user': None})
    
    users = load_users()
    if user_id in users:
        return jsonify({'ok': True, 'user': {'id': user_id, 'name': users[user_id]['name']}})
    return jsonify({'ok': True, 'user': None})

@app.route('/api/user/last-chapter', methods=['POST'])
def api_save_last_chapter():
    """保存用户最后访问的章节"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': '未登录'}), 401

        chapter_name = request.json.get('chapter_name')
        scroll_position = request.json.get('scroll_position', 0)

        users = load_users()
        if user_id in users:
            users[user_id]['last_chapter'] = chapter_name
            users[user_id]['scroll_position'] = scroll_position
            save_users(users)

        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/last-chapter', methods=['GET'])
def api_get_last_chapter():
    """获取用户最后访问的章节"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'ok': True, 'chapter': None, 'scroll_position': 0})

        users = load_users()
        if user_id in users:
            return jsonify({
                'ok': True,
                'chapter': users[user_id].get('last_chapter'),
                'scroll_position': users[user_id].get('scroll_position', 0)
            })
        return jsonify({'ok': True, 'chapter': None, 'scroll_position': 0})
    except Exception as e:
        return jsonify({'ok': True, 'chapter': None, 'scroll_position': 0})


@app.route('/api/user/delete', methods=['POST'])
def api_delete_user():
    """删除用户"""
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'error': '用户 ID 不能为空'}), 400
    
    users = load_users()
    if user_id not in users:
        return jsonify({'error': '用户不存在'}), 404
    
    deleted_name = users[user_id]['name']
    del users[user_id]
    save_users(users)
    
    # 如果删除的是当前用户，清除 session
    current = get_current_user()
    if current == user_id:
        from flask import session
        session.pop('user_id', None)
    
    return jsonify({'ok': True, 'deleted_name': deleted_name})


# ============ API ============

@app.route('/api/chapter/rename', methods=['POST'])
def api_rename_chapter():
    """重命名章节文件夹"""
    global chapter_cache
    old_name = request.json.get('old_name')
    new_name = request.json.get('new_name')
    old_path = os.path.join(ROOT_DIR, old_name)
    new_path = os.path.join(ROOT_DIR, new_name)
    if not os.path.exists(old_path):
        return jsonify({'error': '章节不存在'}), 404
    if os.path.exists(new_path):
        return jsonify({'error': '名称已存在'}), 400
    # 清理文件名中的非法字符
    new_name = re.sub(r'[<>:"/\\|?*]', '', new_name).strip()
    if not new_name:
        return jsonify({'error': '名称无效'}), 400
    new_path = os.path.join(ROOT_DIR, new_name)
    os.rename(old_path, new_path)
    # 清除缓存
    chapter_cache = {}
    return jsonify({'ok': True, 'new_name': new_name})


@app.route('/api/chapter/create', methods=['POST'])
def api_create_chapter():
    """新建章节文件夹（年份.月份 自定义名字）"""
    global chapter_cache
    
    # 支持两种格式：新格式(年/月/自定义名) 和旧格式(直接名称)
    year = request.json.get('year', '')
    month = request.json.get('month', '')
    custom_name = request.json.get('custom_name', '').strip()
    old_name = request.json.get('name', '').strip()
    
    if year and month and custom_name:
        # 新格式：年份 + 月份 + 自定义名字
        name = f"{year}.{month}{custom_name}"
    elif old_name:
        # 旧兼容：直接使用名称
        name = old_name
    else:
        return jsonify({'error': '请填写完整信息'}), 400
    
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    if not name:
        return jsonify({'error': '名称无效'}), 400
    path = os.path.join(ROOT_DIR, name)
    if os.path.exists(path):
        return jsonify({'error': '已存在'}), 400
    os.makedirs(path, exist_ok=True)
    # 创建默认 MD 文件
    with open(os.path.join(path, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(f'# {name}\n\n在这里写下你的回忆...\n')
    # 清除缓存
    chapter_cache = {}
    return jsonify({'ok': True, 'name': name})


@app.route('/api/chapter/delete', methods=['POST'])
def api_delete_chapter():
    """删除章节文件夹"""
    global chapter_cache
    name = request.json.get('name')
    path = os.path.join(ROOT_DIR, name)
    if not os.path.exists(path):
        return jsonify({'error': '不存在'}), 404
    shutil.rmtree(path)
    # 清除缓存
    chapter_cache = {}
    return jsonify({'ok': True})


@app.route('/api/file/upload', methods=['POST'])
def api_upload_file():
    """上传图片/视频到章节"""
    global chapter_cache
    chapter = request.form.get('chapter')
    folder = os.path.join(ROOT_DIR, chapter)
    if not os.path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    uploaded = request.files.getlist('files')
    saved = []
    for f in uploaded:
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext in SUPPORTED_IMAGE or ext in SUPPORTED_VIDEO:
                # 同名文件加后缀
                dest = os.path.join(folder, f.filename)
                if os.path.exists(dest):
                    name, ex = os.path.splitext(f.filename)
                    dest = os.path.join(folder, f"{name}_{uuid.uuid4().hex[:6]}{ex}")
                f.save(dest)
                saved.append(os.path.basename(dest))
    # 清除缓存
    chapter_cache = {}
    return jsonify({'ok': True, 'saved': saved})


@app.route('/api/file/delete', methods=['POST'])
def api_delete_file():
    """删除文件"""
    global chapter_cache
    fpath = request.json.get('path')
    real = os.path.realpath(fpath)
    if not real.startswith(os.path.realpath(ROOT_DIR)):
        return jsonify({'error': '禁止'}), 403
    if os.path.exists(real):
        os.remove(real)
    # 清除缓存
    chapter_cache = {}
    return jsonify({'ok': True})


@app.route('/api/file/rename', methods=['POST'])
def api_rename_file():
    """重命名文件"""
    global chapter_cache
    old_path = request.json.get('old_path')
    new_name = request.json.get('new_name')
    real = os.path.realpath(old_path)
    if not real.startswith(os.path.realpath(ROOT_DIR)):
        return jsonify({'error': '禁止'}), 403
    if not os.path.exists(real):
        return jsonify({'error': '不存在'}), 404
    new_name = re.sub(r'[<>:"/\\|?*]', '', new_name)
    new_path = os.path.join(os.path.dirname(real), new_name)
    if os.path.exists(new_path):
        return jsonify({'error': '名称已存在'}), 400
    os.rename(real, new_path)
    # 清除缓存
    chapter_cache = {}
    return jsonify({'ok': True, 'new_path': new_path})


@app.route('/api/file/move', methods=['POST'])
def api_move_file():
    """将文件（图片/视频）移动到另一个章节"""
    global chapter_cache
    file_path = request.json.get('path', '')
    target_chapter = request.json.get('target_chapter', '').strip()
    
    if not file_path or not target_chapter:
        return jsonify({'error': '参数不完整'}), 400
    
    real = os.path.realpath(file_path)
    if not real.startswith(os.path.realpath(ROOT_DIR)):
        return jsonify({'error': '禁止'}), 403
    if not os.path.exists(real):
        return jsonify({'error': '文件不存在'}), 404
    
    # 目标章节路径
    target_folder = os.path.join(ROOT_DIR, target_chapter)
    if not os.path.exists(target_folder):
        return jsonify({'error': '目标章节不存在'}), 404
    
    filename = os.path.basename(real)
    dest_path = os.path.join(target_folder, filename)
    
    # 检查目标是否已有同名文件
    if os.path.exists(dest_path) and real != dest_path:
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(target_folder, f"{name}_{counter}{ext}")
            counter += 1
    
    shutil.move(real, dest_path)
    chapter_cache = {}
    return jsonify({
        'ok': True,
        'new_path': dest_path.replace('\\', '/'),
        'target_chapter': target_chapter,
        'filename': os.path.basename(dest_path)
    })


# ============ 多文章 API ============

@app.route('/api/articles/list', methods=['GET'])
def api_list_articles():
    """获取章节所有文章列表"""
    chapter = request.args.get('chapter', '')
    folder = os.path.join(ROOT_DIR, chapter)
    if not os.path.exists(folder):
        return jsonify({'ok': True, 'articles': []})
    
    articles = list_articles(folder)
    return jsonify({'ok': True, 'articles': articles})

@app.route('/api/articles/create', methods=['POST'])
def api_create_article():
    """创建新文章"""
    global chapter_cache
    chapter = request.json.get('chapter', '')
    title = request.json.get('title', '').strip()
    author = request.json.get('author', '').strip()
    
    if not title:
        return jsonify({'error': '标题不能为空'}), 400
    
    folder = os.path.join(ROOT_DIR, chapter)
    if not os.path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    
    key, filename, content = create_new_article(folder, title, author)
    chapter_cache = {}
    return jsonify({'ok': True, 'key': key, 'filename': filename, 'content': content})

@app.route('/api/articles/get', methods=['GET'])
def api_get_article():
    """获取指定文章内容"""
    chapter = request.args.get('chapter', '')
    article_key = request.args.get('key', '')
    
    folder = os.path.join(ROOT_DIR, chapter)
    if not os.path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    
    filename, content = get_article_content(folder, article_key)
    if filename is None:
        return jsonify({'error': '文章不存在'}), 404
    
    meta = load_articles_meta(folder)
    article_info = meta.get(article_key, {})
    
    return jsonify({
        'ok': True,
        'filename': filename,
        'content': content,
        'author': article_info.get('author', ''),
        'title': article_info.get('title', article_key),
        'updated_at': article_info.get('updated_at', '')
    })

@app.route('/api/articles/delete', methods=['POST'])
def api_delete_article_api():
    """删除文章"""
    global chapter_cache
    chapter = request.json.get('chapter', '')
    article_key = request.json.get('key', '')
    
    folder = os.path.join(ROOT_DIR, chapter)
    if not os.path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    
    if delete_article(folder, article_key):
        chapter_cache = {}
        return jsonify({'ok': True})
    return jsonify({'error': '文章不存在'}), 404


@app.route('/api/articles/rename', methods=['POST'])
def api_rename_article():
    """重命名文章（同时修改文件名和标题）"""
    global chapter_cache
    chapter = request.json.get('chapter', '')
    article_key = request.json.get('key', '')
    new_title = request.json.get('title', '').strip()
    
    if not new_title:
        return jsonify({'error': '标题不能为空'}), 400
    
    folder = os.path.join(ROOT_DIR, chapter)
    if not os.path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    
    meta = load_articles_meta(folder)
    if article_key not in meta:
        return jsonify({'error': '文章不存在'}), 404
    
    articles_dir = get_articles_dir(folder)
    
    # 生成安全的文件名
    new_filename = re.sub(r'[<>:"/\\|?*]', '', new_title) + '.md'
    old_filename = meta[article_key].get('file', article_key + '.md')
    
    # 检查新文件名是否已存在（排除当前文件）
    new_filepath = os.path.join(articles_dir, new_filename)
    old_filepath = os.path.join(articles_dir, old_filename)
    if new_filename != old_filename and os.path.exists(new_filepath):
        return jsonify({'error': f'文件名 "{new_filename}" 已存在，请使用其他名称'}), 409
    
    # 重命名文件
    if os.path.exists(old_filepath) and new_filename != old_filename:
        try:
            os.rename(old_filepath, new_filepath)
            meta[article_key]['file'] = new_filename
        except Exception as e:
            return jsonify({'error': f'重命名文件失败: {str(e)}'}), 500
    
    # 更新元数据
    meta[article_key]['title'] = new_title
    meta[article_key]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    save_articles_meta(folder, meta)
    chapter_cache = {}
    
    return jsonify({'ok': True})


@app.route('/api/articles/move', methods=['POST'])
def api_move_article():
    """将文章移动到另一个章节"""
    global chapter_cache
    source_chapter = request.json.get('chapter', '')
    target_chapter = request.json.get('target_chapter', '').strip()
    article_key = request.json.get('key', '')
    
    if not source_chapter or not target_chapter or not article_key:
        return jsonify({'error': '参数不完整'}), 400
    
    if source_chapter == target_chapter:
        return jsonify({'error': '目标章节与当前章节相同'}), 400
    
    source_folder = os.path.join(ROOT_DIR, source_chapter)
    target_folder = os.path.join(ROOT_DIR, target_chapter)
    
    if not os.path.exists(source_folder):
        return jsonify({'error': '源章节不存在'}), 404
    if not os.path.exists(target_folder):
        return jsonify({'error': '目标章节不存在'}), 404
    
    # 加载源文章元数据
    source_meta = load_articles_meta(source_folder)
    if article_key not in source_meta:
        return jsonify({'error': '文章不存在'}), 404
    
    article_info = source_meta[article_key]
    
    # 目标章节的文章目录和元数据
    target_articles_dir = get_articles_dir(target_folder)
    target_meta = load_articles_meta(target_folder)
    
    # 检查目标是否已有相同 key 的文章，如果有则生成新 key
    new_key = article_key
    counter = 1
    original_key = article_key
    while new_key in target_meta:
        new_key = f'{original_key}_{counter}'
        counter += 1
    
    # 移动文件
    source_articles_dir = get_articles_dir(source_folder)
    old_filename = article_info.get('file', article_key + '.md')
    old_filepath = os.path.join(source_articles_dir, old_filename)
    
    # 如果重命名了 key，也重命名文件
    if new_key != article_key:
        name_part = os.path.splitext(old_filename)[0]
        ext = os.path.splitext(old_filename)[1]
        new_filename = re.sub(r'[<>:"/\\|?*]', '', new_key) + ext
    else:
        new_filename = old_filename
    
    # 检查目标文件名冲突
    dest_filepath = os.path.join(target_articles_dir, new_filename)
    if os.path.exists(dest_filepath):
        name_part, ext = os.path.splitext(new_filename)
        c = 1
        while os.path.exists(dest_filepath):
            dest_filepath = os.path.join(target_articles_dir, f"{name_part}_{c}{ext}")
            new_filename = f"{name_part}_{c}{ext}"
            c += 1
    
    if os.path.exists(old_filepath):
        shutil.move(old_filepath, dest_filepath)
    
    # 更新源章节：删除文章记录
    del source_meta[article_key]
    save_articles_meta(source_folder, source_meta)
    
    # 更新目标章节：添加文章记录
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    target_meta[new_key] = {
        'title': article_info.get('title', new_key),
        'file': new_filename,
        'author': article_info.get('author', ''),
        'created_at': article_info.get('created_at', now),
        'updated_at': now,
        '_moved_from': source_chapter
    }
    save_articles_meta(target_folder, target_meta)
    
    chapter_cache = {}
    return jsonify({
        'ok': True,
        'new_key': new_key,
        'target_chapter': target_chapter
    })


@app.route('/api/article/save', methods=['POST'])
def api_save_article():
    """保存文章"""
    global chapter_cache
    chapter = request.json.get('chapter')
    content = request.json.get('content')
    article_key = request.json.get('article_key', '')
    author = request.json.get('author', '')
    folder = os.path.join(ROOT_DIR, chapter)
    if not os.path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    
    migrate_old_article(folder)
    
    if article_key:
        meta = load_articles_meta(folder)
        if article_key in meta:
            articles_dir = get_articles_dir(folder)
            filename = meta[article_key].get('file', article_key + '.md')
            filepath = os.path.join(articles_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            meta[article_key]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            if author:
                meta[article_key]['author'] = author
            save_articles_meta(folder, meta)
            chapter_cache = {}
            return jsonify({'ok': True, 'md_name': filename})
    
    md_name = 'README.md'
    for f in os.listdir(folder):
        if f.lower().endswith('.md') and not f.startswith('_'):
            md_name = f
            break
    with open(os.path.join(folder, md_name), 'w', encoding='utf-8') as f:
        f.write(content)
    chapter_cache = {}
    return jsonify({'ok': True, 'md_name': md_name})


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """获取/修改根目录设置"""
    global ROOT_DIR, chapter_cache
    if request.method == 'GET':
        return jsonify({'root_dir': ROOT_DIR})
    new_dir = request.json.get('root_dir', '').strip()
    if new_dir and os.path.isdir(new_dir):
        ROOT_DIR = new_dir
        # 保存到配置文件
        with open(os.path.join(os.path.dirname(__file__), 'config.txt'), 'w') as f:
            f.write(ROOT_DIR)
        # 清除缓存
        chapter_cache = {}
        return jsonify({'ok': True, 'root_dir': ROOT_DIR})
    return jsonify({'error': '目录不存在'}), 400


# ============ 启动 ============

def load_config():
    """从 config.txt 加载根目录"""
    global ROOT_DIR
    cfg = os.path.join(os.path.dirname(__file__), 'config.txt')
    if os.path.exists(cfg):
        with open(cfg, 'r') as f:
            d = f.read().strip()
            if os.path.isdir(d):
                ROOT_DIR = d

if __name__ == '__main__':
    load_config()
    print(f'\n  🌸 时光印记（精简版）')
    print(f'  📂 照片目录: {ROOT_DIR}')
    print(f'  📱 访问地址: http://localhost:5000\n')
    # 关闭 debug 模式，提高性能
    app.run(host='0.0.0.0', port=5000, debug=False)
