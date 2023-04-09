# coding=utf-8
__author__ = "zephor"

import logging

from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from twisted.internet import threads

logger = logging.getLogger(__name__)


class SeleniumMiddleware(object):
    """
    selenium middleware
    """

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.headless = True
        try:
            self.driver = webdriver.Chrome(options=options)
        except WebDriverException:
            logger.warning("error starting selenium spider", exc_info=True)
            self.driver = None

    def process_request(self, request, spider):
        if "_selenium" not in request.meta:
            return None
        url = request.url
        if self.driver is None:
            return HtmlResponse(url, status=400)
        d = threads.deferToThread(self.driver.get, url)

        def _gen_response(_):
            body = self.driver.find_element(By.XPATH, "//html").get_attribute(
                "outerHTML"
            )
            return HtmlResponse(url, body=body, request=request, encoding="utf-8")

        d.addCallback(_gen_response)
        return d

    def __del__(self):
        self.driver.close()
