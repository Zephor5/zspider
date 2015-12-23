# coding=utf-8
import json
import mock
import time
import dispatcher

from twisted.internet import defer, reactor
from twisted.trial.unittest import TestCase
from dispatcher_conf import STATE_DISPATCH

__author__ = 'zephor'


class HeartBeatTest(TestCase):
    @classmethod
    def setUpClass(cls):
        import init
        init.init()

    def setUp(self):
        self.patch_pc = mock.patch('dispatcher.pooled_conn')
        self.patch_hb = mock.patch('dispatcher.HeartBeat')

        fake_q = mock.Mock()
        fake_q.get.return_value = mock.Mock(), mock.Mock(), None, json.dumps(
            {"1.1.1.1": {"status": STATE_DISPATCH, "refresh": time.time()}})
        fake_channel = mock.Mock()
        fake_channel.basic_consume.return_value = fake_q, None
        fake_conn = mock.Mock()
        fake_conn.channel.return_value = fake_channel

        def _():
            _d = defer.Deferred()
            reactor.callLater(0, _d.callback, fake_conn)
            return _d

        pc = self.patch_pc.start()
        pc.prepare.side_effect = _
        pc.release.return_value = None

    def tearDown(self):
        self.patch_pc.stop()

    def test_startup(self):
        hb = self.patch_hb.start()

        def _():
            self.assertTrue(hb.called)
            self.patch_hb.stop()

        hb.side_effect = _

        d = dispatcher.startup(hb)
        return d

    def test_hb(self):
        d_ = defer.Deferred()

        def patch(_=None):
            return self.patch_hb.start()

        def done(hb):
            def __():
                d_.callback(None)
                self.patch_hb.stop()

            hb.side_effect = __

        d = dispatcher.startup()
        d.addCallback(patch)
        d.addCallback(done)
        return d_
