# coding=utf-8
import unittest
from types import SimpleNamespace
from unittest import mock

from zspider.parsers import BaseParser
from zspider.parsers import get_parser
from zspider.parsers.baseparser import BaseNewsParser
from zspider.parsers.index import IndexParser
from zspider.parsers.jsonparser import JSONParser

__author__ = "zephor"


class DemoParser(BaseNewsParser):
    def parse_index(self, response):
        return []

    def parse_article(self, response):
        return self._parse_article_field(response)


class FakeXPathNode(object):
    def __init__(self, text="", href=""):
        self._text = text
        self._href = href

    def xpath(self, expr):
        if expr == "@href":
            return FakeXPathResult([self._href])
        if "text()" in expr:
            return FakeXPathResult([self._text])
        return FakeXPathResult([])


class FakeXPathResult(object):
    def __init__(self, values):
        self._values = values

    def extract(self):
        return self._values

    def __iter__(self):
        return iter(self._values)


class FakeResponse(object):
    def __init__(self, url, xpath_map=None, body=""):
        self.url = url
        self._xpath_map = xpath_map or {}
        self._body = body
        self.body = body

    def xpath(self, expr):
        return FakeXPathResult(self._xpath_map.get(expr, []))

    def body_as_unicode(self):
        return self._body


class TestParsers(unittest.TestCase):
    def test_get_parser(self):
        class P(BaseParser):
            def __init__(self, task_id, task_name, task_conf=None, article_fields=None):
                super(P, self).__init__(task_name)
                self.task_id = task_id
                self.task_conf = task_conf
                self.article_fields = article_fields

        with mock.patch.dict("zspider.parsers.PARSERS", {"P": P}, clear=True):
            parser = get_parser(
                "P", "task-1", "task-name", task_conf="conf", article_fields=[1]
            )

        self.assertIsInstance(parser, P)
        self.assertEqual(parser.name, "task-name")
        self.assertEqual(parser.task_id, "task-1")
        self.assertEqual(parser.task_conf, "conf")
        self.assertEqual(parser.article_fields, [1])

    def test_base_news_parser_front_url_and_login(self):
        conf = SimpleNamespace(
            front_url="https://example.com/%(year)s/%(month)s/%(day)s/index.html",
            login_data={"u": "demo"},
            to_login="https://example.com/login",
        )
        parser = DemoParser("test_parser", "demo", task_conf=conf, article_fields=[])

        self.assertTrue(parser.need_login)
        self.assertEqual(parser.front_url, "https://example.com/login")

        parser.to_login()
        self.assertFalse(parser.need_login)
        self.assertIn("https://example.com/", parser.front_url)
        self.assertTrue(parser.front_url.endswith("/index.html"))

    def test_parse_article_field_xpath_regex_and_specify(self):
        article_fields = [
            SimpleNamespace(name="title", specify="", xpath="//h1/text()", re=""),
            SimpleNamespace(name="source", specify="ZSpider", xpath="", re=""),
            SimpleNamespace(
                name="src_time",
                specify="",
                xpath="//time/text()",
                re=r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})",
            ),
        ]
        conf = SimpleNamespace(front_url="https://example.com")
        parser = DemoParser(
            "test_parser", "demo", task_conf=conf, article_fields=article_fields
        )
        response = FakeResponse(
            "https://example.com/a1",
            xpath_map={
                "//h1/text()": [" Hello World "],
                "//time/text()": ["2026-03-11 08:30"],
            },
        )

        item = parser.parse_article(response)
        self.assertEqual(item["url"], "https://example.com/a1")
        self.assertEqual(item["title"], "Hello World")
        self.assertEqual(item["source"], "ZSpider")
        self.assertEqual(item["src_time"], "2026-03-11 08:30:00")

    def test_parse_article_field_regex_from_body(self):
        article_fields = [
            SimpleNamespace(name="content", specify="", xpath="", re=r"content=(\w+)"),
        ]
        conf = SimpleNamespace(front_url="https://example.com")
        parser = DemoParser(
            "test_parser", "demo", task_conf=conf, article_fields=article_fields
        )
        response = FakeResponse("https://example.com/a1", body="foo content=hello bar")

        item = parser.parse_article(response)
        self.assertEqual(item["content"], "hello")

    @mock.patch("zspider.parsers.baseparser.datetime")
    def test_parse_article_field_time_falls_back_to_now_when_only_partial_date(
        self, mock_datetime
    ):
        mock_datetime.datetime.now.return_value.strftime.return_value = (
            "2026-03-12 12:34:56"
        )
        article_fields = [
            SimpleNamespace(
                name="publish_time", specify="", xpath="//time/text()", re=""
            ),
        ]
        conf = SimpleNamespace(front_url="https://example.com")
        parser = DemoParser(
            "test_parser", "demo", task_conf=conf, article_fields=article_fields
        )
        response = FakeResponse(
            "https://example.com/a1", xpath_map={"//time/text()": ["2026-03"]}
        )

        item = parser.parse_article(response)
        self.assertEqual(item["publish_time"], "2026-03-12 12:34:56")

    @mock.patch("zspider.parsers.baseparser.datetime")
    def test_parse_article_field_time_adds_current_clock_when_missing_seconds(
        self, mock_datetime
    ):
        mock_datetime.datetime.now.return_value.strftime.return_value = "09:08:07"
        article_fields = [
            SimpleNamespace(
                name="publish_time", specify="", xpath="//time/text()", re=""
            ),
        ]
        conf = SimpleNamespace(front_url="https://example.com")
        parser = DemoParser(
            "test_parser", "demo", task_conf=conf, article_fields=article_fields
        )
        response = FakeResponse(
            "https://example.com/a1", xpath_map={"//time/text()": ["2026-03-11"]}
        )

        item = parser.parse_article(response)
        self.assertEqual(item["publish_time"], "2026-03-11 09:08:07")

    def test_index_parser_extracts_urls_from_xpath(self):
        conf = SimpleNamespace(
            front_url="https://example.com", url_xpath="//a/@href", url_re=""
        )
        parser = IndexParser("test_parser", "demo", task_conf=conf, article_fields=[])
        response = FakeResponse(
            "https://example.com",
            xpath_map={
                "//a/@href": [FakeXPathResult(["/a1"]), FakeXPathResult(["/a2"])]
            },
        )

        self.assertEqual(list(parser.parse_index(response)), [["/a1"], ["/a2"]])

    def test_index_parser_extracts_urls_from_regex(self):
        conf = SimpleNamespace(
            front_url="https://example.com", url_xpath="", url_re=r'url="([^"]+)"'
        )
        parser = IndexParser("test_parser", "demo", task_conf=conf, article_fields=[])
        response = FakeResponse(
            "https://example.com", body='url="https://a" url="https://b"'
        )

        self.assertEqual(list(parser.parse_index(response)), ["https://a", "https://b"])

    def test_index_parser_extracts_urls_from_regex_without_capture_group(self):
        conf = SimpleNamespace(
            front_url="https://example.com",
            url_xpath="",
            url_re=r"https://mil\.news\.sina\.com\.cn/zonghe/\d{4}-\d{2}-\d{2}/doc-[a-z0-9]+\.shtml",
        )
        parser = IndexParser("test_parser", "demo", task_conf=conf, article_fields=[])
        response = FakeResponse(
            "https://example.com",
            body=(
                "foo https://mil.news.sina.com.cn/zonghe/2026-03-18/doc-abc123.shtml "
                "bar https://mil.news.sina.com.cn/zonghe/2026-03-19/doc-def456.shtml"
            ),
        )

        self.assertEqual(
            list(parser.parse_index(response)),
            [
                "https://mil.news.sina.com.cn/zonghe/2026-03-18/doc-abc123.shtml",
                "https://mil.news.sina.com.cn/zonghe/2026-03-19/doc-def456.shtml",
            ],
        )

    def test_json_parser_extracts_nested_list_items(self):
        conf = SimpleNamespace(
            front_url="https://example.com",
            pre_boundary="",
            suf_boundary="",
            json_struct="items->[]->url",
        )
        parser = JSONParser("test_parser", "demo", task_conf=conf, article_fields=[])
        response = FakeResponse(
            "https://example.com", body='{"items": [{"url": "u1"}, {"url": "u2"}]}'
        )

        self.assertEqual(list(parser.parse_index(response)), ["u1", "u2"])

    def test_json_parser_extracts_indexed_item_with_boundaries(self):
        conf = SimpleNamespace(
            front_url="https://example.com",
            pre_boundary="callback(",
            suf_boundary=")",
            json_struct="items->[0]->url",
        )
        parser = JSONParser("test_parser", "demo", task_conf=conf, article_fields=[])
        response = FakeResponse(
            "https://example.com",
            body='callback({"items": [{"url": "u1"}, {"url": "u2"}]})',
        )

        self.assertEqual(list(parser.parse_index(response)), ["u1"])
