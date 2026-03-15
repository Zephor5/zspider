数据模型参考
============

数据模型
--------

Item
~~~~

抓取结果的主数据模型如下：

.. code-block:: python

   class Item(DynamicDocument):
       meta = {
           "collection": "spider_doc",
           "max_size": 8 * 2**30,        # 8GB capped collection
           "max_documents": 1000000,     # 最多 100 万条
       }

       title = StringField(required=True)
       content = StringField()
       src_time = DateTimeField()        # 来源发布时间
       save_time = DateTimeField()       # 入库时间
       source = StringField()            # 媒体来源
       url = URLField(required=True)
       task = ReferenceField(Task)       # 关联任务
       status = IntField()               # 处理状态
       info = StringField()              # 状态说明

状态码
~~~~~~

+-------+--------------------+------------------+
| 代码  | 名称               | 说明             |
+=======+====================+==================+
| 0     | STATUS_NO          | 未处理           |
+-------+--------------------+------------------+
| 1     | STATUS_PUB_OK      | 发布成功         |
+-------+--------------------+------------------+
| 2     | STATUS_PUB_FAIL    | 发布失败         |
+-------+--------------------+------------------+
| 3     | STATUS_PUB_SKIP    | 被过滤或跳过     |
+-------+--------------------+------------------+

任务模型
--------

.. code-block:: python

   class Task(BaseDocument):
       name = StringField(required=True, max_length=32)
       spider = StringField(required=True)    # Spider 类型
       parser = StringField(required=True)    # Parser 类型
       cron = CronField(default="*/5 * * * *")
       is_login = BooleanField(default=False)
       is_active = BooleanField(default=False)
       creator = ReferenceField(User)
       mender = ReferenceField(User)
       ctime = DateTimeField(default=datetime.now)
       mtime = DateTimeField(default=datetime.now)

Cron 格式
~~~~~~~~~

标准 crontab 语法：

.. code-block:: text

   ┌───────────── minute (0 - 59)
   │ ┌───────────── hour (0 - 23)
   │ │ ┌───────────── day of month (1 - 31)
   │ │ │ ┌───────────── month (1 - 12)
   │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday = 0)
   │ │ │ │ │
   * * * * *

示例：

- ``*/5 * * * *``：每 5 分钟一次
- ``0 */2 * * *``：每 2 小时一次
- ``0 9 * * 1-5``：工作日早上 9 点
- ``0 0 * * *``：每天午夜

文章字段模型
------------

定义每个字段如何从文章页面中提取：

.. code-block:: python

   class ArticleField(BaseDocument):
       task = ReferenceField(Task)
       name = StringField(required=True, max_length=32)
       xpath = XPathField(max_length=128)
       re = RegExpField()
       specify = StringField(max_length=64)  # 固定值

字段类型
~~~~~~~~

title
   文章标题，必填

content
   文章正文

src_time
   来源发布时间

source
   媒体或站点名称

url
   文章 URL，由系统自动填充

字段提取逻辑
~~~~~~~~~~~~

1. 如果设置了 ``specify``，直接使用固定值
2. 否则如果设置了 ``xpath``，先用 XPath 提取
3. 如果同时设置了 ``re``，再对提取结果应用正则
4. 时间类字段会进行额外格式化处理

配置示例
~~~~~~~~

.. code-block:: python

   # 标题字段
   ArticleField(
       task=task,
       name="title",
       xpath="//h1[@class='title']/text()",
   )

   # 正文字段
   ArticleField(
       task=task,
       name="content",
       xpath="//div[@class='article-content']//p/text()",
   )

   # 时间字段
   ArticleField(
       task=task,
       name="src_time",
       xpath="//span[@class='pub-time']/text()",
       re=r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})",
   )

   # 固定来源字段
   ArticleField(
       task=task,
       name="source",
       specify="Example News",
   )

发布订阅模型
------------

用于将抓取结果发布到外部系统：

.. code-block:: python

   class PubSubscribe(BaseDocument):
       cids = StringField()          # 渠道 ID，逗号分隔
       model_id = StringField()      # 目标模型 ID
       trans = StringField()         # 转换规则
       app_creator = StringField()   # 创建者
       online = IntField()           # 0=仅存储，1=存储并发布

转换规则
~~~~~~~~

``trans`` 字段当前支持受限转换表达式：

