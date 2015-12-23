# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

SPIDERS = None


def _init():
    global SPIDERS
    from scrapy.spiderloader import SpiderLoader
    from crawl_conf import SPIDER_MODULES

    class _Settings(object):
        @staticmethod
        def getlist(key):
            return SPIDER_MODULES

    spider_loader = SpiderLoader(_Settings())
    SPIDERS = [(name, spider_loader.load(name).__name__) for name in spider_loader.list()]


if not SPIDERS:
    _init()
