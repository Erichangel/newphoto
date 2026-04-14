"""
时光印记 - 精简版
直接读取本地文件夹作为章节，MD文件作为文章，支持图片/视频管理。
"""
import os
import re
import shutil
import uuid
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from PIL import Image

app = Flask(__name__)

# ============ 配置 ============
ROOT_DIR = r'K:\Pictures\照片库'  # ← 改成你的照片总文件夹路径
SUPPORTED_IMAGE = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
SUPPORTED_VIDEO = {'.mp4', '.webm', '.mov', '.avi', '.mkv'}
THUMB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_thumbs')
os.makedirs(THUMB_DIR, exist_ok=True)


def get_chapters():
    """扫描根目录，每个子文件夹是一个章节，按名称排序"""
    chapters = []
    if not os.path.exists(ROOT_DIR):
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
                'path': path,
                'image_count': len(images),
                'video_count': len(videos),
                'has_article': md_file is not None,
                'cover': get_cover(path, images),
            })
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
                img.thumbnail((400, 300), Image.LANCZOS)
                img.save(thumb_path, 'JPEG', quality=80)
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


# ============ 路由 ============

@app.route('/')
def index():
    """首页 - 章节列表"""
    chapters = get_chapters()
    return render_template('index.html', chapters=chapters, root_dir=ROOT_DIR)


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
    return render_template('chapter.html',
                           chapter_name=name,
                           files=files,
                           md_name=md_name,
                           md_content=md_content,
                           md_html=simple_markdown(md_content),
                           chapters=chapters,
                           prev_chapter=prev_chapter,
                           next_chapter=next_chapter)


@app.route('/thumb/<filename>')
def thumb(filename):
    """缩略图"""
    return send_from_directory(THUMB_DIR, filename)


@app.route('/file/<path:fpath>')
def serve_file(fpath):
    """直接访问文件（图片/视频）"""
    from urllib.parse import unquote
    fpath = unquote(fpath)
    # 安全检查：确保路径在 ROOT_DIR 下
    real = os.path.realpath(fpath)
    if not real.startswith(os.path.realpath(ROOT_DIR)):
        return '禁止访问', 403
    return send_file(real)


# ============ API ============

@app.route('/api/chapter/rename', methods=['POST'])
def api_rename_chapter():
    """重命名章节文件夹"""
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
    return jsonify({'ok': True, 'new_name': new_name})


@app.route('/api/chapter/create', methods=['POST'])
def api_create_chapter():
    """新建章节文件夹"""
    name = request.json.get('name', '').strip()
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
    return jsonify({'ok': True, 'name': name})


@app.route('/api/chapter/delete', methods=['POST'])
def api_delete_chapter():
    """删除章节文件夹"""
    name = request.json.get('name')
    path = os.path.join(ROOT_DIR, name)
    if not os.path.exists(path):
        return jsonify({'error': '不存在'}), 404
    shutil.rmtree(path)
    return jsonify({'ok': True})


@app.route('/api/file/upload', methods=['POST'])
def api_upload_file():
    """上传图片/视频到章节"""
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
    return jsonify({'ok': True, 'saved': saved})


@app.route('/api/file/delete', methods=['POST'])
def api_delete_file():
    """删除文件"""
    fpath = request.json.get('path')
    real = os.path.realpath(fpath)
    if not real.startswith(os.path.realpath(ROOT_DIR)):
        return jsonify({'error': '禁止'}), 403
    if os.path.exists(real):
        os.remove(real)
    return jsonify({'ok': True})


@app.route('/api/file/rename', methods=['POST'])
def api_rename_file():
    """重命名文件"""
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
    return jsonify({'ok': True, 'new_path': new_path})


@app.route('/api/article/save', methods=['POST'])
def api_save_article():
    """保存文章"""
    chapter = request.json.get('chapter')
    content = request.json.get('content')
    folder = os.path.join(ROOT_DIR, chapter)
    if not os.path.exists(folder):
        return jsonify({'error': '章节不存在'}), 404
    # 找到已有的 MD 文件，或创建 README.md
    md_name = 'README.md'
    for f in os.listdir(folder):
        if f.lower().endswith('.md'):
            md_name = f
            break
    with open(os.path.join(folder, md_name), 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'ok': True, 'md_name': md_name})


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """获取/修改根目录设置"""
    global ROOT_DIR
    if request.method == 'GET':
        return jsonify({'root_dir': ROOT_DIR})
    new_dir = request.json.get('root_dir', '').strip()
    if new_dir and os.path.isdir(new_dir):
        ROOT_DIR = new_dir
        # 保存到配置文件
        with open(os.path.join(os.path.dirname(__file__), 'config.txt'), 'w') as f:
            f.write(ROOT_DIR)
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
    app.run(host='0.0.0.0', port=5000, debug=True)
