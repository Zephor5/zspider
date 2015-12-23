# coding=utf-8
import logging
import memcache
from scrapy.dupefilters import BaseDupeFilter
from scrapy.utils.request import request_fingerprint

__author__ = 'zephor'


logger = logging.getLogger(__name__)


class MemcachedDupeFilter(BaseDupeFilter):
    """Request Fingerprint duplicates filter"""

    def __init__(self, servers):
        self.mc = memcache.Client(servers)

    @classmethod
    def from_settings(cls, settings):
        servers = settings.getlist('DUPEFILTER_SERVERS')
        return cls(servers)

    def request_seen(self, request):
        fp = request_fingerprint(request)
        if self.mc.get(fp):
            return True
        return False

    def close(self, reason):
        self.mc.disconnect_all()

    def log(self, request, spider):
        logger.info("Filtered duplicate request: %(request)s", {'request': request}, extra={'url': request.url})

        spider.crawler.stats.inc_value('dupefilter/filtered', spider=spider)
