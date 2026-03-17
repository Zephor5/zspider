# coding=utf-8
import unittest
from types import SimpleNamespace

from zspider.www.handlers import tasks


class TestTaskHandlers(unittest.TestCase):
    def test_verify_fields_accepts_specify_only_field(self):
        forms = [
            SimpleNamespace(
                name=SimpleNamespace(data="title"),
                xpath=SimpleNamespace(data="//h1/text()"),
                re=SimpleNamespace(data=""),
                specify=SimpleNamespace(data=""),
            ),
            SimpleNamespace(
                name=SimpleNamespace(data="content"),
                xpath=SimpleNamespace(data="//article//p/text()"),
                re=SimpleNamespace(data=""),
                specify=SimpleNamespace(data=""),
            ),
            SimpleNamespace(
                name=SimpleNamespace(data="src_time"),
                xpath=SimpleNamespace(data="//time/text()"),
                re=SimpleNamespace(data=""),
                specify=SimpleNamespace(data=""),
            ),
            SimpleNamespace(
                name=SimpleNamespace(data="source"),
                xpath=SimpleNamespace(data=""),
                re=SimpleNamespace(data=""),
                specify=SimpleNamespace(data="Python Insider"),
            ),
        ]

        self.assertTrue(tasks._verify_fields(forms))

    def test_with_active_replaces_existing_active_query(self):
        url = "/task/edit/task-1?active=0&page=2"

        result = tasks._with_active(url, 1)

        self.assertEqual("/task/edit/task-1?active=1&page=2", result)
