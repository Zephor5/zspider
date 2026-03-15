Developer Guide
===============

This guide is for developers who want to understand, extend, or operate ZSpider beyond the first-run experience.

ZSpider should be treated as a self-hosted application repository. The source tree is importable as Python modules, but the primary operating model is source checkout + virtualenv + supporting services, not publishing or consuming a PyPI package.

Requirements
------------

First-run shortcut
------------------

If you only want to get a local instance running quickly:

.. code-block:: bash

   cp .env.example .env
   python3.9 -m venv .venv
   ./.venv/bin/pip install -U pip
   ./.venv/bin/pip install -r requirements_dev.txt -c constraints/py39.txt
   make services-up
   make dev

Then open ``http://127.0.0.1:5000/login``.

When the user table is empty, the first username + password you submit becomes the initial admin account.

If you prefer the repository-level convenience target:

.. code-block:: bash

   make install


Python Version
~~~~~~~~~~~~~~

- Python 3.7
- Python 3.8
- Python 3.9

.. note::

   Python 3.10+ is not recommended yet. Some legacy dependencies such as ``pooled-pika~=0.3.0`` and ``flask-mongoengine~=1.0.0`` have limited compatibility with newer Python versions.

Recommended Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pyenv install 3.9.20
   pyenv local 3.9.20
   python -m venv .venv
   . .venv/bin/activate
   pip install -U pip
   pip install -r requirements_dev.txt -c constraints/py39.txt

Repository workflow
~~~~~~~~~~~~~~~~~~~

The recommended way to work with ZSpider is:

1. clone the repository
2. create a project-local virtualenv
3. bring up external services with Docker Compose
4. run services from source with ``python -m`` or ``make``

The project keeps a Python package layout for import structure, but it is not currently intended for PyPI publication.

External Dependencies
~~~~~~~~~~~~~~~~~~~~~

+------------+-----------------------------+--------------+
| Service    | Purpose                     | Default Port |
+============+=============================+==============+
| RabbitMQ   | Task queue                  | 5672         |
+------------+-----------------------------+--------------+
| MongoDB    | Data storage                | 27017        |
+------------+-----------------------------+--------------+
| Memcached  | Heartbeat + URL dedup       | 11211        |
+------------+-----------------------------+--------------+

Configuration
-------------

Main configuration files live in ``zspider/confs/``:

+------------------------+------------------------------------------+
| File                   | Purpose                                  |
+========================+==========================================+
| ``conf.py``            | Core config (MQ, cache, logging, etc.)   |
+------------------------+------------------------------------------+
| ``crawl_conf.py``      | Scrapy crawler settings                  |
+------------------------+------------------------------------------+
| ``dispatcher_conf.py`` | Dispatcher scheduler config              |
+------------------------+------------------------------------------+
| ``web_conf.py``        | Flask web config                         |
+------------------------+------------------------------------------+

Typical local values:

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

Production Mode
~~~~~~~~~~~~~~~

.. code-block:: bash

   export ZSPIDER_PRODUCT=1

Then update the production parameters in each config file.

Core Components
---------------

Dispatcher
~~~~~~~~~~

- APScheduler-based Cron scheduling
- Multi-node deployment with automatic failover
- Heartbeat detection via Memcached
- Hot reload, pause, and delete task support

Management API:

.. code-block:: text

   GET /{MANAGE_KEY}                   # Get status
   GET /reload/{MANAGE_KEY}            # Reload all tasks
   GET /load/{task_id}/{MANAGE_KEY}    # Load a specific task
   GET /pause/{task_id}/{MANAGE_KEY}   # Pause a task
   GET /remove/{task_id}/{MANAGE_KEY}  # Remove a task

Crawler
~~~~~~~

- Built on Scrapy
- Pulls tasks from RabbitMQ
- Supports multiple spider types
- Uses built-in pipeline processing

Web Admin
~~~~~~~~~

- Flask + MongoEngine
- Task CRUD management
- Visual field configuration
- Result browsing
- User management

Main pages:

+--------------+----------------------------------+
| Page         | Function                         |
+==============+==================================+
| Dashboard    | Dispatcher status monitoring     |
+--------------+----------------------------------+
| Task List    | View / manage tasks              |
+--------------+----------------------------------+
| Add Task     | Create new crawl tasks           |
+--------------+----------------------------------+
| Data Records | Review crawl results             |
+--------------+----------------------------------+
| Logs         | Crawler / Dispatcher logs        |
+--------------+----------------------------------+
| User Admin   | User CRUD (admin only)           |
+--------------+----------------------------------+

Spider Types
------------

+--------------+----------------------+-------------------------+
| Spider       | Purpose              | File                    |
+==============+======================+=========================+
| ``news``     | News websites        | ``spiders/news.py``     |
+--------------+----------------------+-------------------------+
| ``wechat``   | WeChat articles      | ``spiders/wechat.py``   |
+--------------+----------------------+-------------------------+
| ``selenium`` | Dynamic rendering    | ``spiders/selenium.py`` |
+--------------+----------------------+-------------------------+

Custom Spider Example
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from zspider.basespider import BaseSpider

   class MySpider(BaseSpider):
       name = "myspider"

       def parse(self, response):
           for item in self._parse_index(response):
               yield item

Parser Configuration
--------------------

ZSpider supports configurable extraction through XPath + regex.

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

Pipelines
---------

+------------------------+------------------------------------------+
| Pipeline               | Function                                 |
+========================+==========================================+
| ``CappedStorePipeLine``| Store to MongoDB capped collections      |
+------------------------+------------------------------------------+
| ``PubPipeLine``        | Publish to external systems              |
+------------------------+------------------------------------------+
| ``TestResultPipeLine`` | Collect results in test mode             |
+------------------------+------------------------------------------+

Project Structure
-----------------

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

Runtime entry points
--------------------

Preferred local entry points are source-based:

.. code-block:: bash

   make dev
   make run-dispatcher
   make run-crawler
   make run-web

Equivalent direct module commands:

.. code-block:: bash

   .venv/bin/python -m zspider.dispatcher
   .venv/bin/python -m zspider.crawler
   .venv/bin/python -m zspider.web
   ├── Dockerfile
   └── docker-compose.services.yml
