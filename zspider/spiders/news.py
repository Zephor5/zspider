# coding=utf-8
import logging

from scrapy import FormRequest
from scrapy import Request

from zspider.basespider import BaseSpider

__author__ = "zephor"

logger = logging.getLogger(__name__)


class NewsSpider(BaseSpider):

    name = "news"

    def __init__(self, *args, **kwargs):
        super(NewsSpider, self).__init__(*args, **kwargs)
        self.start_urls = (self.parser.front_url,)

    def parse(self, response):
        """索引解析"""
        if self.parser.need_login:
            self.parser.to_login()
            request = FormRequest.from_response(
                response, formdata=self.parser.login_data, callback=self.parse
            )
            request.meta["_login"] = "doing"
            yield request
        elif "_login" in response.meta and response.meta["_login"] == "doing":
            if response.status != 200:
                logger.error("Login failed: %s" % self.parser, extra=self._extra)
                return
            response.meta["_login"] = "done"
            logger.info("Login successfully, begin to crawl", extra=self._extra)
            yield Request(self.parser.front_url, self.parse)
        else:
            for r in self._parse_index(response):
                yield r
