"""
时光印记 - 配置模块
管理应用配置、常量、路径等
"""
import os
import time

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
MUSIC_CONFIG_FILE = os.path.join(BASE_DIR, 'music_config.json')
CHAPTER_MUSIC_CSV = os.path.join(BASE_DIR, 'chapter_music.csv')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.txt')

# 确保目录存在
os.makedirs(THUMB_DIR, exist_ok=True)


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
                if lines and os.path.isdir(lines[0].strip()):
                    self.root_dir = lines[0].strip()
                if len(lines) > 1 and os.path.isdir(lines[1].strip()):
                    self.music_dir = lines[1].strip()
    
    def save_to_file(self):
        """保存配置到 config.txt"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(self.root_dir + '\n' + self.music_dir)


# 全局配置实例
config = AppConfig()


def load_config():
    """从 config.txt 加载配置"""
    config.load_from_file()
