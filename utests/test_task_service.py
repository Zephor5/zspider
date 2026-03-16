# coding=utf-8
import unittest
from types import SimpleNamespace
from unittest import mock

from zspider.services import task_service


class TestTaskService(unittest.TestCase):
    def test_build_task_rows_marks_subscription_and_stage(self):
        task = SimpleNamespace(
            id="task-1",
            name="运行中的任务",
            cron="*/5 * * * *",
            is_active=True,
            parser="index",
            spider="news",
            mender="tester",
            mtime="2026-03-16 10:00:00",
        )
        sub = SimpleNamespace(id="task-1")
        subscribe_qs = SimpleNamespace(only=mock.Mock(return_value=[sub]))
        latest_run = SimpleNamespace(
            task=SimpleNamespace(id="task-1"),
            status="failed",
            stage="parse",
            queued_at=SimpleNamespace(strftime=lambda _: "2026-03-16 09:58:00"),
            finished_at=SimpleNamespace(strftime=lambda _: "2026-03-16 10:00:00"),
            last_error_code="parse_failed",
            last_error="XPath 缺失",
            article_count=2,
            stored_count=0,
            publish_ok_count=0,
            publish_fail_count=0,
            publish_skip_count=0,
        )
        run_qs = SimpleNamespace(
            order_by=mock.Mock(
                return_value=SimpleNamespace(only=mock.Mock(return_value=[latest_run]))
            )
        )
        pub_model = mock.Mock()
        pub_model.objects.return_value = subscribe_qs
        run_model = mock.Mock()
        run_model.objects.return_value = run_qs

        with mock.patch.object(
            task_service, "PubSubscribe", pub_model
        ), mock.patch.object(task_service, "TaskRun", run_model):
            rows = task_service.build_task_rows([task])

        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["has_subscription"])
        self.assertEqual(rows[0]["stage_label"], "运行中")
        self.assertEqual(rows[0]["stage_class"], "success")
        self.assertEqual(rows[0]["recent_run"]["status_label"], "失败")
        self.assertIn("解析失败", rows[0]["recent_run"]["detail"])
        self.assertIn("文章 2 / 入库 0 / 发布成功 0", rows[0]["recent_run"]["summary"])

    def test_build_task_list_context_clears_prev_kwargs_when_empty(self):
        task_model = mock.Mock()
        task_model.objects.return_value.count.return_value = 0
        task_model.objects.return_value.paginate.return_value = SimpleNamespace(
            items=[]
        )

        with mock.patch.object(task_service, "Task", task_model), mock.patch.object(
            task_service, "build_task_rows", return_value=[]
        ):
            context = task_service.build_task_list_context("task_name", "demo", 1)

        self.assertEqual(context["count"], 0)
        self.assertEqual(context["prev_kwargs"], {})

    def test_toggle_task_returns_dispatcher_message(self):
        task = SimpleNamespace(id="task-1", is_active=False, cron="*/5 * * * *")
        task.save = mock.Mock()
        task_model = mock.Mock()
        task_model.objects.get_or_404.return_value = task

        with mock.patch.object(task_service, "Task", task_model), mock.patch.object(
            task_service,
            "urlopen",
            return_value=SimpleNamespace(read=lambda: b'{"data":"job loaded"}'),
        ):
            status, message = task_service.toggle_task("task-1", "127.0.0.1")

        self.assertTrue(status)
        self.assertEqual(message, "job loaded")
        self.assertTrue(task.is_active)
        task.save.assert_called_once_with()

    def test_build_recent_run_summary_handles_empty_state(self):
        summary = task_service._build_recent_run_summary(None)

        self.assertFalse(summary["exists"])
        self.assertEqual(summary["status_label"], "暂无运行记录")
