# coding=utf-8
import unittest
from unittest import mock

from lxml import html

from zspider.services import explorer_ai


class _FakeStatusError(Exception):
    def __init__(self, status_code, response):
        super(_FakeStatusError, self).__init__("status error")
        self.status_code = status_code
        self.response = response


class TestExplorerAI(unittest.TestCase):
    @mock.patch("zspider.services.explorer_ai._call_llm")
    @mock.patch("zspider.services.explorer_ai._ensure_llm_ready")
    @mock.patch("zspider.services.explorer_ai.page_explorer.get_cached_article_context")
    @mock.patch("zspider.services.explorer_ai.page_explorer._load_page_variants")
    def test_generate_article_fields_prefers_cached_article_context(
        self,
        load_page_variants,
        get_cached_article_context,
        ensure_llm_ready,
        call_llm,
    ):
        del ensure_llm_ready
        get_cached_article_context.return_value = {
            "final_url": "https://example.com/news/1",
            "fetch_mode": {"label": "直接抓取"},
            "rendered_html": """
            <html><body>
              <h1>缓存标题</h1>
              <article><p>cached article body with enough content to validate.</p></article>
            </body></html>
            """,
        }
        call_llm.return_value = {
            "title": {"mode": "xpath", "value": "//h1/text()"},
            "content": {"mode": "xpath", "value": "//article//p//text()"},
        }

        result = explorer_ai.generate_article_fields(
            "https://example.com/news/1",
            {"title": {"type": "title", "node_xpath": "//h1"}},
            timeout=12,
        )

        self.assertEqual("//h1/text()", result["fields"]["title"]["value"])
        load_page_variants.assert_not_called()
        payload = call_llm.call_args.args[0]
        self.assertEqual("https://example.com/news/1", payload["page_url"])
        self.assertIn("cached", payload["rendered_html"])
        self.assertEqual(["title", "content"], result["written_fields"])
        self.assertEqual(["src_time", "source"], result["missing_fields"])

    def test_generate_index_rule_normalizes_xpath_and_separates_preview_rule(self):
        with mock.patch("zspider.services.explorer_ai._ensure_llm_ready"), mock.patch(
            "zspider.services.explorer_ai.page_explorer._load_page_variants"
        ) as load_page_variants, mock.patch(
            "zspider.services.explorer_ai.page_explorer._extract_index_candidates"
        ) as extract_index_candidates, mock.patch(
            "zspider.services.explorer_ai.page_explorer._detect_fetch_mode"
        ) as detect_fetch_mode, mock.patch(
            "zspider.services.explorer_ai.page_explorer._select_effective_doc"
        ) as select_effective_doc, mock.patch(
            "zspider.services.explorer_ai._call_llm"
        ) as call_llm:
            fake_doc = html.fromstring(
                "<html><body><article><h3><a href='/1'>A</a></h3></article></body></html>"
            )
            load_page_variants.return_value = {
                "final_url": "https://example.com/news/",
                "static_doc": fake_doc,
                "browser_doc": None,
            }
            extract_index_candidates.return_value = []
            detect_fetch_mode.return_value = {"label": "直接抓取"}
            select_effective_doc.return_value = fake_doc
            call_llm.return_value = {
                "rule_type": "xpath",
                "value": "//article//h3//a[@href]",
            }

            result = explorer_ai.generate_index_rule(
                "https://example.com/news/",
                ["https://example.com/1", "https://example.com/2"],
            )

        self.assertEqual("//article//h3//a[@href]/@href", result["value"])
        self.assertEqual("//article//h3//a[@href]", result["preview_rule"]["value"])

    @mock.patch("zspider.services.explorer_ai._call_llm")
    @mock.patch("zspider.services.explorer_ai._ensure_llm_ready")
    @mock.patch("zspider.services.explorer_ai.page_explorer.get_cached_article_context")
    def test_generate_article_fields_validates_and_falls_back_to_points(
        self, get_cached_article_context, ensure_llm_ready, call_llm
    ):
        del ensure_llm_ready
        get_cached_article_context.return_value = {
            "final_url": "https://example.com/news/1",
            "fetch_mode": {"label": "直接抓取"},
            "rendered_html": """
            <html><body>
              <h1>标题一</h1>
              <div class="date-source"><span class="date">2026-03-17 10:00</span><a class="source">示例来源</a></div>
              <article><p>第一段正文，长度足够用于校验。</p><p>第二段正文，继续补充更多细节。</p></article>
            </body></html>
            """,
        }
        call_llm.return_value = {
            "title": {"mode": "xpath", "value": "//h1/text()"},
            "content": {"mode": "xpath", "value": "//article//p//text()"},
        }

        result = explorer_ai.generate_article_fields(
            "https://example.com/news/1",
            {
                "src_time": {
                    "type": "src_time",
                    "text_xpath": '//div[@class="date-source"]//span[@class="date"]//text()',
                },
                "source": {
                    "type": "source",
                    "text_xpath": '//div[@class="date-source"]//a[@class="source"]//text()',
                },
            },
        )

        self.assertEqual(
            ["title", "content", "src_time", "source"], result["written_fields"]
        )
        self.assertEqual([], result["missing_fields"])
        self.assertIn("已写入", result["message"])

    def test_call_llm_uses_openai_tool_result(self):
        fake_tool_call = mock.Mock()
        fake_tool_call.function.arguments = '{"rule_type":"xpath","value":"//a/@href"}'
        fake_message = mock.Mock()
        fake_message.tool_calls = [fake_tool_call]
        fake_message.content = ""
        fake_response = mock.Mock()
        fake_response.choices = [mock.Mock(message=fake_message)]
        fake_client = mock.Mock()
        fake_client.chat.completions.create.return_value = fake_response

        with mock.patch(
            "zspider.services.explorer_ai._get_openai_client_for_timeout",
            return_value=(fake_client, Exception, _FakeStatusError),
        ):
            result = explorer_ai._call_llm(
                {"foo": "bar"},
                "system",
                explorer_ai._index_tool_schema(),
                timeout=12,
            )

        self.assertEqual({"rule_type": "xpath", "value": "//a/@href"}, result)
        fake_client.chat.completions.create.assert_called_once()
        request_kwargs = fake_client.chat.completions.create.call_args.kwargs
        self.assertEqual("required", request_kwargs["tool_choice"])

    def test_call_llm_surfaces_status_error(self):
        fake_client = mock.Mock()
        fake_client.chat.completions.create.side_effect = _FakeStatusError(
            401, "bad auth"
        )

        with mock.patch(
            "zspider.services.explorer_ai._get_openai_client_for_timeout",
            return_value=(fake_client, Exception, _FakeStatusError),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                explorer_ai._call_llm(
                    {"foo": "bar"},
                    "system",
                    explorer_ai._index_tool_schema(),
                    timeout=12,
                )

        self.assertIn("401", str(ctx.exception))

    def test_call_llm_surfaces_timeout_hint(self):
        fake_client = mock.Mock()
        fake_client.chat.completions.create.side_effect = RuntimeError("ReadTimeout")

        with mock.patch(
            "zspider.services.explorer_ai._get_openai_client_for_timeout",
            return_value=(fake_client, Exception, _FakeStatusError),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                explorer_ai._call_llm(
                    {"foo": "bar"},
                    "system",
                    explorer_ai._index_tool_schema(),
                    timeout=45,
                )

        self.assertIn("模型请求超时", str(ctx.exception))
        self.assertIn("45s", str(ctx.exception))

    def test_call_llm_falls_back_to_message_content(self):
        fake_message = mock.Mock()
        fake_message.tool_calls = []
        fake_message.content = '{"rule_type":"xpath","value":"//a/@href"}'
        fake_response = mock.Mock()
        fake_response.choices = [mock.Mock(message=fake_message)]
        fake_client = mock.Mock()
        fake_client.chat.completions.create.return_value = fake_response

        with mock.patch(
            "zspider.services.explorer_ai._get_openai_client_for_timeout",
            return_value=(fake_client, Exception, _FakeStatusError),
        ):
            result = explorer_ai._call_llm(
                {"foo": "bar"},
                "system",
                explorer_ai._index_tool_schema(),
                timeout=12,
            )

        self.assertEqual({"rule_type": "xpath", "value": "//a/@href"}, result)

    def test_get_openai_client_for_timeout_requires_package(self):
        real_import = __import__

        def raising_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=raising_import):
            with self.assertRaises(RuntimeError) as ctx:
                explorer_ai._get_openai_client_for_timeout(10)

        self.assertIn("未安装 openai 包", str(ctx.exception))
