"""
时光印记 - 文章服务
负责多文章系统的 CRUD、迁移等
"""
import os
import re
import json
import time


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
        with open(meta_file, 'r', encoding='utf-8-sig') as f:
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
        import shutil
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


def create_article(folder_path, title, author=''):
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


def rename_article(folder_path, article_key, new_title):
    """重命名文章"""
    meta = load_articles_meta(folder_path)
    if article_key not in meta:
        return False, '文章不存在'
    
    articles_dir = get_articles_dir(folder_path)
    new_filename = re.sub(r'[<>:"/\\|?*]', '', new_title) + '.md'
    old_filename = meta[article_key].get('file', article_key + '.md')
    
    new_filepath = os.path.join(articles_dir, new_filename)
    old_filepath = os.path.join(articles_dir, old_filename)
    
    if new_filename != old_filename and os.path.exists(new_filepath):
        return False, f'文件名 "{new_filename}" 已存在'
    
    if os.path.exists(old_filepath) and new_filename != old_filename:
        try:
            os.rename(old_filepath, new_filepath)
            meta[article_key]['file'] = new_filename
        except Exception as e:
            return False, f'重命名文件失败: {str(e)}'
    
    meta[article_key]['title'] = new_title
    meta[article_key]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    save_articles_meta(folder_path, meta)
    return True, None


def move_article(source_folder, target_folder, article_key):
    """移动文章到另一个章节"""
    source_meta = load_articles_meta(source_folder)
    if article_key not in source_meta:
        return False, '文章不存在', None
    
    article_info = source_meta[article_key]
    target_articles_dir = get_articles_dir(target_folder)
    target_meta = load_articles_meta(target_folder)
    
    new_key = article_key
    counter = 1
    original_key = article_key
    while new_key in target_meta:
        new_key = f'{original_key}_{counter}'
        counter += 1
    
    source_articles_dir = get_articles_dir(source_folder)
    old_filename = article_info.get('file', article_key + '.md')
    old_filepath = os.path.join(source_articles_dir, old_filename)
    
    if new_key != article_key:
        name_part = os.path.splitext(old_filename)[0]
        ext = os.path.splitext(old_filename)[1]
        new_filename = re.sub(r'[<>:"/\\|?*]', '', new_key) + ext
    else:
        new_filename = old_filename
    
    dest_filepath = os.path.join(target_articles_dir, new_filename)
    if os.path.exists(dest_filepath):
        name_part, ext = os.path.splitext(new_filename)
        c = 1
        while os.path.exists(dest_filepath):
            dest_filepath = os.path.join(target_articles_dir, f"{name_part}_{c}{ext}")
            new_filename = f"{name_part}_{c}{ext}"
            c += 1
    
    import shutil
    if os.path.exists(old_filepath):
        shutil.move(old_filepath, dest_filepath)
    
    del source_meta[article_key]
    save_articles_meta(source_folder, source_meta)
    
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    target_meta[new_key] = {
        'title': article_info.get('title', new_key),
        'file': new_filename,
        'author': article_info.get('author', ''),
        'created_at': article_info.get('created_at', now),
        'updated_at': now,
        '_moved_from': os.path.basename(source_folder)
    }
    save_articles_meta(target_folder, target_meta)
    
    return True, None, new_key


def save_article(folder_path, article_key, content, author=''):
    """保存文章内容"""
    meta = load_articles_meta(folder_path)
    
    if article_key and article_key in meta:
        articles_dir = get_articles_dir(folder_path)
        filename = meta[article_key].get('file', article_key + '.md')
        filepath = os.path.join(articles_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        meta[article_key]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if author:
            meta[article_key]['author'] = author
        save_articles_meta(folder_path, meta)
        return True, filename
    
    # Fallback: save to root level README.md
    md_name = 'README.md'
    for f in os.listdir(folder_path):
        if f.lower().endswith('.md') and not f.startswith('_'):
            md_name = f
            break
    with open(os.path.join(folder_path, md_name), 'w', encoding='utf-8') as f:
        f.write(content)
    return True, md_name


def get_legacy_article(folder_path):
    """读取章节的 MD 文章（兼容旧版单文章模式）"""
    if not os.path.exists(folder_path):
        return None, None
    for name in os.listdir(folder_path):
        if name.lower().endswith('.md'):
            fpath = os.path.join(folder_path, name)
            with open(fpath, 'r', encoding='utf-8') as f:
                return name, f.read()
    return None, None
