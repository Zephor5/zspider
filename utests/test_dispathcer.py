# coding=utf-8
import importlib
import json
import sys
from types import SimpleNamespace
from unittest import mock

from twisted.internet import defer
from twisted.trial.unittest import TestCase

__author__ = "zephor"


# preload a fake pooled_pika module so dispatcher can be imported in test env
sys.modules.setdefault("pooled_pika", SimpleNamespace(PooledConn=mock.Mock()))

dispatcher = importlib.import_module("zspider.dispatcher")


class DispatcherStartupTest(TestCase):
    def test_startup_calls_main_job_after_queue_setup(self):
        fake_channel = mock.Mock()
        fake_channel.exchange_declare.return_value = defer.succeed(None)
        fake_channel.queue_declare.return_value = defer.succeed(None)
        fake_channel.queue_bind.return_value = defer.succeed(None)

        with mock.patch.object(dispatcher.pooled_conn, "acquire", return_value=defer.succeed(fake_channel)), \
             mock.patch.object(dispatcher.pooled_conn, "release", return_value=None), \
             mock.patch.object(dispatcher.reactor, "callLater", side_effect=lambda delay, fn, *a, **kw: fn(*a, **kw)):
            main_job = mock.Mock()
            d = dispatcher.startup(main_job)

        def _assert(_):
            main_job.assert_called_once_with()

        d.addCallback(_assert)
        return d


class DispatcherHeartbeatTest(TestCase):
    def test_clear_expire_removes_only_expired_nodes(self):
        nodes = {
            "expired-1": {"refresh": 1},
            "active": {"refresh": 100},
            "expired-2": {"refresh": 2},
        }

        expire = getattr(dispatcher.HeartBeat, "_HeartBeat__expire")
        with mock.patch.object(dispatcher.time, "time", return_value=expire + 10):
            dispatcher.HeartBeat._HeartBeat__clear_expire(nodes)

        self.assertEqual(nodes, {"active": {"refresh": 100}})

    def test_on_beat_promotes_waiting_node_to_pending_when_cluster_empty(self):
        beat = object.__new__(dispatcher.HeartBeat)
        original_state = dispatcher._state_
        dispatcher._state_ = dispatcher.STATE_WAITING
        payload = '{"other": {"status": %d, "refresh": 1}}' % dispatcher.STATE_WAITING

        try:
            with mock.patch.object(dispatcher.time, "time", return_value=2), \
                 mock.patch.object(dispatcher, "load_tasks", return_value=0):
                result = beat._on_beat(payload)

            self.assertEqual(dispatcher._state_, dispatcher.STATE_PENDING)
            self.assertEqual(json.loads(result)[dispatcher.UID]["status"], dispatcher.STATE_PENDING)
        finally:
            dispatcher._state_ = original_state


class FakeRequest(object):
    def __init__(self, path):
        self.path = path.encode("utf-8")
        self.headers = {}

    def setHeader(self, name, value):
        self.headers[name] = value


class TaskManageTest(TestCase):
    def test_render_get_rejects_invalid_manage_key(self):
        request = FakeRequest("/reload/wrong-key")
        body = dispatcher.TaskManage().render_GET(request)
        res = json.loads(body)

        self.assertEqual(request.headers["content-type"], "application/json;charset=UTF-8")
        self.assertFalse(res["status"])
        self.assertEqual(res["data"], "no authenticated")

    def test_render_get_reload_calls_load_tasks(self):
        request = FakeRequest("/reload/%s" % dispatcher.MANAGE_KEY)
        with mock.patch.object(dispatcher, "load_tasks", return_value=3) as load_tasks:
            body = dispatcher.TaskManage().render_GET(request)

        res = json.loads(body)
        load_tasks.assert_called_once_with()
        self.assertTrue(res["status"])
        self.assertEqual(res["data"], "3 tasks loaded")

    def test_render_get_remove_missing_job_returns_error(self):
        request = FakeRequest("/remove/task-1/%s" % dispatcher.MANAGE_KEY)
        with mock.patch.object(dispatcher.scheduler, "remove_job", side_effect=dispatcher.JobLookupError("missing")):
            body = dispatcher.TaskManage().render_GET(request)

        res = json.loads(body)
        self.assertFalse(res["status"])
        self.assertIn("missing", res["data"])
