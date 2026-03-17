# coding=utf-8
from unittest import TestCase

from zspider.confs import crawl_conf


class CrawlConfTest(TestCase):
    def test_browser_middleware_is_enabled(self):
        self.assertEqual(
            crawl_conf.DOWNLOADER_MIDDLEWARES["zspider.middlewares.BrowserMiddleware"],
            1,
        )
