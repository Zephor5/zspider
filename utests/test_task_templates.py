# coding=utf-8
import unittest
from types import SimpleNamespace

from flask import render_template
from flask import session

from zspider.utils.models import ArticleFieldForm
from zspider.utils.models import PARSER_CONF_FORM_REF
from zspider.utils.models import TaskForm
from zspider.www.handlers import app


class TestTaskTemplates(unittest.TestCase):
    def _render_log_list(self, **context_overrides):
        class Pagination:
            def __init__(self, items):
                self.items = items
                self.page = 1
                self.has_prev = False
                self.has_next = False
                self.prev_num = None
                self.next_num = None

            def iter_pages(self):
                return [1]

        with app.app_context():
            context = {
                "part": "crawler",
                "task": SimpleNamespace(id="task-1", name="失败任务"),
                "task_id": "task-1",
                "level": 0,
                "levels": {0: "NOTSET", 20: "INFO"},
                "ips": {"127.0.0.1"},
                "ip": "no",
                "url": "https://example.com/a",
                "logs": Pagination(
                    [
                        SimpleNamespace(
                            id="log-1",
                            time=SimpleNamespace(
                                strftime=lambda _: "2026-03-15 12:00:00"
                            ),
                            level=20,
                            msg="parse failed",
                        )
                    ]
                ),
            }
            context.update(context_overrides)
            with app.test_request_context("/log/crawler?task_id=task-1"):
                session["user"] = "tester"
                session["role"] = "admin"
                return render_template("log.html", **context)

    def _render_task_doc_list(self, **context_overrides):
        class Pagination:
            def __init__(self, items):
                self.items = items
                self.page = 1
                self.has_prev = False
                self.has_next = False
                self.prev_num = None
                self.next_num = None

            def iter_pages(self):
                return [1]

        with app.app_context():
            context = {
                "statuses": {1: "发布成功"},
                "task": SimpleNamespace(id="task-1", name="失败任务"),
                "task_id": "task-1",
                "docs": Pagination(
                    [
                        SimpleNamespace(
                            id="doc-1",
                            title="标题A",
                            url="https://example.com/a",
                            task=SimpleNamespace(id="task-1", name="失败任务"),
                            status=1,
                            src_time="2026-03-15 11:59:00",
                            save_time="2026-03-15 12:00:00",
                        )
                    ]
                ),
            }
            context.update(context_overrides)
            with app.test_request_context("/task/doc?task_id=task-1"):
                session["user"] = "tester"
                session["role"] = "admin"
                return render_template("task/doc.html", **context)

    def _render_task_run_list(self, **context_overrides):
        class Pagination:
            def __init__(self, items):
                self.items = items
                self.page = 1
                self.has_prev = False
                self.has_next = False
                self.prev_num = None
                self.next_num = None

            def iter_pages(self):
                return [1]

        with app.app_context():
            context = {
                "task": SimpleNamespace(id="task-1", name="失败任务"),
                "task_id": "task-1",
                "status": "",
                "error_code": "",
                "statuses": {
                    "queued": "排队中",
                    "running": "运行中",
                    "success": "成功",
                    "partial": "部分成功",
                    "failed": "失败",
                },
                "error_codes": {
                    "parse_failed": "解析失败",
                    "publish_request_failed": "发布请求失败",
                },
                "stages": {
                    "dispatch": "调度",
                    "crawl": "抓取",
                    "parse": "解析",
                    "store": "入库",
                    "publish": "发布",
                    "finished": "完成",
                },
                "runs": Pagination(
                    [
                        SimpleNamespace(
                            id="run-1",
                            task=SimpleNamespace(id="task-1"),
                            task_name="失败任务",
                            spider="news",
                            parser="index",
                            status="failed",
                            stage="parse",
                            last_error_code="parse_failed",
                            last_error="XPath 缺失",
                            index_count=3,
                            article_count=1,
                            stored_count=0,
                            publish_ok_count=0,
                            publish_fail_count=0,
                            publish_skip_count=0,
                            latest_url="https://example.com/a",
                            queued_at="2026-03-15 12:00:00",
                            finished_at="2026-03-15 12:01:00",
                        )
                    ]
                ),
            }
            context.update(context_overrides)
            with app.test_request_context("/task/run"):
                session["user"] = "tester"
                session["role"] = "admin"
                return render_template("task/run.html", **context)

    def _render_task_list(self, **context_overrides):
        class Pagination:
            def __init__(self, items):
                self.items = items
                self.page = 1
                self.has_prev = False
                self.has_next = False
                self.prev_num = None
                self.next_num = None

            def iter_pages(self):
                return [1]

        with app.app_context():
            context = {
                "flashes": [],
                "prev_kwargs": {},
                "count": 2,
                "running_count": 1,
                "draft_count": 1,
                "tasks": Pagination(
                    [SimpleNamespace(id="task-1"), SimpleNamespace(id="task-2")]
                ),
                "task_rows": [
                    {
                        "id": "task-1",
                        "name": "运行中的任务",
                        "spider": "news",
                        "parser": "index",
                        "cron_text": "*/5 * * * *",
                        "has_subscription": True,
                        "mender": "tester",
                        "mtime": SimpleNamespace(
                            strftime=lambda _: "2026-03-15 12:00:00"
                        ),
                        "stage_label": "运行中",
                        "stage_class": "success",
                        "stage_hint": "重点查看最近结果和日志，确认抓取链路是否稳定。",
                        "is_active": True,
                        "recent_run": {
                            "status_label": "失败",
                            "status_class": "danger",
                            "detail": "解析失败 / 阶段：解析 / 结束：2026-03-15 12:01:00",
                            "summary": "文章 2 / 入库 0 / 发布成功 0",
                            "error_label": "解析失败",
                            "error_message": "XPath 缺失",
                        },
                    },
                    {
                        "id": "task-2",
                        "name": "待启动任务",
                        "spider": "news",
                        "parser": "wechat",
                        "cron_text": "0 * * * *",
                        "has_subscription": False,
                        "mender": "tester",
                        "mtime": SimpleNamespace(
                            strftime=lambda _: "2026-03-15 12:30:00"
                        ),
                        "stage_label": "待启动",
                        "stage_class": "warning",
                        "stage_hint": "建议先回到编辑页做索引/新闻测试，确认后再启动。",
                        "is_active": False,
                        "recent_run": {
                            "status_label": "暂无运行记录",
                            "status_class": "default",
                            "detail": "保存并启动任务后，这里会显示最近一次运行结果。",
                            "summary": "建议先完成索引测试和文章测试。",
                            "error_label": "",
                            "error_message": "",
                        },
                    },
                ],
            }
            context.update(context_overrides)
            with app.test_request_context("/task/list"):
                session["user"] = "tester"
                session["role"] = "admin"
                return render_template("task/list.html", **context)

    def _render_task_form(self, **context_overrides):
        with app.app_context():
            task_form = TaskForm(meta={"csrf": False})
            parser = task_form.parser.choices[0][0]
            conf_form = PARSER_CONF_FORM_REF[parser](meta={"csrf": False})
            article_field_forms = [
                ArticleFieldForm(name="title", meta={"csrf": False}),
            ]
            context = {
                "form": task_form,
                "conf_form": conf_form,
                "article_field_forms": article_field_forms,
                "fields_len": 1,
                "base_fields_len": 1,
                "is_add": False,
                "is_active": False,
                "initial_fetch_mode_summary": "直接抓取，建议抓取程序：news",
                "initial_fetch_mode_reason": "当前配置已保存抓取程序。",
                "initial_task_stage": "article",
                "task": SimpleNamespace(id="task-1", name="示例任务"),
                "explore_url": "https://example.com/news/",
                "explore_result": {
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
                            "xpath": '//div[contains(concat(" ", normalize-space(@class), " "), " news-list ")]//a[@href]/@href',
                            "count": 3,
                            "reason": "命中 3 条链接，其中站内链接 3 条，链接文本可读。",
                            "sample_texts": ["标题一", "标题二"],
                            "sample_urls": [
                                "https://example.com/1",
                                "https://example.com/2",
                            ],
                        }
                    ],
                    "primary_article_url": "https://example.com/1",
                    "preview_html": "<html><body><a data-explore-hit='1'>标题一</a></body></html>",
                },
                "explore_error": "",
                "article_explore_url": "https://example.com/news/1",
                "article_explore_result": {
                    "title": "文章页示例",
                    "final_url": "https://example.com/news/1",
                    "fetch_mode": {
                        "label": "直接抓取",
                        "recommended_spider": "news",
                        "reason": "页面结构基本一致，建议先直接抓取。",
                    },
                    "coverage": {
                        "title": {"label": "标题", "count": 1, "status": "ready"},
                        "content": {"label": "正文", "count": 1, "status": "ready"},
                        "src_time": {"label": "时间", "count": 1, "status": "ready"},
                        "source": {"label": "来源", "count": 1, "status": "ready"},
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
                        "content": [
                            {
                                "mode": "xpath",
                                "rule": "//article//*[self::p or self::li]//text()",
                                "preview": "正文内容",
                                "reason": "这块区域包含较长正文段落，适合作为正文主容器。",
                            }
                        ],
                        "src_time": [
                            {
                                "mode": "xpath",
                                "rule": "//time/@datetime",
                                "preview": "2026-03-17 10:00:00",
                                "reason": "优先使用 time 标签中的 datetime 属性。",
                            }
                        ],
                        "source": [
                            {
                                "mode": "specify",
                                "value": "Python Insider",
                                "preview": "Python Insider",
                                "reason": "优先使用页面声明的站点名称。",
                            }
                        ],
                    },
                    "preview_html": "<html><body><h1 data-explore-hit='1'>标题一</h1></body></html>",
                },
                "article_explore_error": "",
            }
            context.update(context_overrides)
            with app.test_request_context("/task/edit/task-1"):
                session["user"] = "tester"
                session["role"] = "admin"
                return render_template("task/add.html", **context)

    def test_edit_task_template_exposes_debug_shortcuts(self):
        html = self._render_task_form()

        self.assertIn("入口页探索面板", html)
        self.assertIn("文章页字段探索面板", html)
        self.assertIn("任务配置承接区", html)
        self.assertIn("运行观察", html)
        self.assertIn("另存为新任务", html)
        self.assertIn("/task/doc?task_id=task-1", html)
        self.assertIn("/task/run?task_id=task-1", html)
        self.assertIn("/log/crawler?task_id=task-1", html)
        self.assertIn("先复核页面，再调整规则", html)
        self.assertIn("生成文章字段", html)
        self.assertIn("标成标题", html)
        self.assertIn("点击预览中的真实文章链接，直接加入正样本", html)
        self.assertIn("点样本直接生成规则", html)
        self.assertIn("生成索引规则", html)
        self.assertIn("点击节点后，指定它属于哪个字段", html)
        self.assertIn("正在获取页面并准备点选预览", html)
        self.assertIn("按“直接抓取”得到的页面结果展示", html)
        self.assertIn("zspider-preview-command", html)
        self.assertIn("generateIndexRuleByMarkers", html)
        self.assertNotIn("preview-add-index-marker", html)
        self.assertNotIn("preview-apply-index-region", html)
        self.assertNotIn("preview-apply-index-link", html)
        self.assertNotIn("preview-apply-inferred-index", html)
        self.assertNotIn("节点 XPath", html)
        self.assertNotIn("文本 XPath", html)
        self.assertIn("refreshArticlePreviewHighlights", html)
        self.assertIn('data-suggested-task-name="示例入口页"', html)
        self.assertIn('name="return_path"', html)
        self.assertIn('name="save_path"', html)

    def test_add_task_template_hides_edit_shortcuts(self):
        html = self._render_task_form(is_add=True, task=None)

        self.assertIn("任务配置承接区", html)
        self.assertNotIn("运行观察", html)
        self.assertNotIn("另存为新任务", html)
        self.assertIn("探索入口页", html)

    def test_test_result_template_formats_article_preview(self):
        with app.app_context():
            task_form = TaskForm(meta={"csrf": False})
            conf_form = PARSER_CONF_FORM_REF[task_form.parser.choices[0][0]](
                meta={"csrf": False}
            )
            with app.test_request_context("/task/test/article"):
                session["user"] = "tester"
                session["role"] = "admin"
                html = render_template(
                    "task/test.html",
                    done=True,
                    target="article",
                    res=[{"title": "新闻标题", "content": "正文内容"}],
                    index_result_rows=[],
                    article_result_rows=[
                        {
                            "field": "title",
                            "label": "标题",
                            "value": "新闻标题",
                            "missing": False,
                            "config_text": "当前 XPath：//h1/text()",
                        },
                        {
                            "field": "content",
                            "label": "正文",
                            "value": "正文内容",
                            "missing": False,
                            "config_text": "当前 XPath：//article//p//text()",
                        },
                    ],
                    form=task_form,
                    conf_form=conf_form,
                    article_field_forms=[],
                    submitted_items=[("name", "示例任务"), ("return_path", "/task/add")],
                    return_path="/task/add",
                    save_draft_url="/task/add?active=0",
                    save_start_url="/task/add?active=1",
                    test_index_url="/task/test/index",
                    test_article_url="/task/test/article",
                    modal_mode=False,
                )

        self.assertIn("测试新闻结果", html)
        self.assertIn("字段预览", html)
        self.assertIn("新闻标题", html)
        self.assertIn("正文内容", html)
        self.assertIn("当前 XPath：//h1/text()", html)
        self.assertIn("返回继续编辑", html)
        self.assertIn("直接保存", html)
        self.assertIn("保存并启动", html)
        self.assertIn('form method="post" action="/task/add"', html)
        self.assertIn('name="_return_edit" value="1"', html)

    def test_test_result_template_formats_index_preview(self):
        with app.app_context():
            task_form = TaskForm(meta={"csrf": False})
            conf_form = PARSER_CONF_FORM_REF[task_form.parser.choices[0][0]](
                meta={"csrf": False}
            )
            with app.test_request_context("/task/test/index"):
                session["user"] = "tester"
                session["role"] = "admin"
                html = render_template(
                    "task/test.html",
                    done=True,
                    target="index",
                    res=[SimpleNamespace(url="https://example.com/a")],
                    index_result_rows=[
                        {"url": "https://example.com/a", "title": "标题一"}
                    ],
                    form=task_form,
                    conf_form=conf_form,
                    article_field_forms=[],
                    submitted_items=[("name", "示例任务"), ("return_path", "/task/add")],
                    return_path="/task/add",
                    save_draft_url="/task/add?active=0",
                    save_start_url="/task/add?active=1",
                    test_index_url="/task/test/index",
                    test_article_url="/task/test/article",
                    modal_mode=False,
                )

        self.assertIn("测试索引结果", html)
        self.assertIn("抓取到的入口链接", html)
        self.assertIn("标题一", html)
        self.assertIn("https://example.com/a", html)
        self.assertIn("继续测试新闻", html)
        self.assertNotIn('btn btn-success" type="submit">直接保存', html)
        self.assertIn('name="_return_edit" value="1"', html)

    def test_task_list_template_surfaces_workflow_and_status(self):
        html = self._render_task_list()

        self.assertIn("任务总览", html)
        self.assertIn("推荐操作路径", html)
        self.assertIn("运行中的任务", html)
        self.assertIn("待启动任务", html)
        self.assertIn("继续配置", html)
        self.assertIn("最近结果", html)
        self.assertIn("运行历史", html)
        self.assertIn("最近日志", html)
        self.assertIn("运行中", html)
        self.assertIn("待启动", html)
        self.assertIn("暂无运行记录", html)
        self.assertIn("XPath 缺失", html)

    def test_task_list_template_marks_subscription_state(self):
        html = self._render_task_list()

        self.assertIn("订阅：</strong>已配置", html)
        self.assertIn("订阅：</strong>未配置", html)
        self.assertIn("编辑订阅", html)
        self.assertIn("添加订阅", html)

    def test_task_run_template_surfaces_error_classification(self):
        html = self._render_task_run_list()

        self.assertIn("运行历史", html)
        self.assertIn("全部失败类型", html)
        self.assertIn("解析失败", html)
        self.assertIn("XPath 缺失", html)
        self.assertIn("查看最近结果", html)
        self.assertIn("查看 crawler 日志", html)

    def test_task_doc_template_surfaces_linked_navigation(self):
        html = self._render_task_doc_list()

        self.assertIn("当前任务：失败任务", html)
        self.assertIn("查看运行历史", html)
        self.assertIn("查看 crawler 日志", html)
        self.assertIn(
            "/log/crawler?task_id=task-1&amp;url=https%3A%2F%2Fexample.com%2Fa", html
        )

    def test_log_template_surfaces_linked_navigation(self):
        html = self._render_log_list()

        self.assertIn("当前任务：失败任务", html)
        self.assertIn("查看运行历史", html)
        self.assertIn("查看最近结果", html)
        self.assertIn("按 url 过滤", html)
