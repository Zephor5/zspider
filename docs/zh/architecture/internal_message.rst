内部消息设计
============

RabbitMQ 消息格式
-----------------

任务由 Dispatcher 通过 RabbitMQ 发送给 Crawler。

Exchange 配置
~~~~~~~~~~~~~

.. code-block:: python

   EXCHANGE_PARAMS = dict(
       exchange="spider",
       exchange_type="direct"
   )

Queue 配置
~~~~~~~~~~

.. code-block:: python

   TASK_Q_PARAMS = dict(
       queue="task",
       durable=True,
       auto_delete=False,
       exclusive=False,
       arguments={"x-message-ttl": 60000},  # 60 秒 TTL
   )

任务消息
--------

发送到任务队列的 JSON 格式如下：

.. code-block:: json

   {
       "id": "507f1f77bcf86cd799439011",
       "name": "News Crawler Task",
       "spider": "news",
       "parser": "news",
       "is_login": false
   }

字段说明
~~~~~~~~

+-----------+----------+--------------------------------------+
| 字段      | 类型     | 说明                                 |
+===========+==========+======================================+
| id        | string   | 任务的 MongoDB ObjectId              |
+-----------+----------+--------------------------------------+
| name      | string   | 任务名称                             |
+-----------+----------+--------------------------------------+
| spider    | string   | 要执行的 Spider 名称                 |
+-----------+----------+--------------------------------------+
| parser    | string   | 要使用的 Parser 名称                 |
+-----------+----------+--------------------------------------+
| is_login  | boolean  | 是否需要登录 cookie                  |
+-----------+----------+--------------------------------------+

Dispatcher 管理接口
-------------------

Dispatcher 暴露了一组 HTTP 管理接口。

基础地址
~~~~~~~~

``http://{HOST}:{MANAGE_PORT}/``

默认端口：43722

鉴权方式
~~~~~~~~

所有请求都需要以管理 key 结尾：

.. code-block:: text

   GET /{MANAGE_KEY}

默认 key 为 ``managekey-change-me``，可通过环境变量配置。

接口列表
~~~~~~~~

查看 Dispatcher 状态
^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   GET /{MANAGE_KEY}

返回示例：

.. code-block:: json

   {
       "status": true,
       "data": "dispatcher state: dispatch"
   }

重载全部任务
^^^^^^^^^^^^

.. code-block:: text

   GET /reload/{MANAGE_KEY}

返回示例：

.. code-block:: json

   {
       "status": true,
       "data": "5 tasks loaded"
   }

加载单个任务
^^^^^^^^^^^^

.. code-block:: text

   GET /load/{TASK_ID}/{MANAGE_KEY}

返回示例：

.. code-block:: json

   {
       "status": true,
       "data": "job loaded successfully, will first run at 2026-03-11 08:00:00"
   }

暂停任务
^^^^^^^^

.. code-block:: text

   GET /pause/{TASK_ID}/{MANAGE_KEY}

返回示例：

.. code-block:: json

   {
       "status": true,
       "data": "task 507f1f77bcf86cd799439011 paused"
   }

移除任务
^^^^^^^^

.. code-block:: text

   GET /remove/{TASK_ID}/{MANAGE_KEY}

返回示例：

.. code-block:: json

   {
       "status": true,
       "data": "task 507f1f77bcf86cd799439011 removed"
   }

心跳协议
--------

Dispatcher 节点通过 Memcached 完成心跳和主备选举。

Key
~~~

.. code-block:: python

   DISPATCHER_KEY = "_zspider_cluster"

心跳数据
~~~~~~~~

Memcached 中存储的 JSON 类似：

.. code-block:: json

   {
       "192.168.1.100": {
           "status": 2,
           "refresh": 1710140400.123
       },
       "192.168.1.101": {
           "status": 0,
           "refresh": 1710140398.456
       }
   }

状态码
~~~~~~

+-------+-----------+-------------------------------+
| 代码  | 状态      | 说明                          |
+=======+===========+===============================+
| 0x00  | WAITING   | 待命，不参与主动调度          |
+-------+-----------+-------------------------------+
| 0x01  | PENDING   | 正在准备接管                  |
+-------+-----------+-------------------------------+
| 0x02  | DISPATCH  | 正在主动分发任务              |
+-------+-----------+-------------------------------+

选举逻辑
~~~~~~~~

1. 所有节点每 5 秒向 Memcached 写入心跳
2. 如果当前没有 ``DISPATCH`` 节点，优先级最高的 ``PENDING`` 节点升级为 ``DISPATCH``
3. 如果当前 ``DISPATCH`` 节点超过 10 秒没有心跳，备用节点接管

过期清理
~~~~~~~~

超过 10 秒没有心跳的节点，会从集群状态中移除。
