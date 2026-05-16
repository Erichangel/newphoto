"""
时光印记 - 配置模块
管理应用配置、常量、路径等
"""
import os
import time
import hashlib
import json
import csv

# Flask secret key
SECRET_KEY = 'time-imprint-secret-key-2024'

# 默认目录配置
DEFAULT_ROOT_DIR = r'K:\Pictures\照片库'
DEFAULT_MUSIC_DIR = r'K:\Pictures\音乐'

# 支持的文件类型
SUPPORTED_IMAGE = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
SUPPORTED_VIDEO = {'.mp4', '.webm', '.mov', '.avi', '.mkv'}
SUPPORTED_AUDIO = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}

# 缓存配置
CACHE_DURATION = 3600  # 缓存时间（秒）

# MIME 类型映射
MIME_IMAGE = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.gif': 'image/gif', '.webp': 'image/webp',
}
MIME_VIDEO = {
    '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
    '.avi': 'video/x-msvideo', '.mkv': 'video/x-matroska',
}
MIME_AUDIO = {
    '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4', '.flac': 'audio/flac', '.aac': 'audio/aac',
}

# 基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMB_DIR = os.path.join(BASE_DIR, '_thumbs')
USER_DATA_FILE = os.path.join(BASE_DIR, 'users.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.txt')

# 全局配置目录（存储所有照片根目录的独立配置）
ROOT_CONFIGS_DIR = os.path.join(BASE_DIR, 'root_configs')
os.makedirs(ROOT_CONFIGS_DIR, exist_ok=True)

# 确保缩略图目录存在
os.makedirs(THUMB_DIR, exist_ok=True)


def get_root_hash(root_dir):
    """根据照片根目录路径生成唯一哈希标识"""
    return hashlib.md5(root_dir.encode('utf-8')).hexdigest()[:12]


def get_root_config_dir(root_dir):
    """获取指定照片根目录的独立配置目录"""
    config_dir = os.path.join(ROOT_CONFIGS_DIR, get_root_hash(root_dir))
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_chapter_covers_file(root_dir):
    """获取章节封面配置文件路径（按照片根目录独立）"""
    return os.path.join(get_root_config_dir(root_dir), 'chapter_covers.json')


def get_chapter_file_order_file(root_dir):
    """获取章节文件排序文件路径（按照片根目录独立）"""
    return os.path.join(get_root_config_dir(root_dir), 'chapter_file_orders.json')


def get_chapter_music_file(root_dir):
    """获取章节音乐配置文件路径（按照片根目录独立）"""
    return os.path.join(get_root_config_dir(root_dir), 'chapter_music.csv')


def get_music_config_file(root_dir):
    """获取音乐播放器配置文件路径（按照片根目录独立）"""
    return os.path.join(get_root_config_dir(root_dir), 'music_config.json')


def migrate_old_configs_to_root(root_dir):
    """将旧的全局配置文件迁移到照片根目录的独立配置目录"""
    config_dir = get_root_config_dir(root_dir)
    
    # 迁移章节封面
    old_covers = os.path.join(BASE_DIR, 'chapter_covers.json')
    new_covers = get_chapter_covers_file(root_dir)
    if os.path.exists(old_covers) and not os.path.exists(new_covers):
        try:
            import shutil
            shutil.copy2(old_covers, new_covers)
        except Exception:
            pass
    
    # 迁移文件排序
    old_orders = os.path.join(BASE_DIR, 'chapter_file_orders.json')
    new_orders = get_chapter_file_order_file(root_dir)
    if os.path.exists(old_orders) and not os.path.exists(new_orders):
        try:
            import shutil
            shutil.copy2(old_orders, new_orders)
        except Exception:
            pass
    
    # 迁移章节音乐
    old_music = os.path.join(BASE_DIR, 'chapter_music.csv')
    new_music = get_chapter_music_file(root_dir)
    if os.path.exists(old_music) and not os.path.exists(new_music):
        try:
            import shutil
            shutil.copy2(old_music, new_music)
        except Exception:
            pass


class AppConfig:
    """应用运行时配置"""
    
    def __init__(self):
        self.root_dir = DEFAULT_ROOT_DIR
        self.music_dir = DEFAULT_MUSIC_DIR
        self.chapter_cache = {}
        self.cache_timestamp = 0
    
    def load_from_file(self):
        """从 config.txt 加载配置"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                lines = f.read().strip().splitlines()
                if lines:
                    path = lines[0].strip().replace('\\\\', '\\')
                    if os.path.isdir(path):
                        self.root_dir = path
                if len(lines) > 1:
                    path = lines[1].strip().replace('\\\\', '\\')
                    if os.path.isdir(path):
                        self.music_dir = path
        
        # 迁移旧配置到新位置
        migrate_old_configs_to_root(self.root_dir)
    
    def save_to_file(self):
        """保存配置到 config.txt"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(self.root_dir + '\n' + self.music_dir)
    
    def set_root_dir(self, new_root_dir):
        """切换照片根目录"""
        self.root_dir = new_root_dir
        self.save_to_file()
        # 为新目录创建配置目录
        get_root_config_dir(new_root_dir)
        # 刷新缓存
        self.chapter_cache = {}
        self.cache_timestamp = 0


# 全局配置实例
config = AppConfig()


def load_config():
    """从 config.txt 加载配置"""
    config.load_from_file()
