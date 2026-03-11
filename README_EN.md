# ZSPIDER

[![Documentation Status](https://readthedocs.org/projects/zspider/badge/?version=latest)](http://zspider.readthedocs.org/en/latest/?badge=latest)

A distributed cron spider system

[中文说明](README.md)

---

## Features

- 🕷️ **Distributed Architecture** - Dispatcher hot-standby, Crawler horizontal scaling
- ⏰ **Cron Scheduling** - APScheduler-based timed tasks
- 🌐 **Web Management** - Flask admin dashboard for task management
- 📦 **Configurable Parsing** - XPath + Regex extraction without coding
- 🔐 **Login Support** - Automatic handling of login-required websites
- 🔄 **Deduplication** - Memcached-based distributed URL deduplication

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ZSpider System                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐      ┌──────────────┐                    │
│   │  Dispatcher  │◄────►│  Dispatcher  │  (Hot standby)     │
│   │   (Master)   │      │   (Backup)   │                    │
│   └──────┬───────┘      └──────────────┘                    │
│          │                                                    │
│          ▼                                                    │
│   ┌──────────────┐                                           │
│   │   RabbitMQ   │  Task Queue                               │
│   └──────┬───────┘                                           │
│          │                                                    │
│          ▼                                                    │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│   │   Crawler    │   │   Crawler    │   │   Crawler    │    │
│   │   (Worker)   │   │   (Worker)   │   │   (Worker)   │    │
│   └──────┬───────┘   └──────────────┘   └──────────────┘    │
│          │                                                    │
│          ▼                                                    │
│   ┌──────────────┐                                           │
│   │   MongoDB    │  Data Storage                             │
│   └──────────────┘                                           │
│                                                              │
│   ┌──────────────┐                                           │
│   │  Memcached   │  Heartbeat + Deduplication                │
│   └──────────────┘                                           │
│                                                              │
│   ┌──────────────┐                                           │
│   │  Web Admin   │  Management Dashboard                     │
│   └──────────────┘                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Requirements

### Python Version
- Python 3.7
- Python 3.8
- Python 3.9

### External Dependencies
| Service | Purpose | Default Port |
|---------|---------|--------------|
| RabbitMQ | Task Queue | 5672 |
| MongoDB | Data Storage | 27017 |
| Memcached | Heartbeat + Deduplication | 11211 |

---

## Quick Start

### 1. Clone the Project

```bash
git clone https://github.com/Zephor5/zspider.git
cd zspider
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start External Services

Using Docker for quick setup:

```bash
# Start RabbitMQ
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management

# Start MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:4.4

# Start Memcached
docker run -d --name memcached -p 11211:11211 memcached:alpine
```

### 4. Configuration

Modify configuration files in `zspider/confs/`:

**conf.py** - Core configuration:
```python
# Development mode
DEBUG = True

# RabbitMQ connection
AMQP_PARAM = URLParameters("amqp://guest:guest@127.0.0.1")

# Memcached servers
MC_SERVERS = "127.0.0.1:11211"
```

**web_conf.py** - Web backend configuration:
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

### 5. Start Services

```bash
# Start Dispatcher (Task Scheduler)
python -m zspider.dispatcher

# Start Crawler (Worker Process)
python -m zspider.crawler

# Start Web Admin
python -m zspider.web
```

Or using Docker:

```bash
docker-compose up -d
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `conf.py` | Core config (MQ, MC, logging, etc.) |
| `crawl_conf.py` | Scrapy crawler settings |
| `dispatcher_conf.py` | Dispatcher scheduler config |
| `web_conf.py` | Flask web config |

### Production Configuration

Set environment variable for production mode:

```bash
export ZSPIDER_PRODUCT=1
```

Then update production parameters in each config file.

---

## Core Components

### Dispatcher - Task Scheduler

- APScheduler-based Cron scheduling
- Multi-node deployment with automatic failover
- Heartbeat detection via Memcached
- Hot reload, pause, and delete tasks

**Management API:**
```
GET /{MANAGE_KEY}              # Get status
GET /reload/{MANAGE_KEY}       # Reload all tasks
GET /load/{task_id}/{MANAGE_KEY}   # Load specific task
GET /pause/{task_id}/{MANAGE_KEY}  # Pause task
GET /remove/{task_id}/{MANAGE_KEY} # Remove task
```

### Crawler - Worker Process

- Built on Scrapy framework
- Fetches tasks from RabbitMQ
- Multiple Spider types supported
- Built-in Pipeline processing

### Web - Admin Dashboard

- Flask + MongoEngine
- Frontend: **Ace Admin** template (Bootstrap responsive admin)
- Task CRUD management
- Visual field configuration
- Result viewing
- User permission management

**Pages:**
| Page | Function |
|------|----------|
| Dashboard | Dispatcher status monitoring |
| Task List | View/manage all tasks |
| Add Task | Create new crawl task |
| Data Records | View crawl results |
| Logs | Crawler/Dispatcher logs |

---

## Spider Types

| Spider | Purpose | File |
|--------|---------|------|
| `news` | News websites | `spiders/news.py` |
| `wechat` | WeChat articles | `spiders/wechat.py` |
| `selenium` | Dynamic rendering | `spiders/selenium.py` |

### Custom Spider

Extend `BaseSpider` to create your own:

```python
from zspider.basespider import BaseSpider

class MySpider(BaseSpider):
    name = "myspider"
    
    def parse(self, response):
        # Parse index page
        for item in self._parse_index(response):
            yield item
```

---

## Parser Configuration

Parser handles extraction logic with XPath + Regex:

```python
# Task configuration example
task = Task(
    name="News Crawler",
    spider="news",
    parser="news",
    cron="0 */2 * * *",  # Every 2 hours
    is_active=True,
)

# Field extraction configuration
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

## Pipeline Processing

| Pipeline | Function |
|----------|----------|
| `CappedStorePipeLine` | Store to MongoDB (capped collection) |
| `PubPipeLine` | Publish to external systems |
| `TestResultPipeLine` | Test mode result collection |

---

## Development Tool

Install [dev](https://github.com/wish/dev) tool:

```bash
pip install dev
```

Run in project directory:

```bash
dev zspider
```

---

## Documentation

Build with Sphinx:

```bash
cd docs
make html
```

Or visit [ReadTheDocs](http://zspider.readthedocs.org/)

---

## Project Structure

```
zspider/
├── zspider/
│   ├── spiders/          # Spider implementations
│   │   ├── news.py       # News spider
│   │   ├── wechat.py     # WeChat spider
│   │   └── selenium.py   # Dynamic rendering spider
│   ├── parsers/          # Parsers
│   │   ├── baseparser.py # Base parser
│   │   ├── jsonparser.py # JSON parser
│   │   ├── wechat.py     # WeChat parser
│   │   └── papers.py     # Paper parser
│   ├── pipelines/        # Data pipelines
│   │   ├── store.py      # MongoDB storage
│   │   └── publish.py    # Publish pipeline
│   ├── middlewares/      # Scrapy middlewares
│   ├── utils/            # Utilities
│   ├── www/              # Web admin
│   │   ├── handlers/     # Request handlers
│   │   └── templates/    # Templates
│   ├── confs/            # Configuration files
│   ├── models.py         # Data models
│   ├── crawler.py        # Crawler entry
│   ├── dispatcher.py     # Dispatcher entry
│   └── web.py            # Web entry
├── utests/               # Unit tests
├── docs/                 # Sphinx docs
├── requirements.txt      # Dependencies
├── Dockerfile            # Docker build
└── docker-compose.yml    # Docker Compose
```

---

## License

MIT License

---

## Contributing

Issues and Pull Requests are welcome!