"""
时光印记 - 文章 API 路由
"""
from flask import request, jsonify
from services.chapter_service import get_chapter_folder, invalidate_chapter_cache
from services.article_service import (
    list_articles, create_article, get_article_content, delete_article,
    rename_article, move_article, save_article,
)
from routes import article_api_bp


@article_api_bp.route('/articles/list', methods=['GET'])
def api_list_articles():
    """获取章节所有文章列表"""
    try:
        chapter = request.args.get('chapter', '')
        folder = get_chapter_folder(chapter)
        if not folder:
            return jsonify({'ok': True, 'articles': []})
        
        articles = list_articles(folder)
        return jsonify({'ok': True, 'articles': articles})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@article_api_bp.route('/articles/create', methods=['POST'])
def api_create_article():
    """创建新文章"""
    chapter = request.json.get('chapter', '')
    title = request.json.get('title', '').strip()
    author = request.json.get('author', '').strip()
    
    if not title:
        return jsonify({'error': '标题不能为空'}), 400
    
    folder = get_chapter_folder(chapter)
    if not folder:
        return jsonify({'error': '章节不存在'}), 404
    
    key, filename, content = create_article(folder, title, author)
    invalidate_chapter_cache()
    return jsonify({'ok': True, 'key': key, 'filename': filename, 'content': content})


@article_api_bp.route('/articles/get', methods=['GET'])
def api_get_article():
    """获取指定文章内容"""
    chapter = request.args.get('chapter', '')
    article_key = request.args.get('key', '')
    
    folder = get_chapter_folder(chapter)
    if not folder:
        return jsonify({'error': '章节不存在'}), 404
    
    filename, content = get_article_content(folder, article_key)
    if filename is None:
        return jsonify({'error': '文章不存在'}), 404
    
    meta = __import__('json').loads(open(__import__('os').path.join(folder, '_articles', 'articles.json'), 'r', encoding='utf-8-sig').read())
    article_info = meta.get(article_key, {})
    
    return jsonify({
        'ok': True,
        'filename': filename,
        'content': content,
        'author': article_info.get('author', ''),
        'title': article_info.get('title', article_key),
        'updated_at': article_info.get('updated_at', '')
    })


@article_api_bp.route('/articles/delete', methods=['POST'])
def api_delete_article():
    """删除文章"""
    chapter = request.json.get('chapter', '')
    article_key = request.json.get('key', '')
    
    folder = get_chapter_folder(chapter)
    if not folder:
        return jsonify({'error': '章节不存在'}), 404
    
    if delete_article(folder, article_key):
        invalidate_chapter_cache()
        return jsonify({'ok': True})
    return jsonify({'error': '文章不存在'}), 404


@article_api_bp.route('/articles/rename', methods=['POST'])
def api_rename_article():
    """重命名文章"""
    chapter = request.json.get('chapter', '')
    article_key = request.json.get('key', '')
    new_title = request.json.get('title', '').strip()
    
    if not new_title:
        return jsonify({'error': '标题不能为空'}), 400
    
    folder = get_chapter_folder(chapter)
    if not folder:
        return jsonify({'error': '章节不存在'}), 404
    
    success, error = rename_article(folder, article_key, new_title)
    if not success:
        return jsonify({'error': error}), 400
    invalidate_chapter_cache()
    return jsonify({'ok': True})


@article_api_bp.route('/articles/move', methods=['POST'])
def api_move_article():
    """移动文章到另一个章节"""
    source_chapter = request.json.get('chapter', '')
    target_chapter = request.json.get('target_chapter', '').strip()
    article_key = request.json.get('key', '')
    
    if not source_chapter or not target_chapter or not article_key:
        return jsonify({'error': '参数不完整'}), 400
    if source_chapter == target_chapter:
        return jsonify({'error': '目标章节与当前章节相同'}), 400
    
    source_folder = get_chapter_folder(source_chapter)
    target_folder = get_chapter_folder(target_chapter)
    
    if not source_folder or not target_folder:
        return jsonify({'error': '章节不存在'}), 404
    
    success, error, new_key = move_article(source_folder, target_folder, article_key)
    if not success:
        return jsonify({'error': error}), 404
    invalidate_chapter_cache()
    return jsonify({'ok': True, 'new_key': new_key, 'target_chapter': target_chapter})


@article_api_bp.route('/article/save', methods=['POST'])
def api_save_article():
    """保存文章"""
    chapter = request.json.get('chapter')
    content = request.json.get('content')
    article_key = request.json.get('article_key', '')
    author = request.json.get('author', '')
    
    folder = get_chapter_folder(chapter)
    if not folder:
        return jsonify({'error': '章节不存在'}), 404
    
    success, md_name = save_article(folder, article_key, content, author)
    invalidate_chapter_cache()
    return jsonify({'ok': True, 'md_name': md_name})
