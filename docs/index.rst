.. zspider documentation master file

=======
ZSPIDER
=======

A self-hosted crawling platform for content monitoring and news aggregation.

|build-status|

.. |build-status| image:: https://readthedocs.org/projects/zspider/badge/?version=latest
   :target: http://zspider.readthedocs.org/en/latest/?badge=latest

ZSpider helps teams run recurring collection workflows for public web content such as news, announcements, company updates, and WeChat articles.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   developer_guide
   project_analysis
   desgin
   internal_message
   item_info

Overview
========

ZSpider focuses on three practical needs:

- schedule recurring collection jobs
- configure extraction rules through parsers
- review and manage results from a centralized backend

It is a better fit for content monitoring and information aggregation workflows than one-off crawler scripts.

Documentation Guide
===================

- ``developer_guide``: environment, configuration, components, parser model, and project structure
- ``project_analysis``: current codebase structure, runtime flow, strengths, and risks
- ``desgin``: architecture design notes
- ``internal_message``: internal messaging details
- ``item_info``: item and field model reference

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
