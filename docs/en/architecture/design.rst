Architecture Design
===================

Architecture Overview
---------------------

ZSpider is a distributed spider system with three main components:

.. code-block:: text

   ┌────────────────┐     ┌────────────────┐
   │   Dispatcher   │◄───►│   Dispatcher   │
   │    (Active)    │     │   (Standby)    │
   └───────┬────────┘     └────────────────┘
           │
           ▼
   ┌────────────────┐
   │   RabbitMQ     │  Task Queue
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │    Crawler     │  Worker Nodes (Scalable)
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │    MongoDB     │  Data Storage
   └────────────────┘

Components
----------

Dispatcher
~~~~~~~~~~

The Dispatcher is the task scheduling center:

- **Cron Scheduling**: Based on APScheduler with standard crontab syntax
- **High Availability**: Multiple dispatchers can be deployed; one active, others standby
- **Heartbeat Detection**: Uses Memcached for leader election
- **Hot Reload**: Tasks can be loaded, paused, or removed without restart

State Machine:

.. code-block:: text

   WAITING ──► PENDING ──► DISPATCH
      ▲                        │
      └────────────────────────┘
           (on failover)

Crawler
~~~~~~~

The Crawler is the worker process:

- Built on **Scrapy** framework
- Consumes tasks from **RabbitMQ**
- Supports multiple spider types
- Pipelines for data processing

Web Admin
~~~~~~~~~

Flask-based management interface:

- Task CRUD operations
- Field configuration
- Result viewing
- User authentication

Data Flow
---------

.. code-block:: text

   1. Task defined in MongoDB (via Web Admin or direct insert)
   2. Dispatcher loads active tasks and schedules based on cron
   3. At scheduled time, Dispatcher sends task message to RabbitMQ
   4. Crawler receives message and executes spider
   5. Spider parses content using configured Parser
   6. Pipeline processes and stores result in MongoDB

Spider Types
------------

NewsSpider
~~~~~~~~~~

For news websites with standard structure:

- Index page → Article list
- Article page → Content extraction
- Optional login support

WechatSpider
~~~~~~~~~~~~

For WeChat public account articles:

- Handles WeChat-specific anti-crawling
- Extracts article content and metadata

SeleniumSpider
~~~~~~~~~~~~~~

For JavaScript-rendered pages:

- Uses Selenium WebDriver
- Handles dynamic content

Parser System
-------------

Parsers define extraction logic:

- **XPath**: Extract elements from HTML
- **Regex**: Further process extracted text
- **Field Mapping**: Map to data model

BaseParser Methods
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class BaseParser:
       def parse_index(self, response):
           """Extract article URLs from index page"""
           raise NotImplementedError
       
       def parse_article(self, response):
           """Extract article content"""
           raise NotImplementedError

Pipeline Processing
-------------------

Pipelines process extracted items:

1. **CappedStorePipeLine**: Store to MongoDB capped collection
2. **PubPipeLine**: Publish to external API
3. **TestResultPipeLine**: Collect results for testing

Deduplication
-------------

URL deduplication uses Memcached:

- MD5 hash of URL as key
- Configurable TTL
- Distributed across multiple crawler instances

.. code-block:: python

   class MemcachedDupeFilter(BaseDupeFilter):
       def request_seen(self, request):
           fp = hashlib.md5(request.url.encode()).hexdigest()
           return self.mc.add(fp, '1', self.ttl)

Configuration
-------------

Key configuration files:

- ``conf.py``: Core settings (MQ, MC, logging)
- ``crawl_conf.py``: Scrapy settings
- ``dispatcher_conf.py``: Dispatcher-specific config
- ``web_conf.py``: Flask web config

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

- ``ZSPIDER_PRODUCT=1``: Enable production mode

Development
-----------

Running Tests
~~~~~~~~~~~~~

.. code-block:: bash

   pytest utests/

Adding New Spider
~~~~~~~~~~~~~~~~~

1. Create spider class in ``zspider/spiders/``
2. Create parser class in ``zspider/parsers/``
3. Register in ``spiders/__init__.py`` and ``parsers/__init__.py``

Extending Pipeline
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class MyPipeline:
       def __init__(self, task_id):
           self.task_id = task_id
       
       @classmethod
       def from_crawler(cls, crawler):
           return cls(crawler.spider.task_id)
       
       def process_item(self, item, spider):
           # Process item
           return item
