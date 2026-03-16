# coding=utf-8
import unittest
from types import SimpleNamespace
from unittest import mock

from zspider.services import monitor_service


class TestMonitorService(unittest.TestCase):
    def test_build_log_list_context_loads_task_when_task_filter_present(self):
        task = SimpleNamespace(id="task-1", name="任务A")
        task_model = mock.Mock()
        task_model.objects.get_or_404.return_value = task

        query_rows = [{"ip": "127.0.0.1"}]
        query_qs = mock.Mock()
        query_qs.only.return_value.order_by.return_value.limit.return_value = query_rows
        query_qs.order_by.return_value.paginate.return_value = "LOGS"

        log_model = mock.Mock()
        log_model.objects.return_value = query_qs

        with mock.patch.object(monitor_service, "Task", task_model), mock.patch.object(
            monitor_service, "get_log_model_or_404", return_value=log_model
        ):
            context = monitor_service.build_log_list_context(
                part="crawler",
                page=1,
                ip="no",
                level=0,
                task_id="task-1",
                url="",
            )

        self.assertEqual(context["task"], task)
        self.assertEqual(context["logs"], "LOGS")
        log_model.objects.assert_called_with(task_id="task-1")

    def test_serialize_doc_maps_task_and_status(self):
        doc = SimpleNamespace(
            task=SimpleNamespace(name="示例任务"),
            status=1,
            to_mongo=lambda: SimpleNamespace(
                to_dict=lambda: {"_id": "doc-1", "title": "标题"}
            ),
        )
        item_model = mock.Mock()
        item_model.objects.get_or_404.return_value = doc

        with mock.patch.object(monitor_service, "Item", item_model):
            payload = monitor_service.serialize_doc("doc-1")

        self.assertEqual(payload["task"], "示例任务")
        self.assertEqual(payload["status"], "发布成功")

    def test_serialize_task_run_maps_labels(self):
        run = SimpleNamespace(
            task=SimpleNamespace(name="任务A"),
            status="failed",
            stage="parse",
            last_error_code="parse_failed",
            last_error_stage="parse",
            to_mongo=lambda: SimpleNamespace(
                to_dict=lambda: {"_id": "run-1", "task_name": "任务A"}
            ),
        )
        run_model = mock.Mock()
        run_model.objects.get_or_404.return_value = run

        with mock.patch.object(monitor_service, "TaskRun", run_model):
            payload = monitor_service.serialize_task_run("run-1")

        self.assertEqual(payload["task"], "任务A")
        self.assertEqual(payload["status"], "失败")
        self.assertEqual(payload["stage"], "解析")
        self.assertEqual(payload["last_error_code"], "解析失败")
        self.assertEqual(payload["last_error_stage"], "解析")

    def test_build_run_list_context_filters_task_status_and_error_code(self):
        task = SimpleNamespace(id="task-1")
        task_model = mock.Mock()
        task_model.objects.get_or_404.return_value = task
        run_qs = mock.Mock()
        run_qs.order_by.return_value.paginate.return_value = "RUNS"
        run_model = mock.Mock()
        run_model.objects.return_value = run_qs

        with mock.patch.object(monitor_service, "Task", task_model), mock.patch.object(
            monitor_service, "TaskRun", run_model
        ):
            context = monitor_service.build_run_list_context(
                page=2,
                task_id="task-1",
                status="failed",
                error_code="parse_failed",
            )

        self.assertEqual(context["task"], task)
        self.assertEqual(context["runs"], "RUNS")
        run_model.objects.assert_called_once_with(
            task=task, status="failed", last_error_code="parse_failed"
        )
