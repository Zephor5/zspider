开发指南
========

本文面向希望理解、扩展或维护 ZSpider 的开发者。

ZSpider 应被视为一个自托管应用仓库。源码目录虽然保持了 Python 模块结构，但主要运行方式是“源码检出 + 虚拟环境 + 外部依赖服务”，而不是发布或消费一个 PyPI 包。

环境要求
--------

快速启动
--------

如果你只想先把本地实例跑起来，可以直接执行：

.. code-block:: bash

   cp .env.example .env
   python3.9 -m venv .venv
   ./.venv/bin/pip install -U pip
   ./.venv/bin/pip install -r requirements_dev.txt -c constraints/py39.txt
   make services-up
   make dev

先初始化管理员账号：

.. code-block:: bash

   make bootstrap-admin ADMIN_USERNAME=admin ADMIN_PASSWORD=change-me

然后访问 ``http://127.0.0.1:5000/login`` 并使用该账号登录。

如果你想使用仓库统一入口，也可以直接执行：

.. code-block:: bash

   make install

Python 版本
~~~~~~~~~~~

- Python 3.7
- Python 3.8
- Python 3.9

.. note::

   当前并不推荐直接使用 Python 3.10 及以上版本。部分历史依赖如 ``pooled-pika~=0.3.0`` 和 ``flask-mongoengine~=1.0.0`` 对新版本 Python 的兼容性有限。

推荐开发环境
~~~~~~~~~~~~

.. code-block:: bash

   pyenv install 3.9.20
   pyenv local 3.9.20
   python -m venv .venv
   . .venv/bin/activate
   pip install -U pip
   pip install -r requirements_dev.txt -c constraints/py39.txt

仓库工作方式
~~~~~~~~~~~~

推荐按下面的方式使用 ZSpider：

1. 克隆源码仓库
2. 创建项目本地虚拟环境
3. 用 Docker Compose 拉起依赖服务
4. 通过 ``python -m`` 或 ``make`` 从源码运行各组件

项目保留 Python 包目录结构，主要是为了模块组织和源码运行，而不是为了发布 PyPI 包。

外部依赖服务
~~~~~~~~~~~~

+------------+----------------------+----------+
| 服务       | 用途                 | 默认端口 |
+============+======================+==========+
| RabbitMQ   | 任务队列             | 5672     |
+------------+----------------------+----------+
| MongoDB    | 数据存储             | 27017    |
+------------+----------------------+----------+
| Memcached  | 心跳与 URL 去重      | 11211    |
+------------+----------------------+----------+

配置
----

核心配置文件位于 ``zspider/confs/``：

+------------------------+----------------------------------------+
| 文件                   | 作用                                   |
+========================+========================================+
| ``conf.py``            | 核心配置，如 MQ、缓存、日志            |
+------------------------+----------------------------------------+
| ``crawl_conf.py``      | Scrapy 抓取配置                        |
+------------------------+----------------------------------------+
| ``dispatcher_conf.py`` | 调度器配置                             |
+------------------------+----------------------------------------+
| ``web_conf.py``        | Flask Web 配置                         |
+------------------------+----------------------------------------+

本地开发常见配置示例：

.. code-block:: python

   # conf.py
   DEBUG = True
   AMQP_PARAM = URLParameters("amqp://guest:guest@127.0.0.1")
   MC_SERVERS = "127.0.0.1:11211"

.. code-block:: python

   # web_conf.py
   FLASK_CONF = {
       "SECRET_KEY": "your-secret-key",
       "MONGODB_SETTINGS": {
           "db": "spider",
           "host": "localhost",
       "port": 27017,
       },
   }

生产模式
~~~~~~~~

.. code-block:: bash

   export ZSPIDER_PRODUCT=1

然后按环境修改各配置文件中的生产参数。

核心组件
--------

Dispatcher
~~~~~~~~~~

