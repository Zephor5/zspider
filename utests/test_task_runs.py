# coding=utf-8
import unittest
from types import SimpleNamespace
from unittest import mock

from zspider import task_runs
from zspider.models import RUN_STATUS_FAILED
from zspider.models import RUN_STATUS_PARTIAL
from zspider.models import RUN_STATUS_SUCCESS


class TestTaskRunHelpers(unittest.TestCase):
    def test_create_task_run_uses_task_snapshot(self):
        task = SimpleNamespace(id="task-1")
        task_model = mock.Mock()
        task_model.objects.get.return_value = task

        with mock.patch.object(task_runs, "Task", task_model), mock.patch.object(
            task_runs, "TaskRun"
        ) as task_run_cls:
            task_run = mock.Mock()
            task_run_cls.return_value = task_run

            result = task_runs.create_task_run("task-1", "示例任务", "news", "index")

        task_run_cls.assert_called_once_with(
            task=task,
            task_name="示例任务",
            spider="news",
            parser="index",
            trigger_type="schedule",
            status="queued",
            stage="dispatch",
        )
        task_run.save.assert_called_once_with()
        self.assertIs(result, task_run)

    def test_finish_task_run_marks_partial_when_fail_counts_exist(self):
        run = SimpleNamespace(
            status="running",
            store_fail_count=1,
            publish_fail_count=0,
            update=mock.Mock(),
        )
        task_run_model = mock.Mock()
        task_run_model.objects.get.return_value = run

        with mock.patch.object(task_runs, "TaskRun", task_run_model):
            task_runs.finish_task_run("run-1")

        self.assertEqual(run.update.call_args.kwargs["set__status"], RUN_STATUS_PARTIAL)
        self.assertEqual(run.update.call_args.kwargs["set__stage"], "finished")

    def test_finish_task_run_keeps_failed_status(self):
        run = SimpleNamespace(
            status=RUN_STATUS_FAILED,
            store_fail_count=0,
            publish_fail_count=0,
            update=mock.Mock(),
        )
        task_run_model = mock.Mock()
        task_run_model.objects.get.return_value = run

        with mock.patch.object(task_runs, "TaskRun", task_run_model):
            task_runs.finish_task_run("run-1")

        self.assertEqual(run.update.call_args.kwargs["set__status"], RUN_STATUS_FAILED)

    def test_finish_task_run_marks_success_when_no_failures(self):
        run = SimpleNamespace(
            status="running",
            store_fail_count=0,
            publish_fail_count=0,
            update=mock.Mock(),
        )
        task_run_model = mock.Mock()
        task_run_model.objects.get.return_value = run

        with mock.patch.object(task_runs, "TaskRun", task_run_model):
            task_runs.finish_task_run("run-1")

        self.assertEqual(run.update.call_args.kwargs["set__status"], RUN_STATUS_SUCCESS)

    def test_record_task_run_issue_sets_error_code(self):
        task_run_model = mock.Mock()

        with mock.patch.object(task_runs, "TaskRun", task_run_model):
            task_runs.record_task_run_issue(
                "run-1", "publish", "publish_request_failed", "boom"
            )

        task_run_model.objects.assert_called_once_with(id="run-1")
        task_run_model.objects.return_value.update_one.assert_called_once_with(
            set__last_error_stage="publish",
            set__last_error_code="publish_request_failed",
            set__last_error="boom",
        )
