# ZSPIDER | [![Documentation Status](https://readthedocs.org/projects/zspider/badge/?version=latest)](http://zspider.readthedocs.org/en/latest/?badge=latest)
a distributed cron spider system

[中文说明](README.md)


## Python Requirements
- python3.7
- python3.8
- python3.9

## Components
- **dispatcher**
_dispatch center :_ auto detect to work.
- **crawler**
_crawler daemon :_ to process the crawl task
- **web**
_a web site :_ to manage this system.

## Resource Dependencis
rabbitmq, mongodb, memcached

## Notice
Docs are writing, but not that quick.

This project is ready to use. There are several resources to be prepared and configured to use.

Mind those source file containing `conf` in the filename. mainly: `conf.py`, `crawl_conf.py`, `dispatcher_conf.py`, `web_conf.py`

## Development
[dev](https://github.com/wish/dev) tool is preferred.

just run `dev zspider` to see options
