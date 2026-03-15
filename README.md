# ZSpider

[![CI](https://github.com/Zephor5/zspider/actions/workflows/ci.yml/badge.svg)](https://github.com/Zephor5/zspider/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/zspider/badge/?version=latest)](http://zspider.readthedocs.org/en/latest/?badge=latest)

面向 **内容监控 / 资讯聚合** 场景的自托管抓取平台。

ZSpider 不是“写几个爬虫脚本然后自己拼调度”的工具，而是一套带 **Web 后台、定时调度、配置化解析、结果查看** 的平台化抓取系统，适合持续监控新闻、公告、公众号和各类公开网页内容。

项目最终形态按 **自托管应用** 设计，而不是面向 PyPI 的通用 Python 包。推荐使用源码仓库 + 虚拟环境 + Docker Compose 来运行和维护。

[English README](README_EN.md)

---

## 它适合什么场景

ZSpider 更适合“持续运行的内容采集任务”，而不是一次性脚本：

- **新闻 / 资讯聚合**：监控多个媒体站点，统一采集标题、正文、时间、来源
- **公告监控**：追踪政府、学校、企业官网的公告更新
- **公众号采集**：抓取公众号文章列表和正文，做归档或二次分析
- **行业情报收集**：持续拉取公开网页内容，用于研究、投研、舆情或专题跟踪
- **自建抓取后台**：把任务、字段、结果、日志放在同一套后台中集中管理

如果你的目标是“长期稳定地监控内容变化”，ZSpider 会比零散脚本更省心。

---

## 核心能力

- 🕷️ **平台化任务管理**：通过 Web 后台集中管理抓取任务和字段配置
- ⏰ **定时调度**：基于 APScheduler 的 Cron 任务调度
- 🌐 **可视化后台**：查看任务状态、抓取结果、运行日志
- 📦 **配置化解析**：支持 XPath + 正则提取，不必每次都重写代码
- 🔐 **登录站点支持**：支持需要登录态的网站抓取
- 🔄 **去重机制**：基于 Memcached 的 URL 去重和心跳机制
- 🚚 **可扩展架构**：Dispatcher / Crawler 解耦，可横向扩展 Worker

---

## 为什么不是普通爬虫脚本

当需求从“一次抓完”变成“持续监控”后，团队通常会开始遇到这些问题：

- 任务分散在多个脚本里，不好管理
- 调度依赖 crontab / supervisor，链路分散
- 解析规则改完后，没有统一入口重新验证
- 多站点并发后，日志、状态、结果难以集中查看

ZSpider 的目标就是把这类 **持续抓取 + 定时调度 + 结果管理** 的工作沉淀成一套更容易跑起来、也更容易交接的平台。

---

## 5 分钟快速体验

### 1）准备环境

推荐使用 Python 3.9：

```bash
git clone https://github.com/Zephor5/zspider.git
cd zspider
cp .env.example .env
python3.9 -m venv .venv
./.venv/bin/pip install -U pip
./.venv/bin/pip install -r requirements_dev.txt -c constraints/py39.txt
```

也可以直接使用统一入口：

```bash
make install
```

### 2）一键启动依赖服务

```bash
make services-up
```

会启动：

- MongoDB
- RabbitMQ
- Memcached

### 3）启动 ZSpider 本地开发栈

```bash
make dev
```

这个命令会统一启动：

- `zspider.dispatcher`
- `zspider.crawler`
- `zspider.web`

默认访问地址：

```text
http://127.0.0.1:5000
```

### 4）初始化管理员账号

先显式创建管理员账号：

```bash
make bootstrap-admin ADMIN_USERNAME=admin ADMIN_PASSWORD=change-me
```

然后再访问 `/login` 使用该账号登录。

### 5）验证是否跑通

- 打开后台首页，确认能访问 Dashboard
- 登录后新建任务 / 查看任务页是否正常打开
- 查看 `logs/web.log`、`logs/dispatcher.log`、`logs/crawler.log` 是否有异常

停止服务：

```bash
# Ctrl + C 停止 make dev 启动的本地进程
make services-down
```

---

## 本地开发的统一入口

为了减少“到底先起哪个组件”的理解成本，仓库现在提供了统一入口：

```bash
make dev
```

它会：

1. 自动拉起 `docker-compose.services.yml` 里的依赖
2. 用当前仓库 `.venv` 启动 dispatcher / crawler / web
3. 将日志写入 `logs/dispatcher.log`、`logs/crawler.log`、`logs/web.log`

如果你只想启动外部依赖：

```bash
make services-up
```

如果你只想运行测试：

```bash
make test
```

如果你只想单独启动某个进程：

```bash
make run-dispatcher
make run-crawler
make run-web
```

如果需要初始化管理员账号：

```bash
make bootstrap-admin ADMIN_USERNAME=admin ADMIN_PASSWORD=change-me
```

如果你只想构建文档：

```bash
make docs
```

---

## 仓库形态

ZSpider 按“自托管应用”维护，意味着：

- 默认运行方式是源码仓库 + `.venv` + `docker compose`
- 推荐入口是 `make`、`scripts/dev-start.sh` 和 `python -m zspider.<service>`
- 仓库保留 Python 包目录结构，是为了模块组织和源码运行
- 项目当前**不以发布 PyPI 包为目标**

---

## 系统架构

```text
┌─────────────────────────────────────────────────────────────┐
│                        ZSpider 系统                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Dispatcher  →  RabbitMQ  →  Crawler Workers              │
│        │                               │                    │
│        └──────── 状态 / 管理 ──────────┘                    │
│                                                             │
│   MongoDB   存储任务与抓取结果                              │
│   Memcached 心跳与去重                                      │
│   Web Admin 后台管理与查看                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 面向开发者的进一步阅读

中文文档：

- [文档首页](docs/zh/index.rst)
- [开发指南](docs/zh/guides/developer_guide.rst)
- [运维指南](docs/zh/guides/operations.rst)
- [现代化改造规划](docs/zh/guides/modernization_plan.rst)
- [架构设计](docs/zh/architecture/design.rst)
- [内部消息设计](docs/zh/architecture/internal_message.rst)
- [数据模型参考](docs/zh/reference/item_info.rst)

英文文档：

- [Documentation Home](docs/en/index.rst)
- [Developer Guide](docs/en/guides/developer_guide.rst)
- [Operations Guide](docs/en/guides/operations.rst)
- [Modernization Plan](docs/en/guides/modernization_plan.rst)
- [Architecture Design](docs/en/architecture/design.rst)
- [Internal Message Design](docs/en/architecture/internal_message.rst)
- [Item Model Reference](docs/en/reference/item_info.rst)

构建文档：

```bash
cd docs
make html
```

或访问 [Read the Docs](http://zspider.readthedocs.org/)。

---

## License

MIT License

## Contributing

欢迎提交 Issue 和 Pull Request。
