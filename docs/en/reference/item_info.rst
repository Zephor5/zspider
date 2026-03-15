Item Model Reference
====================

Data Model
----------

Item
~~~~

The main data model for crawled content:

.. code-block:: python

   class Item(DynamicDocument):
       meta = {
           "collection": "spider_doc",
           "max_size": 8 * 2**30,      # 8GB capped collection
           "max_documents": 1000000,    # Max 1 million documents
       }

       title = StringField(required=True)
       content = StringField()
       src_time = DateTimeField()       # Source publish time
       save_time = DateTimeField()      # Storage time
       source = StringField()           # Media source
       url = URLField(required=True)
       task = ReferenceField(Task)      # Reference to task
       status = IntField()              # Processing status
       info = StringField()             # Status message

Status Codes
~~~~~~~~~~~~

+-------+--------------------+-------------------+
| Code  | Name               | Description       |
+=======+====================+===================+
| 0     | STATUS_NO          | Not processed     |
+-------+--------------------+-------------------+
| 1     | STATUS_PUB_OK      | Published success |
+-------+--------------------+-------------------+
| 2     | STATUS_PUB_FAIL    | Published failed  |
+-------+--------------------+-------------------+
| 3     | STATUS_PUB_SKIP    | Filtered/Skipped  |
+-------+--------------------+-------------------+

Task Model
----------

.. code-block:: python

   class Task(BaseDocument):
       name = StringField(required=True, max_length=32)
       spider = StringField(required=True)    # Spider type
       parser = StringField(required=True)    # Parser type
       cron = CronField(default="*/5 * * * *")
       is_login = BooleanField(default=False)
       is_active = BooleanField(default=False)
       creator = ReferenceField(User)
       mender = ReferenceField(User)
       ctime = DateTimeField(default=datetime.now)
       mtime = DateTimeField(default=datetime.now)

Cron Field Format
~~~~~~~~~~~~~~~~~

Standard crontab syntax:

.. code-block:: text

   ┌───────────── minute (0 - 59)
   │ ┌───────────── hour (0 - 23)
   │ │ ┌───────────── day of month (1 - 31)
   │ │ │ ┌───────────── month (1 - 12)
   │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday = 0)
   │ │ │ │ │
   * * * * *

Examples:

- ``*/5 * * * *`` - Every 5 minutes
- ``0 */2 * * *`` - Every 2 hours
- ``0 9 * * 1-5`` - Weekdays at 9 AM
- ``0 0 * * *`` - Daily at midnight

Article Field Model
-------------------

Defines how to extract each field from article pages:

.. code-block:: python

   class ArticleField(BaseDocument):
       task = ReferenceField(Task)
       name = StringField(required=True, max_length=32)
       xpath = XPathField(max_length=128)
       re = RegExpField()
       specify = StringField(max_length=64)  # Fixed value

Field Types
~~~~~~~~~~~

title
   Article title (required)

content
   Article body content

src_time
   Publication time from source

source
   Media/source name

url
   Article URL (auto-filled)

Field Extraction Logic
~~~~~~~~~~~~~~~~~~~~~~

1. If ``specify`` is set, use that value directly
2. Else if ``xpath`` is set, extract using XPath
3. If ``re`` is also set, apply regex to extracted value
4. Special handling for ``time`` fields (auto-formatting)

Example Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Title field
   ArticleField(
       task=task,
       name="title",
       xpath="//h1[@class='title']/text()",
   )

   # Content field
   ArticleField(
       task=task,
       name="content",
       xpath="//div[@class='article-content']//p/text()",
   )

   # Time field with regex
   ArticleField(
       task=task,
       name="src_time",
       xpath="//span[@class='pub-time']/text()",
       re=r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})",
   )

   # Fixed value field
   ArticleField(
       task=task,
       name="source",
       specify="Example News",
   )

PubSubscribe Model
------------------

For publishing crawled items to external systems:

.. code-block:: python

   class PubSubscribe(BaseDocument):
       cids = StringField()          # Channel IDs (comma-separated)
       model_id = StringField()      # Target model ID
       trans = StringField()         # Transformation rules
       app_creator = StringField()   # Creator name
       online = IntField()           # 0=store only, 1=store and publish

Transformation Rules
~~~~~~~~~~~~~~~~~~~~

