# ZSPIDER

[![Documentation Status](https://readthedocs.org/projects/zspider/badge/?version=latest)](http://zspider.readthedocs.org/en/latest/?badge=latest)

一个分布式的定时抓站系统

[English README](README_EN.md)

---

## 特性

- 🕷️ **分布式架构** - Dispatcher 多节点热备，Crawler 可横向扩展
- ⏰ **定时调度** - 基于 APScheduler 的 Cron 定时任务
- 🌐 **Web 管理** - Flask 后台可视化管理任务
- 📦 **可配置解析** - XPath + 正则表达式配置化提取
- 🔐 **登录支持** - 自动处理需要登录的网站
- 🔄 **去重机制** - 基于 Memcached 的分布式 URL 去重

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        ZSpider 系统                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐      ┌──────────────┐                    │
│   │  Dispatcher  │◄────►│  Dispatcher  │  (主备热切换）       │
│   │   (主节点)    │      │   (备节点)    │                    │
│   └──────┬───────┘      └──────────────┘                    │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────┐                                          │
│   │   RabbitMQ   │  任务队列                                  │
│   └──────┬───────┘                                          │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│   │   Crawler    │   │   Crawler    │   │   Crawler    │    │
│   │   (Worker)   │   │   (Worker)   │   │   (Worker)   │    │
│   └──────┬───────┘   └──────────────┘   └──────────────┘    │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────┐                                          │
│   │   MongoDB    │  数据存储                                  │
│   └──────────────┘                                          │
│                                                             │
│   ┌──────────────┐                                          │
│   │  Memcached   │  心跳 + 去重                               │
│   └──────────────┘                                          │
│                                                             │
│   ┌──────────────┐                                          │
│   │  Web Admin   │  管理后台                                  │
│   └──────────────┘                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 环境要求

### Python 版本
- Python 3.7
- Python 3.8
- Python 3.9

> ⚠️ 不建议使用 Python 3.10+ 直接运行本项目。项目中的 `pooled-pika~=0.3.0`、`flask-mongoengine~=1.0.0` 等老依赖在高版本 Python 上兼容性较差。

### 推荐开发环境

推荐使用 **pyenv + Python 3.9 + 项目独立 `.venv`**：

```bash
pyenv install 3.9.20
pyenv local 3.9.20
python -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements_dev.txt
```

如果已经存在 `.venv`，建议在切换 Python 版本后重建一次，避免旧解释器残留。

### 外部依赖
| 服务 | 用途 | 默认端口 |
|------|------|----------|
| RabbitMQ | 任务队列 | 5672 |
| MongoDB | 数据存储 | 27017 |
| Memcached | 心跳检测 + URL去重 | 11211 |

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Zephor5/zspider.git
cd zspider
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动外部服务

使用项目内的 Docker Compose 配置启动：

```bash
docker compose -f docker-compose.services.yml up -d
```

查看状态：

```bash
docker compose -f docker-compose.services.yml ps
```

### 4. 配置修改

修改 `zspider/confs/` 目录下的配置文件：

**conf.py** - 核心配置：
```python
# 开发模式
DEBUG = True

# RabbitMQ 连接
AMQP_PARAM = URLParameters("amqp://guest:guest@127.0.0.1")

# Memcached 服务器
MC_SERVERS = "127.0.0.1:11211"
```

**web_conf.py** - Web 后台配置：
```python
FLASK_CONF = {
    "SECRET_KEY": "your-secret-key",
    "MONGODB_SETTINGS": {
        "db": "spider",
        "host": "localhost",
        "port": 27017,
    },
}
```

### 5. 启动服务

```bash
# 启动 Dispatcher (任务调度)
python -m zspider.dispatcher

# 启动 Crawler (抓取工作进程)
python -m zspider.crawler

# 启动 Web 管理后台
python -m zspider.web
```

停止外部服务：

```bash
docker compose -f docker-compose.services.yml down
```

---

## 配置文件说明

| 文件 | 用途 |
|------|------|
| `conf.py` | 核心配置（MQ、MC、日志等） |
| `crawl_conf.py` | Scrapy 爬虫配置 |
| `dispatcher_conf.py` | Dispatcher 调度器配置 |
| `web_conf.py` | Flask Web 配置 |

### 生产环境配置

设置环境变量启用生产模式：

```bash
export ZSPIDER_PRODUCT=1
```

然后修改各配置文件中的生产环境参数。

---

## 核心组件

### Dispatcher - 任务调度中心

- 基于 APScheduler 的 Cron 调度
- 多节点部署，自动主备切换
- 通过 Memcached 实现心跳检测
- 支持任务热加载、暂停、删除

**管理接口：**
```
GET /{MANAGE_KEY}              # 查看状态
GET /reload/{MANAGE_KEY}       # 重载所有任务
GET /load/{task_id}/{MANAGE_KEY}   # 加载指定任务
GET /pause/{task_id}/{MANAGE_KEY}  # 暂停任务
GET /remove/{task_id}/{MANAGE_KEY} # 删除任务
```

### Crawler - 抓取工作进程

- 基于 Scrapy 框架
- 从 RabbitMQ 获取任务
- 支持多种 Spider 类型
- 内置 Pipeline 处理

### Web - 管理后台

- Flask + MongoEngine
- 前端：**Ace Admin** 模板（Bootstrap 响应式后台）
- 任务管理 CRUD
- 字段配置可视化
- 抓取结果查看
- 用户权限管理

**页面功能：**
| 页面 | 功能 |
|------|------|
| Dashboard | 调度中心状态监控 |
| 任务列表 | 查看/管理所有任务 |
| 添加任务 | 创建新抓取任务 |
| 数据记录 | 查看抓取结果 |
| 日志记录 | Crawler/Dispatcher 日志 |
| 用户管理 | 用户 CRUD（需 admin 权限） |

---

## Spider 类型

| Spider | 用途 | 文件 |
|--------|------|------|
| `news` | 新闻网站 | `spiders/news.py` |
| `wechat` | 微信公众号 | `spiders/wechat.py` |
| `selenium` | 动态渲染页面 | `spiders/selenium.py` |

### 自定义 Spider

继承 `BaseSpider` 实现自己的爬虫：

```python
from zspider.basespider import BaseSpider

class MySpider(BaseSpider):
    name = "myspider"
    
    def parse(self, response):
        # 解析索引页
        for item in self._parse_index(response):
            yield item
```

---

## Parser 配置

Parser 负责解析逻辑，支持 XPath + 正则表达式配置：

```python
# 任务字段配置示例
task = Task(
    name="新闻抓取",
    spider="news",
    parser="news",
    cron="0 */2 * * *",  # 每2小时执行
    is_active=True,
)

# 字段提取配置
ArticleField(
    task=task,
    name="title",
    xpath="//h1/text()",
)
ArticleField(
    task=task,
    name="content",
    xpath="//div[@class='content']//text()",
)
ArticleField(
    task=task,
    name="src_time",
    xpath="//span[@class='date']/text()",
    re=r"(\d{4}-\d{2}-\d{2})",
)
```

---

## Pipeline 处理

| Pipeline | 功能 |
|----------|------|
| `CappedStorePipeLine` | 存储到 MongoDB (固定大小集合) |
| `PubPipeLine` | 发布到外部系统 |
| `TestResultPipeLine` | 测试模式结果收集 |

---

## API 文档

完整文档使用 Sphinx 构建：

```bash
cd docs
make html
```

或访问 [ReadTheDocs](http://zspider.readthedocs.org/)

---

## 项目结构

```
zspider/
├── zspider/
│   ├── spiders/          # 爬虫实现
│   │   ├── news.py       # 新闻爬虫
│   │   ├── wechat.py     # 微信爬虫
│   │   └── selenium.py   # 动态渲染爬虫
│   ├── parsers/          # 解析器
│   │   ├── baseparser.py # 基础解析器
│   │   ├── jsonparser.py # JSON解析
│   │   ├── wechat.py     # 微信解析
│   │   └── papers.py     # 论文解析
│   ├── pipelines/        # 数据管道
│   │   ├── store.py      # MongoDB存储
│   │   └── publish.py    # 发布管道
│   ├── middlewares/      # Scrapy中间件
│   ├── utils/            # 工具类
│   ├── www/              # Web管理后台
│   │   ├── handlers/     # 请求处理
│   │   └── templates/    # 模板文件
│   ├── confs/            # 配置文件
│   ├── models.py         # 数据模型
│   ├── crawler.py        # Crawler入口
│   ├── dispatcher.py     # Dispatcher入口
│   └── web.py            # Web入口
├── utests/               # 单元测试
├── docs/                 # Sphinx文档
├── requirements.txt      # 依赖列表
├── Dockerfile            # Docker构建
└── docker-compose.yml    # Docker Compose
```

---

## License

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！
