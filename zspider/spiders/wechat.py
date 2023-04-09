# coding=utf-8
import logging

from scrapy.http import Request

from zspider.basespider import BaseSpider

__author__ = "zephor"

logger = logging.getLogger(__name__)


class WeChatSpider(BaseSpider):
    """
    参数说明：入口url的格式为 http://weixin.微信号
    """

    # in case antispider sougou
    custom_settings = {"CONCURRENT_REQUESTS_PER_DOMAIN": 1}

    name = "wechat"

    def __init__(self, *args, **kwargs):
        super(WeChatSpider, self).__init__(*args, **kwargs)
        self.wechat_id = self.parser.front_url
        self.start_urls = (
            "http://weixin.sogou.com/weixin?type=1&query=%s&ie=utf8" % self.wechat_id,
        )
        self._extra.update({"wechat_id": self.wechat_id})

    def parse(self, response, **kwargs):
        err = None
        res = response.css(".results>div:first-of-type")
        if res:
            res = res[0]
            res = res.xpath("@href").extract()
            if res:
                res = res[0]
                url = (
                    "http://weixin.sogou.com/gzhjs?cb=sogou.weixin.gzhcb&%s&t=1447729170941"
                    % res.split("?", 1)[1]
                )
                yield Request(url, self.parse_index)
            else:
                err = "没找到微信号链接"
        else:
            err = "没找到微信号"
        if err:
            logger.error(err, extra=self._extra)

    def parse_index(self, response):
        logger.info("parse index", extra=self._extra)
        for r in self._parse_index(response, self.parse_content):
            yield r

    def parse_content(self, response):
        f = response.xpath('//form[@name="authform"]')
        if not f:
            return self._parse_article(response)
        logger.warning("antispider", extra=self._extra)
