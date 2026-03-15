# ZSpider

[![CI](https://github.com/Zephor5/zspider/actions/workflows/ci.yml/badge.svg)](https://github.com/Zephor5/zspider/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/zspider/badge/?version=latest)](http://zspider.readthedocs.org/en/latest/?badge=latest)

[中文说明](README.md)

A self-hosted crawling platform for **content monitoring and news aggregation**.

ZSpider is not just a place to dump crawler scripts. It is a platform-oriented system with a **web admin, scheduling, configurable parsing, and result review**, built for recurring collection workflows such as monitoring news sites, announcements, WeChat articles, and other public web content.

The project is maintained as a **self-hosted application**, not as a general-purpose Python package for PyPI. The intended operating model is source checkout + virtualenv + Docker Compose.

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
./.venv/bin/pip install -U pip
./.venv/bin/pip install -r requirements_dev.txt -c constraints/py39.txt
```

You can also use the unified bootstrap target:

```bash
make install
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

Create the initial admin account explicitly:

```bash
make bootstrap-admin ADMIN_USERNAME=admin ADMIN_PASSWORD=change-me
```

Then visit `/login` and sign in with that account.

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

If you want to start a single service:

```bash
make run-dispatcher
make run-crawler
make run-web
```

The practical difference is:

- `make run-web`: starts only the web process, which is useful when you only want to work on the admin UI or web-side behavior
- `make dev`: starts the full local development stack, including dependency services, dispatcher, crawler, and web, which is better for end-to-end local validation

If you need to bootstrap the admin user:

```bash
make bootstrap-admin ADMIN_USERNAME=admin ADMIN_PASSWORD=change-me
```

If you only want to build docs:

```bash
make docs
```

---

## Repository Shape

ZSpider is maintained as a self-hosted application. In practice that means:

- the default operating model is source checkout + `.venv` + `docker compose`
- the preferred entry points are `make`, `scripts/dev-start.sh`, and `python -m zspider.<service>`
- the Python package layout is kept for module organization and source-based execution
- the project is **not currently targeting PyPI publication**

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

## Further Reading

- [Documentation Home](docs/en/index.rst)
- [Developer Guide](docs/en/guides/developer_guide.rst)
- [Operations Guide](docs/en/guides/operations.rst)
- [Modernization Plan](docs/en/guides/modernization_plan.rst)
- [Architecture Design](docs/en/architecture/design.rst)
- [Internal Message Design](docs/en/architecture/internal_message.rst)
- [Item Model Reference](docs/en/reference/item_info.rst)

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
