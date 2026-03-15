# coding=utf-8
import json
from dataclasses import dataclass


class TaskMessageError(ValueError):
    pass


@dataclass(frozen=True)
class TaskDispatchMessage:
    task_id: str
    task_name: str
    spider: str
    parser: str
    needs_login: bool
    run_id: str = ""
    trigger_type: str = "schedule"
    version: int = 1

    @classmethod
    def from_task(cls, task, trigger_type="schedule"):
        return cls(
            task_id=str(task.id),
            task_name=task.name,
            spider=task.spider,
            parser=task.parser,
            needs_login=bool(task.is_login),
            trigger_type=trigger_type,
        )

    @classmethod
    def from_body(cls, body):
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        try:
            payload = json.loads(body)
        except (TypeError, ValueError) as exc:
            raise TaskMessageError("invalid task message body") from exc
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict):
            raise TaskMessageError("task message payload must be a dict")
        if payload.get("version") != 1:
            raise TaskMessageError("unsupported task message version")

        task = payload.get("task")
        run = payload.get("run", {})
        if not isinstance(task, dict):
            raise TaskMessageError("task message missing task section")
        if not isinstance(run, dict):
            raise TaskMessageError("task message run section must be a dict")

        required = ("id", "name", "spider", "parser", "needs_login")
        missing = [key for key in required if key not in task]
        if missing:
            raise TaskMessageError(
                "task message missing task fields: %s" % ", ".join(missing)
            )

        return cls(
            task_id=str(task["id"]),
            task_name=str(task["name"]),
            spider=str(task["spider"]),
            parser=str(task["parser"]),
            needs_login=bool(task["needs_login"]),
            run_id=str(run.get("id", "")),
            trigger_type=str(run.get("trigger_type", "schedule")),
        )

    def with_run_id(self, run_id):
        return TaskDispatchMessage(
            task_id=self.task_id,
            task_name=self.task_name,
            spider=self.spider,
            parser=self.parser,
            needs_login=self.needs_login,
            run_id=run_id,
            trigger_type=self.trigger_type,
            version=self.version,
        )

    def to_dict(self):
        return {
            "version": self.version,
            "task": {
                "id": self.task_id,
                "name": self.task_name,
                "spider": self.spider,
                "parser": self.parser,
                "needs_login": self.needs_login,
            },
            "run": {
                "id": self.run_id,
                "trigger_type": self.trigger_type,
            },
        }

    def to_json(self):
        return json.dumps(self.to_dict())
