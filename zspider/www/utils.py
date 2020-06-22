# coding=utf-8
import functools

from flask import abort
from flask import request
from flask import session

from zspider.crawler import TestCrawler

__author__ = "zephor"


test_crawler = TestCrawler()
test_crawler.settings.set(
    "ITEM_PIPELINES", {"zspider.pipelines.TestResultPipeLine": 100}
)


def acquire_admin(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if session["role"] != "admin":
            abort(403)
        return f(*args, **kwargs)

    return wrap


def acquire_xhr(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not is_xhr():
            abort(403)
        return f(*args, **kwargs)

    return wrap


def is_xhr():
    request_xhr_key = request.headers.get("X-Requested-With")
    return request_xhr_key and request_xhr_key == "XMLHttpRequest"
