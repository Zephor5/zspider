# coding=utf-8
__author__ = "zephor"

import logging

from scrapy.http import HtmlResponse
from selenium import webdriver
from twisted.internet import threads

logger = logging.getLogger(__name__)


class SeleniumMiddleware(object):
    """
    selenium middleware
    """

    def __init__(self):
        options = webdriver.FirefoxOptions()
        options.headless = True
        self.driver = webdriver.Firefox(options=options)

    def process_request(self, request, spider):
        if "_selenium" not in request.meta:
            return None
        url = request.url
        d = threads.deferToThread(self.driver.get, url)

        def _gen_response(_):
            body = self.driver.find_element_by_xpath("//html").get_attribute(
                "outerHTML"
            )
            return HtmlResponse(url, body=body, request=request, encoding="utf-8")

        d.addCallback(_gen_response)
        return d

    def __del__(self):
        self.driver.close()
