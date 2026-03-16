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
