# coding=utf-8
from twisted.web.client import getPage

__author__ = "zephor"


def twisted_get(url, **kwargs):
    """
    :param url: url to get
    :param kwargs: headers, timeout
    :return: Deferred
    """
    return getPage(url, **kwargs)


def twisted_post(url, data=None, **kwargs):
    """
    :param url: url to post
    :param data: type str, dict like urlencoded
    :param kwargs: timeout
    :return: Deferred
    """
    kwargs.setdefault("method", "POST")
    kwargs.setdefault("headers", {"Content-Type": "application/x-www-form-urlencoded"})
    kwargs.setdefault("postdata", data)
    return getPage(url, **kwargs)
