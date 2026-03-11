.. zspider documentation master file

=======
ZSPIDER
=======

A distributed cron spider system with web management interface.

|build-status|

.. |build-status| image:: https://readthedocs.org/projects/zspider/badge/?version=latest
   :target: http://zspider.readthedocs.org/en/latest/?badge=latest

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   desgin
   internal_message
   item_info
   api

Installation
============

Requirements
------------

Python Version
~~~~~~~~~~~~~~

- Python 3.7
- Python 3.8
- Python 3.9

External Dependencies
~~~~~~~~~~~~~~~~~~~~~

+------------+---------------+------------------+
| Service    | Purpose       | Default Port     |
+============+===============+==================+
| RabbitMQ   | Task Queue    | 5672             |
+------------+---------------+------------------+
| MongoDB    | Data Storage  | 27017            |
+------------+---------------+------------------+
| Memcached  | Heartbeat     | 11211            |
+------------+---------------+------------------+

Install from PyPI
-----------------

.. code-block:: bash

   pip install zspider

Install from Source
-------------------

.. code-block:: bash

   git clone https://github.com/Zephor5/zspider.git
   cd zspider
   pip install -r requirements.txt
   pip install -e .

Docker Installation
-------------------

.. code-block:: bash

   docker-compose up -d

Components
----------

Dispatcher
~~~~~~~~~~

Task scheduling center with high availability support.

.. code-block:: bash

   python -m zspider.dispatcher

Crawler
~~~~~~~

Worker process for executing crawl tasks.

.. code-block:: bash

   python -m zspider.crawler

Web Admin
~~~~~~~~~

Flask-based management interface.

.. code-block:: bash

   python -m zspider.web

Quick Start
-----------

1. Start external services (RabbitMQ, MongoDB, Memcached)
2. Configure ``zspider/confs/*.py`` files
3. Start Dispatcher, Crawler, and Web components
4. Access Web Admin at ``http://localhost:5000``

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`