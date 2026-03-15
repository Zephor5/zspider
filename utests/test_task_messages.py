# coding=utf-8
import unittest
from types import SimpleNamespace

from zspider.task_messages import TaskDispatchMessage
from zspider.task_messages import TaskMessageError


class TestTaskDispatchMessage(unittest.TestCase):
    def test_from_task_builds_explicit_message(self):
        task = SimpleNamespace(
            id="task-1",
            name="示例任务",
            spider="news",
            parser="index",
            is_login=1,
        )

        msg = TaskDispatchMessage.from_task(task)

        self.assertEqual(msg.task_id, "task-1")
        self.assertEqual(msg.task_name, "示例任务")
        self.assertTrue(msg.needs_login)
        self.assertEqual(
            msg.to_dict(),
            {
                "version": 1,
                "task": {
                    "id": "task-1",
                    "name": "示例任务",
                    "spider": "news",
                    "parser": "index",
                    "needs_login": True,
                },
                "run": {
                    "id": "",
                    "trigger_type": "schedule",
                },
            },
        )

    def test_from_body_restores_run_context(self):
        body = (
            '{"version": 1, "task": {"id": "task-1", "name": "示例任务", '
            '"spider": "news", "parser": "index", "needs_login": false}, '
            '"run": {"id": "run-1", "trigger_type": "schedule"}}'
        )

        msg = TaskDispatchMessage.from_body(body)

        self.assertEqual(msg.run_id, "run-1")
        self.assertEqual(msg.task_name, "示例任务")
        self.assertFalse(msg.needs_login)

    def test_from_body_rejects_invalid_payload(self):
        with self.assertRaises(TaskMessageError):
            TaskDispatchMessage.from_body('{"version": 2}')
