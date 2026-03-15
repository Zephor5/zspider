# coding=utf-8
import importlib
import json
import sys
from types import SimpleNamespace
from unittest import mock

from twisted.internet import defer
from twisted.trial.unittest import TestCase

from zspider.task_messages import TaskDispatchMessage

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

        with mock.patch.object(
            dispatcher.pooled_conn, "acquire", return_value=defer.succeed(fake_channel)
        ), mock.patch.object(
            dispatcher.pooled_conn, "release", return_value=None
        ), mock.patch.object(
            dispatcher.reactor,
            "callLater",
            side_effect=lambda delay, fn, *a, **kw: fn(*a, **kw),
        ):
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
            with mock.patch.object(
                dispatcher.time, "time", return_value=2
            ), mock.patch.object(dispatcher, "load_tasks", return_value=0):
                result = beat._on_beat(payload)

            self.assertEqual(dispatcher._state_, dispatcher.STATE_PENDING)
            self.assertEqual(
                json.loads(result)[dispatcher.UID]["status"], dispatcher.STATE_PENDING
            )
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

        self.assertEqual(
            request.headers["content-type"], "application/json;charset=UTF-8"
        )
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
        with mock.patch.object(
            dispatcher.scheduler,
            "remove_job",
            side_effect=dispatcher.JobLookupError("missing"),
        ):
            body = dispatcher.TaskManage().render_GET(request)

        res = json.loads(body)
        self.assertFalse(res["status"])
        self.assertIn("missing", res["data"])

    def test_render_get_load_returns_next_run_time(self):
        request = FakeRequest("/load/task-1/%s" % dispatcher.MANAGE_KEY)
        fake_job = SimpleNamespace(next_run_time="2026-03-12 09:30:00")
        with mock.patch.object(dispatcher, "load_tasks", return_value=fake_job):
            body = dispatcher.TaskManage().render_GET(request)

        res = json.loads(body)
        self.assertTrue(res["status"])
        self.assertIn("2026-03-12 09:30:00", res["data"])


class SendTest(TestCase):
    def test_on_send_publishes_message_and_returns_channel(self):
        sender = dispatcher.Send(
            TaskDispatchMessage(
                task_id="task-1",
                task_name="demo",
                spider="news",
                parser="index",
                needs_login=False,
            )
        )
        channel = mock.Mock()

        result = sender._on_send(channel)
        payload = json.loads(sender.msgs)

        channel.basic_publish.assert_called_once_with(
            dispatcher.EXCHANGE_PARAMS["exchange"],
            dispatcher.TASK_BIND_PARAMS["routing_key"],
            sender.msgs,
        )
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["task"]["id"], "task-1")
        self.assertEqual(payload["task"]["name"], "demo")
        self.assertFalse(sender._doing)
        self.assertIs(result, channel)

    def test_reset_state_sets_doing_false(self):
        sender = dispatcher.Send(
            TaskDispatchMessage(
                task_id="task-1",
                task_name="demo",
                spider="news",
                parser="index",
                needs_login=False,
            )
        )
        sender._doing = True

        sender._reset_state()

        self.assertFalse(sender._doing)

    def test_rand_reschedule_uses_scheduler_and_sets_max(self):
        sender = dispatcher.Send(
            TaskDispatchMessage(
                task_id="task-1",
                task_name="demo",
                spider="wechat",
                parser="index",
                needs_login=False,
            ),
            rand=True,
        )
        fake_now = 1000

        class FakeRunTime(object):
            def __sub__(self, other):
                return SimpleNamespace(total_seconds=lambda: 100)

        existing_job = SimpleNamespace(next_run_time=FakeRunTime())
        scheduled_job = SimpleNamespace(next_run_time="later")

        with mock.patch.object(
            dispatcher.scheduler, "get_job", return_value=existing_job
        ), mock.patch.object(
            dispatcher.scheduler, "add_job", return_value=scheduled_job
        ) as add_job, mock.patch.object(
            dispatcher.tzlocal, "get_localzone", return_value="UTC"
        ), mock.patch.object(
            dispatcher.datetime, "datetime"
        ) as mock_datetime, mock.patch.object(
            dispatcher.datetime, "timedelta", side_effect=lambda seconds: seconds
        ), mock.patch.object(
            dispatcher.random, "random", return_value=0.5
        ):
            mock_datetime.now.return_value = fake_now
            mock_datetime.now.side_effect = None
            sender._rand_reschedule()

        self.assertEqual(sender._max, 140)
        add_job.assert_called_once()
        self.assertEqual(add_job.call_args.kwargs["id"], "task-1")
        self.assertEqual(add_job.call_args.kwargs["replace_existing"], True)
        self.assertEqual(add_job.call_args.kwargs["run_date"], 1130.0)
