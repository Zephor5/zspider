# coding=utf-8
import importlib
import json
import sys
from types import SimpleNamespace
from unittest import mock

from twisted.trial.unittest import TestCase


sys.modules.setdefault("pooled_pika", SimpleNamespace(PooledConn=mock.Mock()))

crawler = importlib.import_module("zspider.crawler")


class FakeRequest(object):
    def __init__(self, path):
        self.path = path.encode("utf-8")
        self.headers = {}
        self.response_code = 200

    def setHeader(self, name, value):
        self.headers[name] = value

    def setResponseCode(self, code):
        self.response_code = code


class CrawlerDaemonHealthTest(TestCase):
    def test_readiness_payload_reports_not_ready_before_queue_setup(self):
        daemon = SimpleNamespace(
            crawlers=set(),
            _CrawlerDaemon__task_queue=None,
        )

        ready, payload = crawler.CrawlerDaemon.readiness_payload(daemon)

        self.assertFalse(ready)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["checks"]["task_queue"]["status"], "error")

    def test_readiness_payload_reports_ready_after_queue_setup(self):
        daemon = SimpleNamespace(
            crawlers={"crawler-1"},
            _conn=object(),
            _channel=object(),
            _CrawlerDaemon__task_queue=object(),
        )

        ready, payload = crawler.CrawlerDaemon.readiness_payload(daemon)

        self.assertTrue(ready)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["active_crawlers"], 1)


class CrawlerManageTest(TestCase):
    def test_healthz_returns_ok(self):
        daemon = mock.Mock()
        daemon.health_payload.return_value = {"status": "ok", "service": "crawler"}
        request = FakeRequest("/healthz")

        body = crawler.CrawlerManage(daemon).render_GET(request)

        self.assertEqual(
            request.headers["content-type"], "application/json;charset=UTF-8"
        )
        self.assertEqual(json.loads(body), {"status": "ok", "service": "crawler"})

    def test_readyz_returns_503_when_not_ready(self):
        daemon = mock.Mock()
        daemon.readiness_payload.return_value = (
            False,
            {"status": "error", "service": "crawler"},
        )
        request = FakeRequest("/readyz")

        body = crawler.CrawlerManage(daemon).render_GET(request)

        self.assertEqual(request.response_code, 503)
        self.assertEqual(json.loads(body), {"status": "error", "service": "crawler"})
