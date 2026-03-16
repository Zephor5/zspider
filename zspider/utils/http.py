# coding=utf-8
from io import BytesIO

from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.web.client import FileBodyProducer
from twisted.web.client import readBody
from twisted.web.http_headers import Headers

__author__ = "zephor"


def twisted_get(url, **kwargs):
    """
    :param url: url to get
    :param kwargs: headers, timeout
    :return: Deferred
    """
    return _request(url, **kwargs)


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
    return _request(url, **kwargs)


def _request(url, **kwargs):
    method = kwargs.pop("method", "GET")
    headers = Headers(_normalize_headers(kwargs.pop("headers", {})))
    postdata = kwargs.pop("postdata", None)
    timeout = kwargs.pop("timeout", None)

    agent = Agent(reactor, connectTimeout=timeout)
    body_producer = None
    if postdata is not None:
        body_producer = FileBodyProducer(BytesIO(_to_bytes(postdata)))

    deferred = agent.request(
        _to_bytes(method.upper()),
        _to_bytes(url),
        headers=headers,
        bodyProducer=body_producer,
    )
    deferred.addCallback(readBody)
    return deferred


def _normalize_headers(headers):
    normalized = {}
    for key, value in headers.items():
        if isinstance(value, (list, tuple)):
            normalized[_to_bytes(key)] = [_to_bytes(v) for v in value]
        else:
            normalized[_to_bytes(key)] = [_to_bytes(value)]
    return normalized


def _to_bytes(value):
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8")
