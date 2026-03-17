# coding=utf-8
import logging

from scrapy import Request

from zspider.basespider import BaseSpider

__author__ = "zephor"

logger = logging.getLogger(__name__)


class BrowserSpider(BaseSpider):
    name = "browser"

    def __init__(self, *args, **kwargs):
        super(BrowserSpider, self).__init__(*args, **kwargs)
        self.start_urls = (self.parser.front_url,)

    def start_requests(self):
        for url in self.start_urls:
            request = Request(url, dont_filter=True)
            request.meta["_browser"] = True
            yield request

    def parse(self, response, **kwargs):
        """索引解析"""
        for r in self._parse_index(response):
            if not self.task_id.startswith("test_"):
                r.meta["_browser"] = True
            yield r