The ``trans`` field accepts restricted transform expressions:

.. code-block:: python

   # Filter condition
   "not doc.get('trash') and doc.update({'published': 1})"

   # Field transformation
   "doc.update({'title': doc['title'].strip()})"

Pre-defined Variables:

- ``doc``: The item dictionary
- ``re``: Python regex module

Execution Model
~~~~~~~~~~~~~~~

- ``trans`` is processed line by line; each line is an independent expression
- Expressions run in order against the same mutable ``doc``
- If one line fails, its changes are discarded and a warning is logged; later lines still run
- If a line writes ``trash`` into ``doc``, the item is marked as ``STATUS_PUB_SKIP`` and publishing stops

Supported Syntax
~~~~~~~~~~~~~~~~

The evaluator intentionally supports only a small Python expression subset:

- Constants: strings, numbers, booleans, ``None``
- Container literals: ``dict``, ``list``, ``tuple``
- Variable access: ``doc``, ``re``
- Subscription access: for example ``doc['title']``
- Boolean expressions: ``and``, ``or``, ``not``
- Comparisons: ``==``, ``!=``, ``in``, ``not in``, ``>``, ``>=``, ``<``, ``<=``
- Addition: mainly for string or list/tuple concatenation
- Limited method calls: only whitelisted ``dict`` / ``str`` / ``re`` methods

Allowed Methods
~~~~~~~~~~~~~~~

Allowed on ``doc``:

- ``doc.get(...)``
- ``doc.update(...)``
- ``doc.pop(...)``
- ``doc.setdefault(...)``

Allowed on strings:

- ``strip`` / ``lstrip`` / ``rstrip``
- ``replace``
- ``lower`` / ``upper``
- ``split``

Allowed on the ``re`` module:

- ``re.search(...)``
- ``re.match(...)``
- ``re.sub(...)``
- ``re.findall(...)``
- ``re.compile(...)``

Allowed on compiled regex patterns:

- ``search(...)``
- ``match(...)``
- ``sub(...)``
- ``findall(...)``

Common Examples
~~~~~~~~~~~~~~~

Trim title whitespace:

.. code-block:: python

   "doc.update({'title': doc['title'].strip()})"

Add a title prefix:

.. code-block:: python

   "doc.update({'title': '[Feature] ' + doc['title']})"

Set a default source only if it is missing:

.. code-block:: python

   "doc.setdefault('source', 'ZSpider')"

Normalize repeated whitespace in content:

.. code-block:: python

   "doc.update({'content': re.sub(r'\\s+', ' ', doc['content']).strip()})"

Skip publishing when a filter matches:

.. code-block:: python

   "re.search(r'ad|promo', doc.get('title', '')) and doc.update({'trash': 1})"

Compile a regex and reuse it immediately:

.. code-block:: python

   "doc.update({'source': re.compile(r'Source[:：]\\s*(.+)').findall(doc['content'])[0]})"

Unsupported Capabilities
~~~~~~~~~~~~~~~~~~~~~~~~

The new evaluator rejects anything that would execute arbitrary Python code, including:

- Arbitrary imports such as ``__import__('os')``
- Arbitrary function calls such as ``open(...)``, ``eval(...)``, ``exec(...)``
- Attribute access outside the allowlist
- Assignment statements, ``lambda``, comprehensions, generator expressions, ternary expressions
- Function definitions, class definitions, exception handling, loops, and other full Python statements

Pipeline Flow
-------------

.. code-block:: text

   Spider extracts item
          │
          ▼
   ┌──────────────────┐
   │  PubPipeLine     │  Status: STATUS_PUB_OK/FAIL/SKIP
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │ CappedStorePipeLine │  Save to MongoDB
   └──────────────────┘

Querying Items
--------------

Using MongoEngine:

.. code-block:: python

   from zspider.models import Item
   from zspider.utils.models import Task

   # Get items by task
   task = Task.objects.get(name="News Crawler")
   items = Item.objects.filter(task=task)

   # Get items by status
   pending = Item.objects.filter(status=0)
   published = Item.objects.filter(status=1)

   # Get items by date range
   recent = Item.objects.filter(
       save_time__gte=datetime(2026, 3, 1)
   )

   # Full-text search (if enabled)
   results = Item.objects.filter(
       title__contains="keyword"
   )
