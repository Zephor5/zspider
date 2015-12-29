.. zspider documentation master file, created by
   sphinx-quickstart on Thu Dec 24 16:40:17 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 1
   :numbered:
   :hidden:

    desgin <desgin.rst>
    internal_message <internal_message.rst>
    item_info <item_info.rst>

=======
ZSPIDER
=======
a distributed spider system

Components
----------
- **dispatcher**
   *dispatch center :* auto detect to work.
- **crawler**
   *crawler daemon :* to process the crawl task
- **web**
   *a web site :* to manage this system.

Resource Dependencis
--------------------
rabbitmq, mongodb, memcached

Notice
------
This project doesn't actively develop now.  
But it's ready for production use. There are several resources to be prepared and configured to use.  

Indices and tables
------------------

* :doc:`item_info`
* :doc:`desgin`
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
