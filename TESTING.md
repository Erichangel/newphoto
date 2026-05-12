# 时光印记 - 测试文档

## 📋 测试策略

### 测试金字塔
```
        /\
       /  \
      / E2E \       端到端测试 (10%)
     /--------\    
    /          \   集成测试 (30%)
   /------------\  
  /              \ 单元测试 (60%)
 /----------------\
```

---

## 🧪 单元测试

### 环境搭建

#### 1. 安装测试依赖
```bash
pip install pytest pytest-cov pytest-flask
```

#### 2. 项目结构
```
时光印记/
├── app.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # pytest 配置
│   ├── test_chapters.py  # 章节测试
│   ├── test_files.py     # 文件测试
│   ├── test_music.py     # 音乐测试
│   └── test_articles.py  # 文章测试
└── test_requirements.txt
```

---

### 测试用例设计

#### 章节管理测试 (`test_chapters.py`)

```python
import pytest
import os
import shutil
from app import app, create_test_config

@pytest.fixture
def client():
    """测试客户端"""
    app.config['TESTING'] = True
    app.config['ROOT_DIR'] = './test_data'
    with app.test_client() as client:
        yield client

@pytest.fixture
def test_chapter():
    """创建测试章节"""
    chapter_path = './test_data/测试章节'
    os.makedirs(chapter_path, exist_ok=True)
    yield chapter_path
    shutil.rmtree('./test_data', ignore_errors=True)

def test_get_chapters_empty(client):
    """测试空章节列表"""
    response = client.get('/api/chapters')
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] == True
    assert isinstance(data['chapters'], list)

def test_get_chapters_with_data(client, test_chapter):
    """测试有数据的章节列表"""
    response = client.get('/api/chapters')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['chapters']) >= 1
    assert any(c['name'] == '测试章节' for c in data['chapters'])

def test_create_chapter_success(client):
    """测试创建章节成功"""
    response = client.post('/api/chapter/create', json={
        'name': '新章节'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] == True
    assert os.path.exists('./test_data/新章节')

def test_create_chapter_duplicate(client):
    """测试创建重复章节"""
    client.post('/api/chapter/create', json={'name': '重复章节'})
    response = client.post('/api/chapter/create', json={'name': '重复章节'})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_rename_chapter(client, test_chapter):
    """测试重命名章节"""
    response = client.post('/api/chapter/rename', json={
        'old_name': '测试章节',
        'new_name': '重命名章节'
    })
    assert response.status_code == 200
    assert os.path.exists('./test_data/重命名章节')
    assert not os.path.exists('./test_data/测试章节')

def test_delete_chapter(client, test_chapter):
    """测试删除章节"""
    response = client.post('/api/chapter/delete', json={
        'name': '测试章节'
    })
    assert response.status_code == 200
    assert not os.path.exists('./test_data/测试章节')
```

---

#### 文件管理测试 (`test_files.py`)

```python
import pytest
from PIL import Image
import io

def create_test_image():
    """创建测试图片"""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes

def test_upload_image(client, test_chapter):
    """测试上传图片"""
    data = {
        'file': (create_test_image(), 'test.jpg'),
        'chapter': '测试章节'
    }
    response = client.post('/api/file/upload', data=data)
    assert response.status_code == 200
    assert os.path.exists('./test_data/测试章节/test.jpg')

def test_upload_video(client, test_chapter):
    """测试上传视频"""
    # 创建假视频文件
    video_data = b'fake video content'
    data = {
        'file': (io.BytesIO(video_data), 'test.mp4'),
        'chapter': '测试章节'
    }
    response = client.post('/api/file/upload', data=data)
    assert response.status_code == 200

def test_upload_invalid_type(client, test_chapter):
    """测试上传不支持的文件类型"""
    data = {
        'file': (io.BytesIO(b'fake'), 'test.txt'),
        'chapter': '测试章节'
    }
    response = client.post('/api/file/upload', data=data)
    assert response.status_code == 400

def test_get_thumbnail(client, test_chapter):
    """测试获取缩略图"""
    # 先上传图片
    create_test_image()
    client.post('/api/file/upload', data={
        'file': (create_test_image(), 'thumb_test.jpg'),
        'chapter': '测试章节'
    })
    
    # 获取缩略图
    response = client.get('/thumb/thumb_test.jpg')
    assert response.status_code == 200
    assert response.content_type.startswith('image/')
```

---

