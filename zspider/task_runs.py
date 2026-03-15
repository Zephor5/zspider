# coding=utf-8
from datetime import datetime

from mongoengine import DoesNotExist

from zspider.confs.conf import INNER_IP
from zspider.models import RUN_STAGE_DISPATCH
from zspider.models import RUN_STAGE_FINISHED
from zspider.models import RUN_STATUS_FAILED
from zspider.models import RUN_STATUS_PARTIAL
from zspider.models import RUN_STATUS_QUEUED
from zspider.models import RUN_STATUS_RUNNING
from zspider.models import RUN_STATUS_SUCCESS
from zspider.models import TaskRun
from zspider.utils.models import Task


def create_task_run(task_id, task_name, spider, parser, trigger_type="schedule"):
    task = Task.objects.get(id=task_id)
    task_run = TaskRun(
        task=task,
        task_name=task_name,
        spider=spider,
        parser=parser,
        trigger_type=trigger_type,
        status=RUN_STATUS_QUEUED,
        stage=RUN_STAGE_DISPATCH,
    )
    task_run.save()
    return task_run


def mark_task_run_running(run_id, worker_ip=None):
    _update_task_run(
        run_id,
        set__status=RUN_STATUS_RUNNING,
        set__stage=RUN_STAGE_DISPATCH,
        set__started_at=datetime.now(),
        set__worker_ip=worker_ip or INNER_IP,
    )


def mark_task_run_stage(run_id, stage, latest_url=None):
    updates = {"set__stage": stage}
    if latest_url:
        updates["set__latest_url"] = latest_url
    _update_task_run(run_id, **updates)


def increment_task_run_metric(run_id, field_name, amount=1, latest_url=None):
    updates = {"inc__%s" % field_name: amount}
    if latest_url:
        updates["set__latest_url"] = latest_url
    _update_task_run(run_id, **updates)


def record_task_run_warning(run_id, stage, message, latest_url=None):
    updates = {"set__last_error_stage": stage, "set__last_error": str(message)}
    if latest_url:
        updates["set__latest_url"] = latest_url
    _update_task_run(run_id, **updates)


def record_task_run_issue(run_id, stage, code, message, latest_url=None):
    updates = {
        "set__last_error_stage": stage,
        "set__last_error_code": code,
        "set__last_error": str(message),
    }
    if latest_url:
        updates["set__latest_url"] = latest_url
    _update_task_run(run_id, **updates)


def fail_task_run(run_id, stage, code, message, latest_url=None):
    updates = {
        "set__status": RUN_STATUS_FAILED,
        "set__stage": stage,
        "set__last_error_stage": stage,
        "set__last_error_code": code,
        "set__last_error": str(message),
        "set__finished_at": datetime.now(),
    }
    if latest_url:
        updates["set__latest_url"] = latest_url
    _update_task_run(run_id, **updates)


def finish_task_run(run_id, close_reason="finished"):
    try:
        task_run = TaskRun.objects.get(id=run_id)
    except DoesNotExist:
        return

    if task_run.status == RUN_STATUS_FAILED:
        status = RUN_STATUS_FAILED
    elif task_run.store_fail_count or task_run.publish_fail_count:
        status = RUN_STATUS_PARTIAL
    else:
        status = RUN_STATUS_SUCCESS

    task_run.update(
        set__status=status,
        set__stage=RUN_STAGE_FINISHED,
        set__close_reason=close_reason,
        set__finished_at=datetime.now(),
    )


def _update_task_run(run_id, **updates):
    if not run_id:
        return
    TaskRun.objects(id=run_id).update_one(**updates)
