# coding=utf-8
import functools

from flask import session, abort, request
from crawler import TestCrawler

__author__ = 'zephor'


test_crawler = TestCrawler()
test_crawler.settings.set('ITEM_PIPELINES', {'zspider.pipelines.TestResultPipeLine': 100})


def acquire_admin(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if session['role'] != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return wrap


def acquire_xhr(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not request.is_xhr:
            abort(403)
        return f(*args, **kwargs)
    return wrap