- 基于 APScheduler 的 Cron 调度
- 支持多节点部署和自动切换
- 使用 Memcached 做心跳检测
- 支持热加载、暂停和删除任务

管理接口：

.. code-block:: text

   GET /{MANAGE_KEY}                   # 查看状态
   GET /reload/{MANAGE_KEY}            # 重载全部任务
   GET /load/{task_id}/{MANAGE_KEY}    # 加载单个任务
   GET /pause/{task_id}/{MANAGE_KEY}   # 暂停任务
   GET /remove/{task_id}/{MANAGE_KEY}  # 删除任务

Crawler
~~~~~~~

- 基于 Scrapy
- 从 RabbitMQ 拉取任务
- 支持多种 Spider 类型
- 使用内置 Pipeline 做后处理

Web 管理后台
~~~~~~~~~~~~

- Flask + MongoEngine
- 任务增删改查
- 可视化字段配置
- 结果浏览
- 用户管理

主要页面：

+--------------+--------------------------------+
| 页面         | 功能                           |
+==============+================================+
| Dashboard    | 调度状态监控                   |
+--------------+--------------------------------+
| Task List    | 查看和管理任务                 |
+--------------+--------------------------------+
| Add Task     | 创建抓取任务                   |
+--------------+--------------------------------+
| Data Records | 查看抓取结果                   |
+--------------+--------------------------------+
| Logs         | 查看 Crawler / Dispatcher 日志 |
+--------------+--------------------------------+
| User Admin   | 用户管理，仅管理员可见         |
+--------------+--------------------------------+

Spider 类型
-----------

+--------------+----------------------+-------------------------+
| Spider       | 用途                 | 文件                    |
+==============+======================+=========================+
| ``news``     | 新闻站点             | ``spiders/news.py``     |
+--------------+----------------------+-------------------------+
| ``wechat``   | 公众号文章           | ``spiders/wechat.py``   |
+--------------+----------------------+-------------------------+
| ``browser``  | 动态渲染页面         | ``spiders/browser.py``  |
+--------------+----------------------+-------------------------+

自定义 Spider 示例
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from zspider.basespider import BaseSpider

   class MySpider(BaseSpider):
       name = "myspider"

       def parse(self, response):
           for item in self._parse_index(response):
               yield item

解析配置
--------

ZSpider 支持通过 XPath + 正则进行配置化提取。

.. code-block:: python

   task = Task(
       name="News Crawler",
       spider="news",
       parser="news",
       cron="0 */2 * * *",
       is_active=True,
   )

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

Pipeline
--------

+-------------------------+------------------------------------+
| Pipeline                | 作用                               |
+=========================+====================================+
| ``CappedStorePipeLine`` | 存入 MongoDB capped collection     |
+-------------------------+------------------------------------+
| ``PubPipeLine``         | 发布到外部系统                     |
+-------------------------+------------------------------------+
| ``TestResultPipeLine``  | 测试模式下收集结果                 |
+-------------------------+------------------------------------+

项目结构
--------

.. code-block:: text

   zspider/
   ├── zspider/
   │   ├── spiders/
   │   ├── parsers/
   │   ├── pipelines/
   │   ├── middlewares/
   │   ├── utils/
   │   ├── www/
   │   ├── confs/
   │   ├── models.py
   │   ├── crawler.py
   │   ├── dispatcher.py
   │   └── web.py
   ├── utests/
   ├── docs/
   ├── requirements.txt
   ├── requirements_dev.txt

运行入口
--------

推荐使用以下源码运行入口：

.. code-block:: bash

   make dev
   make run-dispatcher
   make run-crawler
   make run-web
   make bootstrap-admin ADMIN_USERNAME=admin ADMIN_PASSWORD=change-me

对应的直接模块命令为：

.. code-block:: bash

   .venv/bin/python -m zspider.dispatcher
   .venv/bin/python -m zspider.crawler
   .venv/bin/python -m zspider.web
