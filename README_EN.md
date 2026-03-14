# ZSpider

[![CI](https://github.com/Zephor5/zspider/actions/workflows/ci.yml/badge.svg)](https://github.com/Zephor5/zspider/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/zspider/badge/?version=latest)](http://zspider.readthedocs.org/en/latest/?badge=latest)

A self-hosted crawling platform for **content monitoring and news aggregation**.

ZSpider is not just a place to dump crawler scripts. It is a platform-oriented system with a **web admin, scheduling, configurable parsing, and result review**, built for recurring collection workflows such as monitoring news sites, announcements, WeChat articles, and other public web content.

[中文说明](README.md)

---

## What it is good for

ZSpider fits ongoing collection workflows better than one-off scripts:

- **News / content aggregation** across multiple sites
- **Announcement monitoring** for government, school, or company websites
- **WeChat article collection** for archiving or downstream analysis
- **Research / intelligence gathering** from public information sources
- **Self-hosted content operations** with jobs, fields, logs, and results in one backend

If your goal is long-running monitoring rather than a one-time scrape, ZSpider is the better fit.

---

## Core capabilities

- 🕷️ **Platform-style job management** through a web admin
- ⏰ **Scheduled crawling** powered by APScheduler Cron jobs
- 🌐 **Visual backend** for task status, logs, and results
- 📦 **Configurable parsing** with XPath + regex extraction
- 🔐 **Login-aware crawling** for authenticated sites
- 🔄 **Deduplication** backed by Memcached
- 🚚 **Scalable architecture** with decoupled Dispatcher / Crawler components

---

## Why not plain crawler scripts

Once a scraper turns into an always-on monitoring workflow, teams usually hit the same problems:

- jobs are scattered across many scripts
- scheduling depends on ad-hoc crontab or supervisor setups
- parser changes have no single execution path to verify them
- logs, status, and results become fragmented across many places

ZSpider exists to make **recurring crawling + scheduling + result management** easier to operate as a real platform.

---

## 5-minute quick start

### 1) Prepare the environment

Python 3.9 is recommended:

```bash
git clone https://github.com/Zephor5/zspider.git
cd zspider
cp .env.example .env
python3.9 -m venv .venv
./.venv/bin/pip install -U pip setuptools wheel
./.venv/bin/pip install -r requirements_dev.txt -c constraints/py39.txt
```

### 2) Start dependency services

```bash
make services-up
```

This starts:

- MongoDB
- RabbitMQ
- Memcached

### 3) Start the local ZSpider stack

```bash
make dev
```

This unified entry point starts:

- `zspider.dispatcher`
- `zspider.crawler`
- `zspider.web`

Default URL:

```text
http://127.0.0.1:5000
```

### 4) Initialize the admin account

On the first visit to `/login`:

- enter **any username and password**
- if the user table is empty, that credential pair becomes the **initial admin account**

So there is no hard-coded default admin account today. The **first successful login creates the initial admin user**.

### 5) Verify the setup

- open the dashboard and confirm it loads
- log in and verify task pages open normally
- inspect `logs/web.log`, `logs/dispatcher.log`, and `logs/crawler.log` for errors

Stop everything with:

```bash
# Ctrl + C stops the local processes started by make dev
make services-down
```

---

## Unified local development flow

To reduce first-run friction, the repository now provides one local entry point:

```bash
make dev
```

It will:

1. bring up dependency services from `docker-compose.services.yml`
2. start dispatcher / crawler / web from the repo `.venv`
3. write logs to `logs/dispatcher.log`, `logs/crawler.log`, and `logs/web.log`

If you only want the dependency services:

```bash
make services-up
```

If you only want tests:

```bash
make test
```

---

## Basic trust signals

For phase one, the goal is to improve the fastest trust-building signals:

- **GitHub Actions CI** added for unit tests
- the repository currently includes **27 unit tests**, runnable via `make test`
- `docs/` remains available as the deeper developer documentation entry
- README now covers positioning, use cases, quick start, admin initialization, and the unified startup path

Still worth adding later:

- dashboard screenshots / GIFs
- more realistic task templates
- clearer production deployment docs
- better health / observability docs

---

## System architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                        ZSpider System                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Dispatcher  →  RabbitMQ  →  Crawler Workers              │
│        │                               │                    │
│        └──────── status / control ─────┘                    │
│                                                             │
│   MongoDB   stores tasks and crawl results                  │
│   Memcached heartbeat and deduplication                     │
│   Web Admin backend management and review                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Further reading

- [Developer Guide](docs/developer_guide.rst)
- [Desgin](docs/desgin.rst)
- [Internal Message](docs/internal_message.rst)
- [Item Info](docs/item_info.rst)

Build docs with:

```bash
cd docs
make html
```

Or visit [Read the Docs](http://zspider.readthedocs.org/).

---

## License

MIT License

## Contributing

Issues and Pull Requests are welcome.
