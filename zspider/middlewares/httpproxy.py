# coding=utf-8
import logging

from scrapy.exceptions import NotConfigured
from scrapy.utils.httpobj import urlparse_cached

__author__ = "zephor"

logger = logging.getLogger(__name__)


class HttpProxyMiddleware(object):
    """
    http(s) proxy
    """

    def __init__(self, proxy):
        self.proxy = proxy
        if not self.proxy:
            raise NotConfigured

    @classmethod
    def from_settings(cls, settings):
        return cls(settings.get("HTTP_PROXY"))

    def process_request(self, request, spider):
        # ignore if proxy is already seted
        if "proxy" in request.meta:
            return

        parsed = urlparse_cached(request)
        scheme = parsed.scheme

        if scheme in ("http", "https"):
            logger.debug("add proxy %s" % self.proxy, extra={"url": request.url})
            request.meta["proxy"] = self.proxy
