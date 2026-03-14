# ZSPIDER

[![Documentation Status](https://readthedocs.org/projects/zspider/badge/?version=latest)](http://zspider.readthedocs.org/en/latest/?badge=latest)

A self-hosted crawling platform for **content monitoring and news aggregation**.

ZSpider is built for continuously collecting public web content such as news sites, announcements, WeChat articles, and other information sources. You manage jobs in a web dashboard, configure extraction rules, schedule crawls, and review results in one place.

[中文说明](README.md)

---

## What ZSpider is

ZSpider is not just a crawler code scaffold. It is a more platform-oriented system for operating recurring collection workflows:

- manage crawl jobs from a **web dashboard** instead of scattered scripts
- run **scheduled monitoring** with Cron rather than manual execution
- extract structured data through **configurable parsers**
- review and manage results through a **centralized backend**

Typical use cases include:
- news and article aggregation
- public announcement monitoring
- company website update tracking
- WeChat content collection
- continuous gathering of public information for research and intelligence work

---

## Features

- 🕷️ **Platform-oriented crawling** - built for content monitoring and information aggregation
- ⏰ **Cron Scheduling** - APScheduler-based timed tasks
- 🌐 **Web Management** - Flask admin dashboard for managing jobs, fields, and results
- 📦 **Configurable Parsing** - XPath + Regex extraction without coding
- 🔐 **Login Support** - Automatic handling of login-required websites
- 🔄 **Deduplication** - Memcached-based distributed URL deduplication
- 🚚 **Scalable Architecture** - decoupled Dispatcher / Crawler design with horizontal scaling

---

## Use Cases

| Use Case | Description |
|----------|-------------|
| News Monitoring | Periodically crawl media sites for aggregation and topic tracking |
| Announcement Tracking | Monitor government, school, or company websites for updates |
| WeChat Collection | Collect article indexes and detail pages from public accounts |
| Research / Intel Gathering | Continuously gather public information for analysis workflows |
| Self-hosted Content Ops | Centralize crawl jobs, parser rules, and result review in one system |

---

## Why not plain crawler scripts

When a crawler evolves from a one-off script into an ongoing collection workflow, teams usually run into the same problems:

- jobs are scattered across scripts and hard to manage
- scheduling depends on ad-hoc crontab or supervisor setups
- parser changes lack a unified execution and review flow
- logs, status, and results become messy when multiple sites run in parallel

ZSpider is not trying to replace every crawler development style. Its goal is to make **recurring crawling + scheduled monitoring + result management** easier to operate as a platform.

---

## Quick Start

### 1. Clone the project

```bash
git clone https://github.com/Zephor5/zspider.git
cd zspider
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start external services

```bash
docker compose -f docker-compose.services.yml up -d
```

### 4. Start ZSpider components

```bash
python -m zspider.dispatcher
python -m zspider.crawler
python -m zspider.web
```

> For environment requirements, configuration details, components, parser model, pipelines, and project structure, see `docs/` or Read the Docs.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ZSpider System                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐      ┌──────────────┐                    │
│   │  Dispatcher  │◄────►│  Dispatcher  │  (Hot standby)     │
│   │   (Master)   │      │   (Backup)   │                    │
│   └──────┬───────┘      └──────────────┘                    │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────┐                                          │
│   │   RabbitMQ   │  Task Queue                              │
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
│   │   MongoDB    │  Data Storage                            │
│   └──────────────┘                                          │
│                                                             │
│   ┌──────────────┐                                          │
│   │  Memcached   │  Heartbeat + Deduplication               │
│   └──────────────┘                                          │
│                                                             │
│   ┌──────────────┐                                          │
│   │  Web Admin   │  Management Dashboard                    │
│   └──────────────┘                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Further Reading for Developers

- [Developer Guide](docs/developer_guide.rst): requirements, configuration, core components, parsers, pipelines, project structure
- [Desgin](docs/desgin.rst): architecture design notes
- [Internal Message](docs/internal_message.rst): internal messaging details
- [Item Info](docs/item_info.rst): item and field model reference

Build docs with Sphinx:

```bash
cd docs
make html
```

Or visit [ReadTheDocs](http://zspider.readthedocs.org/)

---

## License

MIT License

---

## Contributing

Issues and Pull Requests are welcome!
