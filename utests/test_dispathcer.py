# coding=utf-8
import importlib
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
