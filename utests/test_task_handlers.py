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
        self.assertIn("候选链接区域", html)
        self.assertIn("应用这组候选", html)
        self.assertIn("点击预览中的文章或区域，提取整块区域的链接 XPath", html)
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
        self.assertIn("标题候选", html)
        self.assertIn("应用到标题", html)
        self.assertIn("一键应用各字段首选候选", html)
        self.assertIn("点击文章节点，直接提取字段 XPath", html)
        self.assertIn("按“直接抓取”得到的页面结果展示", html)

    @mock.patch("zspider.www.handlers.tasks.infer_index_xpath")
    def test_task_explore_index_infer_returns_json(self, infer_index_xpath):
        infer_index_xpath.return_value = {
            "final_url": "https://example.com/news/",
            "fetch_mode": {
                "label": "直接抓取",
                "recommended_spider": "news",
                "reason": "结构稳定。",
            },
            "candidate": {
                "xpath": "//article//h3//a/@href",
                "count": 3,
                "sample_urls": ["https://example.com/1"],
                "sample_texts": ["标题一"],
                "reason": "已覆盖你标注的 2 个目标链接，额外命中 1 条链接。",
            },
        }

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "tester"
                session["role"] = "admin"

            response = client.post(
                "/task/explore/index/infer",
                data={
                    "front_url": "https://example.com/news/",
                    "urls": ["https://example.com/1", "https://example.com/2"],
                },
            )

        payload = response.get_json()
        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["status"])
        self.assertEqual(
            "//article//h3//a/@href", payload["data"]["candidate"]["xpath"]
        )
