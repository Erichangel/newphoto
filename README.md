# 时光印记 v1.0

一个简洁优雅的本地照片回忆管理工具，帮助你整理和浏览珍贵的照片记忆。

## 功能特点

- **章节管理**: 每个子文件夹自动成为一个章节，按时间线展示
- **图片/视频支持**: 支持 JPG、PNG、GIF、WebP 等图片格式，MP4、WebM 等视频格式
- **缩略图生成**: 自动生成封面缩略图，提升浏览体验
- **Markdown 文章**: 每个章节可添加 Markdown 格式的回忆文章
- **继续回忆**: 记住上次浏览位置，下次打开可快速继续
- **滚动位置记忆**: 返回首页时保持之前的浏览位置

## 快速开始

### 环境要求

- Python 3.7+
- pip

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/Erichangel/newphoto.git
cd newphoto
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

或者双击运行 `install.bat`

3. 配置照片目录

编辑 `app.py` 文件，修改 `ROOT_DIR` 变量为你的照片文件夹路径：
```python
ROOT_DIR = r'K:\Pictures\照片库'  # 改成你的照片总文件夹路径
```

4. 启动应用
```bash
python app.py
```

或者双击运行 `start.bat`

5. 打开浏览器访问 `http://localhost:5000`

## 目录结构

```
照片库/
├── 2023年春节/          # 章节文件夹
│   ├── photo1.jpg       # 照片
│   ├── photo2.jpg
│   ├── video.mp4        # 视频
│   └── 2023年春节.md    # 回忆文章（可选）
├── 2023年暑假/
│   └── ...
└── 2024年新年/
    └── ...
```

## API 接口

- `GET /` - 首页，章节列表
- `GET /chapter/<name>` - 章节详情页
- `GET /thumb/<filename>` - 获取缩略图
- `GET /file/<path>` - 获取原始文件
- `POST /api/chapter/create` - 创建章节
- `POST /api/chapter/rename` - 重命名章节
- `POST /api/chapter/delete` - 删除章节
- `POST /api/file/upload` - 上传文件
- `POST /api/file/rename` - 重命名文件
- `POST /api/file/delete` - 删除文件
- `POST /api/article/save` - 保存文章
- `GET/POST /api/settings` - 获取/修改设置

## 技术栈

- **后端**: Flask
- **前端**: HTML/CSS/JavaScript
- **图片处理**: Pillow
- **存储**: 本地文件系统

## 版本历史

### v1.0
- 初始版本发布
- 章节管理功能
- 图片/视频浏览
- Markdown 文章支持
- 继续回忆功能
- 滚动位置记忆

## 许可证

MIT License
