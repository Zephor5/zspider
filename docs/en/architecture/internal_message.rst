Internal Message Design
=======================

RabbitMQ Message Format
-----------------------

Tasks are sent from Dispatcher to Crawler via RabbitMQ.

Exchange Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   EXCHANGE_PARAMS = dict(
       exchange="spider",
       exchange_type="direct"
   )

Queue Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   TASK_Q_PARAMS = dict(
       queue="task",
       durable=True,
       auto_delete=False,
       exclusive=False,
       arguments={"x-message-ttl": 60000},  # 60 seconds TTL
   )

Task Message
------------

JSON format sent to the task queue:

.. code-block:: json

   {
       "id": "507f1f77bcf86cd799439011",
       "name": "News Crawler Task",
       "spider": "news",
       "parser": "news",
       "is_login": false
   }

Fields
~~~~~~

+-----------+----------+-----------------------------------+
| Field     | Type     | Description                       |
+===========+==========+===================================+
| id        | string   | MongoDB ObjectId of the task      |
+-----------+----------+-----------------------------------+
| name      | string   | Human-readable task name          |
+-----------+----------+-----------------------------------+
| spider    | string   | Spider name to use                |
+-----------+----------+-----------------------------------+
| parser    | string   | Parser name to use                |
+-----------+----------+-----------------------------------+
| is_login  | boolean  | Whether login cookies are needed  |
+-----------+----------+-----------------------------------+

Dispatcher Management API
-------------------------

The Dispatcher exposes an HTTP management API.

Base URL
~~~~~~~~

``http://{HOST}:{MANAGE_PORT}/``

Default port: 43722

Authentication
~~~~~~~~~~~~~~

All requests must end with the management key:

.. code-block:: text

   GET /{MANAGE_KEY}

Default key: ``managekey-change-me`` (configurable through environment variables)

Endpoints
~~~~~~~~~

Get Dispatcher Status
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   GET /{MANAGE_KEY}

Response:

.. code-block:: json

   {
       "status": true,
       "data": "dispatcher state: dispatch"
   }

Reload All Tasks
^^^^^^^^^^^^^^^^

.. code-block:: text

   GET /reload/{MANAGE_KEY}

Response:

.. code-block:: json

   {
       "status": true,
       "data": "5 tasks loaded"
   }

Load Single Task
^^^^^^^^^^^^^^^^

.. code-block:: text

   GET /load/{TASK_ID}/{MANAGE_KEY}

Response:

.. code-block:: json

   {
       "status": true,
       "data": "job loaded successfully, will first run at 2026-03-11 08:00:00"
   }

Pause Task
^^^^^^^^^^

.. code-block:: text

   GET /pause/{TASK_ID}/{MANAGE_KEY}

Response:

.. code-block:: json

   {
       "status": true,
       "data": "task 507f1f77bcf86cd799439011 paused"
   }

Remove Task
^^^^^^^^^^^

.. code-block:: text

   GET /remove/{TASK_ID}/{MANAGE_KEY}

Response:

.. code-block:: json

   {
       "status": true,
       "data": "task 507f1f77bcf86cd799439011 removed"
   }

Heartbeat Protocol
------------------

Dispatcher nodes use Memcached for heartbeat and leader election.

Key
~~~

.. code-block:: python

   DISPATCHER_KEY = "_zspider_cluster"

Heartbeat Data
~~~~~~~~~~~~~~

Stored as JSON in Memcached:

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

Status Codes
~~~~~~~~~~~~

+-------+-----------+-------------------------------+
| Code  | State     | Description                   |
+=======+===========+===============================+
| 0x00  | WAITING   | Standing by, not active       |
+-------+-----------+-------------------------------+
| 0x01  | PENDING   | Preparing to become active    |
+-------+-----------+-------------------------------+
| 0x02  | DISPATCH  | Actively dispatching tasks    |
+-------+-----------+-------------------------------+

Election Logic
~~~~~~~~~~~~~~

1. All nodes write heartbeat to Memcached every 5 seconds
2. If no DISPATCH node exists, highest priority PENDING node becomes DISPATCH
3. If current DISPATCH node fails (no heartbeat for 10+ seconds), standby takes over

Expiration
~~~~~~~~~~

Nodes without heartbeat for more than 10 seconds are removed from the cluster state.