#### 音乐管理测试 (`test_music.py`)

```python
import pytest
import json

def test_get_music_list_empty(client):
    """测试空音乐列表"""
    response = client.get('/api/music/list')
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] == True
    assert data['musics'] == []

def test_get_chapter_music_not_set(client):
    """测试章节未设置音乐"""
    response = client.get('/api/chapter/music?chapter=测试章节')
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] == True
    assert data['music'] == ''

def test_set_chapter_music(client):
    """测试设置章节音乐"""
    response = client.post('/api/chapter/music', json={
        'chapter': '测试章节',
        'music': 'test.mp3'
    })
    assert response.status_code == 200
    assert data['ok'] == True
    
    # 验证读取
    response = client.get('/api/chapter/music?chapter=测试章节')
    data = response.get_json()
    assert data['music'] == 'test.mp3'

def test_set_chapter_no_music(client):
    """测试设置章节不播放音乐"""
    response = client.post('/api/chapter/music', json={
        'chapter': '测试章节',
        'music': '__none__'
    })
    assert response.status_code == 200
    
    response = client.get('/api/chapter/music?chapter=测试章节')
    data = response.get_json()
    assert data['music'] == '__none__'

def test_clear_chapter_music(client):
    """测试清除章节音乐设置"""
    # 先设置
    client.post('/api/chapter/music', json={
        'chapter': '测试章节',
        'music': 'test.mp3'
    })
    
    # 再清除
    response = client.post('/api/chapter/music', json={
        'chapter': '测试章节',
        'music': ''
    })
    assert response.status_code == 200
    
    # 验证已清除
    response = client.get('/api/chapter/music?chapter=测试章节')
    data = response.get_json()
    assert data['music'] == ''
```

---

#### 文章管理测试 (`test_articles.py`)

```python
import pytest

def test_get_articles_empty(client, test_chapter):
    """测试空文章列表"""
    response = client.get('/api/articles/list?chapter=测试章节')
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] == True
    assert data['articles'] == []

def test_create_article(client, test_chapter):
    """测试创建文章"""
    response = client.post('/api/articles/create', json={
        'chapter': '测试章节',
        'title': '测试文章',
        'author': '测试作者'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] == True
    assert 'key' in data
    assert 'filename' in data

def test_create_article_empty_title(client):
    """测试创建空标题文章"""
    response = client.post('/api/articles/create', json={
        'chapter': '测试章节',
        'title': ''
    })
    assert response.status_code == 400

def test_save_article(client, test_chapter):
    """测试保存文章"""
    # 先创建
    create_resp = client.post('/api/articles/create', json={
        'chapter': '测试章节',
        'title': '保存测试'
    })
    article_key = create_resp.get_json()['key']
    
    # 再保存
    response = client.post('/api/article/save', json={
        'chapter': '测试章节',
        'article_key': article_key,
        'content': '# 测试内容\n这是测试文章。'
    })
    assert response.status_code == 200
    assert response.get_json()['ok'] == True

def test_get_article_content(client, test_chapter):
    """测试获取文章内容"""
    # 创建并保存
    create_resp = client.post('/api/articles/create', json={
        'chapter': '测试章节',
        'title': '读取测试'
    })
    article_key = create_resp.get_json()['key']
    
    client.post('/api/article/save', json={
        'chapter': '测试章节',
        'article_key': article_key,
        'content': '# 标题\n内容'
    })
    
    # 读取
    response = client.get('/api/articles/get?chapter=测试章节&key=' + article_key)
    data = response.get_json()
    assert data['ok'] == True
    assert '内容' in data['content']
```

---

## 🔗 集成测试

### 章节完整流程测试

