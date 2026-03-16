# coding=utf-8
import unittest
from unittest import mock

from zspider.utils import http


class TestTwistedHttpHelpers(unittest.TestCase):
    def test_twisted_get_uses_agent_request(self):
        agent = mock.Mock()
        deferred = mock.Mock()
        deferred.addCallback = mock.Mock(return_value=deferred)
        agent.request.return_value = deferred

        with mock.patch.object(http, "Agent", return_value=agent) as agent_cls:
            result = http.twisted_get(
                "https://example.com",
                headers={"Accept": "text/html"},
                timeout=5,
            )

        self.assertIs(result, deferred)
        agent_cls.assert_called_once_with(http.reactor, connectTimeout=5)
        agent.request.assert_called_once()
        self.assertEqual(agent.request.call_args.args[0], b"GET")
        self.assertEqual(agent.request.call_args.args[1], b"https://example.com")
        self.assertEqual(
            agent.request.call_args.kwargs["headers"].getRawHeaders(b"Accept"),
            [b"text/html"],
        )
        self.assertIsNone(agent.request.call_args.kwargs["bodyProducer"])
        deferred.addCallback.assert_called_once_with(http.readBody)

    def test_twisted_post_encodes_body_and_headers(self):
        agent = mock.Mock()
        deferred = mock.Mock()
        deferred.addCallback = mock.Mock(return_value=deferred)
        agent.request.return_value = deferred

        with mock.patch.object(http, "Agent", return_value=agent):
            result = http.twisted_post(
                "https://example.com/api",
                data="name=value",
            )

        self.assertIs(result, deferred)
        agent.request.assert_called_once()
        self.assertEqual(agent.request.call_args.args[0], b"POST")
        self.assertEqual(agent.request.call_args.args[1], b"https://example.com/api")
        self.assertEqual(
            agent.request.call_args.kwargs["headers"].getRawHeaders(b"Content-Type"),
            [b"application/x-www-form-urlencoded"],
        )
        producer = agent.request.call_args.kwargs["bodyProducer"]
        self.assertIsInstance(producer, http.FileBodyProducer)
