# coding=utf-8
__author__ = "zephor"

import logging

from scrapy.http import HtmlResponse
from twisted.internet import threads

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - exercised by environment setup
    PlaywrightError = Exception
    sync_playwright = None


class BrowserMiddleware(object):
    """
    browser rendering middleware
    """

    def process_request(self, request, spider):
        if "_browser" not in request.meta:
            return None
        url = request.url
        if sync_playwright is None:
            logger.warning("browser renderer is not installed, skip browser rendering")
            return HtmlResponse(url, status=400, request=request)
        d = threads.deferToThread(self._render_page, url)

        def _gen_response(body):
            return HtmlResponse(url, body=body, request=request, encoding="utf-8")

        def _handle_error(failure):
            logger.warning(
                "error rendering page with browser middleware", exc_info=True
            )
            return HtmlResponse(url, status=502, request=request)

        d.addCallbacks(_gen_response, _handle_error)
        return d

    def _render_page(self, url):
        try:
            return render_page_html(url)
        except PlaywrightError:
            logger.warning("browser renderer failed to render %s", url, exc_info=True)
            raise


def render_page_html(url, timeout=30):
    if sync_playwright is None:
        raise RuntimeError("browser renderer is not installed")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            return page.content()
        finally:
            browser.close()
