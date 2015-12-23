# coding=utf-8
import logging
import memcache
from scrapy.utils.request import request_fingerprint

__author__ = 'zephor'

logger = logging.getLogger(__name__)


class AddDupeFilterMiddleware(object):
    """在每个成功的需过滤请求最后添加过滤key"""

    def __init__(self, servers, debug=False):
        self.logdupes = True
        self.debug = debug
        self.mc = memcache.Client(servers)

    @classmethod
    def from_settings(cls, settings):
        debug = settings.getbool('DUPEFILTER_DEBUG')
        servers = settings.getlist('DUPEFILTER_SERVERS')
        return cls(servers, debug)

    def process_response(self, request, response, spider):
        if 'dupefilter' in request.meta and response.status in (200, 304):
            fp = request_fingerprint(request)
            if self.mc.add(fp, 1, time=604800):
                if self.debug:
                    logger.debug('add filter', extra={'url': request.url})
                spider.crawler.stats.inc_value('dupefilter/added', spider=spider)
            else:
                logger.warn('this request may handled before or something wrong with mc', extra={'url': request.url})
        return response
