Operations Guide
================

ZSpider is operated as a self-hosted application. Runtime configuration, dependency services, health checks, and startup modes should therefore be explicit and environment-driven.

Environment model
-----------------

Use ``ZSPIDER_ENV`` to distinguish environments:

- ``development``: local source-based development
- ``testing``: CI or isolated validation
- ``production``: deployed self-hosted environment

Key environment variables
-------------------------

+------------------------------+----------------------------------------+
| Variable                     | Purpose                                |
+==============================+========================================+
| ``ZSPIDER_AMQP_URL``         | RabbitMQ connection URL                |
+------------------------------+----------------------------------------+
| ``ZSPIDER_MEMCACHED_SERVERS``| Memcached server list                  |
+------------------------------+----------------------------------------+
| ``ZSPIDER_MONGODB_URI``      | optional MongoDB URI override          |
+------------------------------+----------------------------------------+
| ``ZSPIDER_MONGODB_HOST``     | MongoDB host                           |
+------------------------------+----------------------------------------+
| ``ZSPIDER_MONGODB_PORT``     | MongoDB port                           |
+------------------------------+----------------------------------------+
| ``ZSPIDER_WEB_HOST``         | web bind host                          |
+------------------------------+----------------------------------------+
| ``ZSPIDER_WEB_PORT``         | web bind port                          |
+------------------------------+----------------------------------------+
| ``ZSPIDER_SECRET_KEY``       | Flask session secret                   |
+------------------------------+----------------------------------------+
| ``ZSPIDER_MANAGE_PORT``      | dispatcher management port             |
+------------------------------+----------------------------------------+
| ``ZSPIDER_MANAGE_KEY``       | dispatcher management key              |
+------------------------------+----------------------------------------+

Local dependencies
------------------

For local development, dependency services are defined in ``docker-compose.services.yml``:

- MongoDB
- RabbitMQ
- Memcached

Start them with:

.. code-block:: bash

   make services-up

Health and readiness
--------------------

The web service exposes:

- ``/healthz``: process is alive
- ``/readyz``: process can reach MongoDB, RabbitMQ, and Memcached

Example checks:

.. code-block:: bash

   curl http://127.0.0.1:5000/healthz
   curl http://127.0.0.1:5000/readyz

Admin bootstrap
---------------

Create the initial admin user explicitly:

.. code-block:: bash

   make bootstrap-admin ADMIN_USERNAME=admin ADMIN_PASSWORD=change-me

Web serving model
-----------------

The web process now runs through a WSGI server instead of Flask's development ``app.run`` path.

Recommended local start:

.. code-block:: bash

   make run-web

Or start the full stack:

.. code-block:: bash

   make dev