```python
class TestChapterWorkflow:
    """章节完整工作流测试"""
    
    def test_full_workflow(self, client):
        """测试完整章节管理流程"""
        # 1. 创建章节
        create_resp = client.post('/api/chapter/create', json={
            'name': '工作流测试'
        })
        assert create_resp.status_code == 200
        
        # 2. 上传图片
        upload_resp = client.post('/api/file/upload', data={
            'file': (create_test_image(), 'photo1.jpg'),
            'chapter': '工作流测试'
        })
        assert upload_resp.status_code == 200
        
        # 3. 创建文章
        article_resp = client.post('/api/articles/create', json={
            'chapter': '工作流测试',
            'title': '测试文章'
        })
        assert article_resp.status_code == 200
        
        # 4. 设置章节音乐
        music_resp = client.post('/api/chapter/music', json={
            'chapter': '工作流测试',
            'music': 'test.mp3'
        })
        assert music_resp.status_code == 200
        
        # 5. 获取章节详情
        detail_resp = client.get('/api/chapter/detail?name=工作流测试')
        assert detail_resp.status_code == 200
        data = detail_resp.get_json()
        assert data['image_count'] == 1
        assert data['article_count'] >= 1
        
        # 6. 重命名章节
        rename_resp = client.post('/api/chapter/rename', json={
            'old_name': '工作流测试',
            'new_name': '重命名测试'
        })
        assert rename_resp.status_code == 200
        
        # 7. 删除章节
        delete_resp = client.post('/api/chapter/delete', json={
            'name': '重命名测试'
        })
        assert delete_resp.status_code == 200
```

---

## 🎭 端到端 (E2E) 测试

### 使用 Selenium

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
import pytest

@pytest.fixture
def browser():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_home_page_load(browser):
    """测试首页加载"""
    browser.get('http://localhost:5000')
    assert '时光印记' in browser.title
    assert len(browser.find_elements(By.CLASS_NAME, 'timeline-node')) > 0

def test_chapter_navigation(browser):
    """测试章节导航"""
    browser.get('http://localhost:5000')
    # 点击第一个章节
    first_chapter = browser.find_element(By.CLASS_NAME, 'timeline-node')
    first_chapter.click()
    # 等待跳转
    WebDriverWait(browser, 10).until(
        lambda d: 'chapter' in d.current_url
    )
    assert 'chapter' in browser.current_url

def test_music_player(browser):
    """测试音乐播放器"""
    browser.get('http://localhost:5000')
    # 检查播放器存在
    player = browser.find_element(By.ID, 'music-player')
    assert player.is_displayed()
```

---

## 📊 性能测试

### 使用 locust

```python
from locust import HttpUser, task, between

class PhotoAppUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def view_home(self):
        self.client.get('/')
    
    @task(2)
    def view_chapter(self):
        self.client.get('/chapter/2017.01')
    
    @task(1)
    def get_thumbnail(self):
        self.client.get('/thumb/test.jpg')
```

运行性能测试：
```bash
locust -f locustfile.py --host=http://localhost:5000
```

---

## 🚀 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定测试文件
```bash
pytest tests/test_chapters.py
```

### 运行特定测试函数
```bash
pytest tests/test_chapters.py::test_create_chapter_success
```

### 生成覆盖率报告
```bash
pytest --cov=app --cov-report=html
```

### 查看覆盖率
```bash
open htmlcov/index.html
```

---

## ✅ 测试检查清单

### 单元测试
- [ ] 章节管理测试
- [ ] 文件管理测试
- [ ] 音乐管理测试
- [ ] 文章管理测试
- [ ] 用户管理测试
- [ ] 配置管理测试

### 集成测试
- [ ] 章节完整流程
- [ ] 文件上传流程
- [ ] 音乐设置流程
- [ ] 文章编辑流程

### E2E 测试
- [ ] 首页加载
- [ ] 章节导航
- [ ] 音乐播放
- [ ] 图片预览
- [ ] 文章编辑

### 性能测试
- [ ] 并发访问测试
- [ ] 缩略图生成性能
- [ ] 大文件上传性能
- [ ] 内存泄漏检测

---

## 📈 测试目标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 单元测试覆盖率 | >70% | 0% |
| 关键路径覆盖率 | 100% | 0% |
| 测试执行时间 | <5 分钟 | N/A |
| CI/CD 通过率 | >95% | N/A |

---

## 🔧 调试技巧

### 1. 测试失败调试
```bash
# 详细输出
pytest -v -s tests/test_chapters.py::test_failed

# 失败后进入调试器
pytest --pdb tests/test_chapters.py
```

### 2. 日志调试
```python
import logging
logging.basicConfig(level=logging.DEBUG)

def test_something():
    logging.debug('调试信息')
```

### 3. 数据库检查
```python
def test_data_persistence():
    import json
    with open('users.json') as f:
        data = json.load(f)
    assert 'test_user' in data
```

---

## 📚 参考资源

- [pytest 官方文档](https://docs.pytest.org/)
- [Flask 测试文档](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [Selenium 文档](https://www.selenium.dev/documentation/)
- [Locust 性能测试](https://locust.io/)

---

*文档版本：1.0*
*最后更新：2026-01-09*
