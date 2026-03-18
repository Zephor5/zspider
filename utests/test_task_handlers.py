# coding=utf-8
import unittest
from types import SimpleNamespace
from unittest import mock

from zspider.www.handlers import app
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

    def test_is_return_edit_post_checks_hidden_flag(self):
        with app.test_request_context(
            "/task/add", method="POST", data={"_return_edit": "1"}
        ):
            self.assertTrue(tasks._is_return_edit_post())
        with app.test_request_context("/task/add", method="POST", data={}):
            self.assertFalse(tasks._is_return_edit_post())

    @mock.patch("zspider.www.handlers.tasks.build_index_test_rows")
    @mock.patch("zspider.www.handlers.tasks.validate_forms")
    @mock.patch("zspider.www.handlers.tasks.test_crawler")
    def test_task_test_index_xhr_returns_modal_panel(
        self, test_crawler, validate_forms, build_index_test_rows
    ):
        validate_forms.return_value = True
        test_crawler.res_q.get.return_value = [{"url": "https://example.com/1"}]
        build_index_test_rows.return_value = [
            {"url": "https://example.com/1", "title": "标题一"}
        ]

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "tester"
                session["role"] = "admin"

            response = client.post(
                "/task/test/index",
                data={
                    "name": "示例任务",
                    "spider": "news",
                    "parser": "IndexParser",
                    "front_url": "https://example.com/news/",
                    "url_xpath": "//article//a/@href",
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
            )

        html = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("标题一", html)
        self.assertIn("关闭测试结果", html)
        self.assertNotIn("返回继续编辑", html)

    @mock.patch("zspider.www.handlers.tasks.explore_index_page")
    def test_task_explore_index_renders_candidate_panel(self, explore_index_page):
        explore_index_page.return_value = {
            "title": "示例入口页",
            "final_url": "https://example.com/news/",
            "suggested_task_name": "示例入口页",
            "fetch_mode": {
                "label": "直接抓取",
                "recommended_spider": "news",
                "reason": "静态页面中已识别到候选链接区域，建议先直接抓取。",
            },
            "candidates": [
                {
                    "xpath": "//div//a[@href]/@href",
                    "count": 3,
                    "reason": "命中 3 条链接。",
                    "sample_texts": ["标题一"],
                    "sample_urls": ["https://example.com/1"],
                }
            ],
            "primary_article_url": "https://example.com/1",
            "preview_html": "<html><body>preview</body></html>",
        }

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "tester"
                session["role"] = "admin"

            response = client.post(
                "/task/explore/index",
                data={"front_url": "https://example.com/news/"},
            )

        html = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("点样本直接生成规则", html)
        self.assertIn("生成索引规则", html)
        self.assertIn("点击预览中的真实文章链接，直接加入正样本", html)
        self.assertIn("按“直接抓取”得到的页面结果展示", html)

    @mock.patch("zspider.www.handlers.tasks.explore_article_page")
    def test_task_explore_article_renders_field_candidates(self, explore_article_page):
        explore_article_page.return_value = {
            "title": "文章页示例",
            "final_url": "https://example.com/news/1",
            "fetch_mode": {
                "label": "直接抓取",
                "recommended_spider": "news",
                "reason": "页面结构基本一致，建议先直接抓取。",
            },
            "coverage": {
                "title": {"label": "标题", "count": 1, "status": "ready"},
                "content": {"label": "正文", "count": 0, "status": "missing"},
                "src_time": {"label": "时间", "count": 0, "status": "missing"},
                "source": {"label": "来源", "count": 0, "status": "missing"},
            },
            "field_candidates": {
                "title": [
                    {
                        "mode": "xpath",
                        "rule": "//h1/text()",
                        "preview": "标题一",
                        "reason": "优先命中详情页主标题节点。",
                    }
                ],
                "content": [],
                "src_time": [],
                "source": [],
            },
            "preview_html": "<html><body>preview</body></html>",
        }

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "tester"
                session["role"] = "admin"

            response = client.post(
                "/task/explore/article",
                data={"article_url": "https://example.com/news/1"},
            )

        html = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("点样本直接生成字段", html)
        self.assertIn("生成文章字段", html)
        self.assertIn("标成标题", html)
        self.assertIn("点击节点后，指定它属于哪个字段", html)
        self.assertIn("按“直接抓取”得到的页面结果展示", html)

    @mock.patch("zspider.www.handlers.tasks.generate_index_rule")
    def test_task_explore_index_generate_returns_json(self, generate_index_rule):
        generate_index_rule.return_value = {
            "final_url": "https://example.com/news/",
            "fetch_mode": {
                "label": "直接抓取",
                "recommended_spider": "news",
                "reason": "结构稳定。",
            },
            "rule_type": "xpath",
            "value": "//article//h3//a/@href",
            "parser_rule": {"rule_type": "xpath", "value": "//article//h3//a/@href"},
            "preview_rule": {"rule_type": "xpath", "value": "//article//h3//a"},
        }

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "tester"
                session["role"] = "admin"

            response = client.post(
                "/task/explore/index/generate",
                data={
                    "front_url": "https://example.com/news/",
                    "selected_urls": [
                        "https://example.com/1",
                        "https://example.com/2",
                    ],
                },
            )

        payload = response.get_json()
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["status"])
        self.assertEqual("//article//h3//a/@href", payload["data"]["value"])
        self.assertEqual("//article//h3//a", payload["data"]["preview_rule"]["value"])

    @mock.patch("zspider.www.handlers.tasks.generate_index_rule")
    def test_task_explore_index_generate_requires_llm(self, generate_index_rule):
        generate_index_rule.side_effect = RuntimeError("未配置页面探索模型。")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "tester"
                session["role"] = "admin"

            response = client.post(
                "/task/explore/index/generate",
                data={
                    "front_url": "https://example.com/news/",
                    "selected_urls": [
                        "https://example.com/1",
                        "https://example.com/2",
                    ],
                },
            )

        payload = response.get_json()
        self.assertEqual(200, response.status_code)
        self.assertFalse(payload["status"])
        self.assertIn("请先配置 ZSPIDER_LLM_API_KEY", payload["message"])

    @mock.patch("zspider.www.handlers.tasks.generate_article_fields")
    def test_task_explore_article_generate_returns_field_status(
        self, generate_article_fields
    ):
        generate_article_fields.return_value = {
            "fields": {
                "title": {"mode": "xpath", "value": "//h1/text()", "preview": "标题一"}
            },
            "written_fields": ["title"],
            "missing_fields": ["content", "src_time", "source"],
            "message": "已写入：标题。仍缺少：正文、时间、来源。",
        }

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "tester"
                session["role"] = "admin"

            response = client.post(
                "/task/explore/article/generate",
                data={"article_url": "https://example.com/news/1"},
            )

        payload = response.get_json()
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["status"])
        self.assertEqual(["title"], payload["data"]["written_fields"])
        self.assertIn("仍缺少", payload["data"]["message"])
