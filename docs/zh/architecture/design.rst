架构设计
========

架构概览
--------

ZSpider 是一个由三个主要组件组成的分布式抓取系统：

.. code-block:: text

   ┌────────────────┐     ┌────────────────┐
   │   Dispatcher   │◄───►│   Dispatcher   │
   │    (Active)    │     │   (Standby)    │
   └───────┬────────┘     └────────────────┘
           │
           ▼
   ┌────────────────┐
   │   RabbitMQ     │  任务队列
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │    Crawler     │  Worker 节点，可横向扩展
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │    MongoDB     │  数据存储
   └────────────────┘

组件职责
--------

Dispatcher
~~~~~~~~~~

Dispatcher 是任务调度中心：

- 基于 APScheduler 的 Cron 调度
- 支持多 Dispatcher 部署，一主多备
- 使用 Memcached 完成心跳与主从切换
- 支持热加载、暂停和移除任务

状态机：

.. code-block:: text

   WAITING ──► PENDING ──► DISPATCH
      ▲                        │
      └────────────────────────┘
           (故障切换后回流)

Crawler
~~~~~~~

Crawler 是执行抓取任务的 Worker 进程：

- 基于 Scrapy
- 从 RabbitMQ 消费任务
- 支持多种 Spider 类型
- 通过 Pipeline 完成后处理

Web 管理后台
~~~~~~~~~~~~

后台基于 Flask：

- 任务管理
- 字段配置
- 结果查看
- 用户认证

数据流
------

.. code-block:: text

   1. 通过 Web 后台或直接写库定义任务
   2. Dispatcher 加载激活任务并按 cron 注册调度
   3. 到达调度时间后，Dispatcher 将任务发送到 RabbitMQ
   4. Crawler 消费消息并执行 Spider
   5. Spider 使用 Parser 解析内容
   6. Pipeline 处理结果并写入 MongoDB

Spider 类型
-----------

NewsSpider
~~~~~~~~~~

适用于结构相对标准的新闻站点：

- 列表页提取文章链接
- 详情页提取正文内容
- 可选登录态支持

WechatSpider
~~~~~~~~~~~~

适用于公众号文章抓取：

- 处理公众号场景的反爬差异
- 提取正文与元数据

SeleniumSpider
~~~~~~~~~~~~~~

适用于依赖 JavaScript 渲染的页面：

- 使用 Selenium WebDriver
- 处理动态内容

解析系统
--------

Parser 负责抽取逻辑定义：

- 使用 XPath 抽取 HTML 节点
- 使用 Regex 做后处理
- 将字段映射到数据模型

BaseParser 方法约定
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class BaseParser:
       def parse_index(self, response):
           """提取文章链接"""
           raise NotImplementedError

       def parse_article(self, response):
           """提取文章内容"""
           raise NotImplementedError

Pipeline 处理链
---------------

Pipeline 用于处理已抽取的数据：

1. ``CappedStorePipeLine``：写入 MongoDB capped collection
2. ``PubPipeLine``：发布到外部接口
3. ``TestResultPipeLine``：测试模式下收集结果

去重机制
--------

URL 去重基于 Memcached：

- 使用 URL 的 MD5 作为 key
- 支持 TTL
- 可在多 Crawler 实例间共享

.. code-block:: python

   class MemcachedDupeFilter(BaseDupeFilter):
       def request_seen(self, request):
           fp = hashlib.md5(request.url.encode()).hexdigest()
           return self.mc.add(fp, '1', self.ttl)

配置
----

核心配置文件包括：

- ``conf.py``：MQ、缓存、日志等核心配置
- ``crawl_conf.py``：Scrapy 配置
- ``dispatcher_conf.py``：Dispatcher 配置
- ``web_conf.py``：Flask Web 配置

环境变量
~~~~~~~~

- ``ZSPIDER_PRODUCT=1``：开启生产模式

开发扩展
--------

运行测试
~~~~~~~~

.. code-block:: bash

   pytest utests/

新增 Spider
~~~~~~~~~~~

1. 在 ``zspider/spiders/`` 中新增 spider 类
2. 在 ``zspider/parsers/`` 中新增 parser 类
3. 在 ``spiders/__init__.py`` 和 ``parsers/__init__.py`` 中注册

扩展 Pipeline
~~~~~~~~~~~~~

.. code-block:: python

   class MyPipeline:
       def __init__(self, task_id):
           self.task_id = task_id

       @classmethod
       def from_crawler(cls, crawler):
           return cls(crawler.spider.task_id)

       def process_item(self, item, spider):
           return item