.. code-block:: python

   # 过滤条件
   "not doc.get('trash') and doc.update({'published': 1})"

   # 字段转换
   "doc.update({'title': doc['title'].strip()})"

预定义变量：

- ``doc``：当前 item 对象的字典
- ``re``：Python 正则模块

执行方式
~~~~~~~~

- ``trans`` 按行执行，每行是一条独立表达式
- 表达式按书写顺序依次作用在同一个 ``doc`` 上
- 某一行执行报错时，该行修改会被丢弃，并记录 warning 日志；后续行仍会继续执行
- 如果某一行执行后给 ``doc`` 写入了 ``trash`` 字段，则当前 item 会被标记为 ``STATUS_PUB_SKIP`` 并停止后续发布

支持的语法
~~~~~~~~~~

当前执行器只支持一小部分 Python 表达式语法，主要覆盖现有发布转换场景：

- 常量：字符串、数字、布尔值、``None``
- 容器字面量：``dict``、``list``、``tuple``
- 变量访问：``doc``、``re``
- 下标访问：例如 ``doc['title']``
- 布尔表达式：``and``、``or``、``not``
- 比较表达式：``==``、``!=``、``in``、``not in``、``>``, ``>=``, ``<``, ``<=``
- 加法：主要用于字符串拼接或列表/元组拼接
- 有限的方法调用：仅允许白名单中的 ``dict`` / ``str`` / ``re`` 方法

允许的方法
~~~~~~~~~~

``doc`` 允许的方法：

- ``doc.get(...)``
- ``doc.update(...)``
- ``doc.pop(...)``
- ``doc.setdefault(...)``

字符串允许的方法：

- ``strip`` / ``lstrip`` / ``rstrip``
- ``replace``
- ``lower`` / ``upper``
- ``split``

``re`` 模块允许的方法：

- ``re.search(...)``
- ``re.match(...)``
- ``re.sub(...)``
- ``re.findall(...)``
- ``re.compile(...)``

由 ``re.compile(...)`` 返回的 pattern 对象允许的方法：

- ``search(...)``
- ``match(...)``
- ``sub(...)``
- ``findall(...)``

常见示例
~~~~~~~~

去除标题首尾空白：

.. code-block:: python

   "doc.update({'title': doc['title'].strip()})"

给标题补前缀：

.. code-block:: python

   "doc.update({'title': '[专题] ' + doc['title']})"

仅当字段不存在时写入默认来源：

.. code-block:: python

   "doc.setdefault('source', 'ZSpider')"

用正则替换正文中的多余空白：

.. code-block:: python

   "doc.update({'content': re.sub(r'\\s+', ' ', doc['content']).strip()})"

命中过滤条件时跳过发布：

.. code-block:: python

   "re.search(r'广告|推广', doc.get('title', '')) and doc.update({'trash': 1})"

先编译正则再复用：

.. code-block:: python

   "doc.update({'source': re.compile(r'来源[:：]\\s*(.+)').findall(doc['content'])[0]})"

不支持的能力
~~~~~~~~~~~~

以下写法会被拒绝，不会像旧版 ``eval`` 那样执行任意 Python 代码：

- 任意模块导入，例如 ``__import__('os')``
- 任意函数调用，例如 ``open(...)``、``eval(...)``、``exec(...)``
- 属性链穿透到白名单之外的对象
- 赋值语句、``lambda``、列表推导式、生成器表达式、条件表达式
- 自定义函数定义、类定义、异常处理、循环等完整 Python 语句

Pipeline 流程
-------------

.. code-block:: text

   Spider 提取 item
          │
          ▼
   ┌──────────────────┐
   │  PubPipeLine     │  状态：STATUS_PUB_OK/FAIL/SKIP
   └────────┬─────────┘
            │
            ▼
   ┌─────────────────────┐
   │ CappedStorePipeLine │  保存到 MongoDB
   └─────────────────────┘

查询示例
--------

使用 MongoEngine 查询：

.. code-block:: python

   from zspider.models import Item
   from zspider.utils.models import Task

   # 按任务查询
   task = Task.objects.get(name="News Crawler")
   items = Item.objects.filter(task=task)

   # 按状态查询
   pending = Item.objects.filter(status=0)
   published = Item.objects.filter(status=1)

   # 按时间范围查询
   recent = Item.objects.filter(
       save_time__gte=datetime(2026, 3, 1)
   )

   # 文本检索
   results = Item.objects.filter(
       title__contains="keyword"
   )
