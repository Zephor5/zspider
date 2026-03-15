# coding=utf-8
from flask import abort

from zspider.init import INIT_CONF
from zspider.models import Item
from zspider.models import ITEM_STATUS
from zspider.models import RUN_ERROR_LABELS
from zspider.models import RUN_STAGE_LABELS
from zspider.models import RUN_STATUS_LABELS
from zspider.models import TaskRun
from zspider.utils.log import BaseLog
from zspider.utils.log import LEVELS
from zspider.utils.models import Task


LOG_PAGE_SIZE = 50
DOC_PAGE_SIZE = 50
RUN_PAGE_SIZE = 50


def get_log_model_or_404(part):
    if part not in INIT_CONF:
        abort(404)
    cls = INIT_CONF[part].get("log_model", None)
    if not (cls and issubclass(cls, BaseLog)):
        abort(404)
    return cls


def build_log_list_context(part, page, ip, level, task_id, url):
    cls = get_log_model_or_404(part)
    q_params = {}
    if level > 0:
        q_params["level__gte"] = level
    if task_id:
        q_params["task_id"] = task_id
    if url:
        q_params["url"] = url

    ips = cls.objects(**q_params).only("ip").order_by("-time", "-msecs").limit(1000)
    ips = set([row["ip"] for row in ips])
    if len(ips) == 0:
        abort(404)
    if ip != "no":
        q_params["ip"] = ip

    return {
        "part": part,
        "levels": LEVELS,
        "level": level,
        "ips": ips,
        "ip": ip,
        "url": url,
        "task_id": task_id,
        "logs": cls.objects(**q_params)
        .order_by("-time", "-msecs")
        .paginate(page=page, per_page=LOG_PAGE_SIZE),
    }


def serialize_log(part, log_id):
    cls = get_log_model_or_404(part)
    log = cls.objects.get_or_404(id=log_id)
    payload = log.to_mongo().to_dict()
    payload.pop("_id", None)
    payload.pop("msecs", None)
    task_id = payload.pop("task_id", None)
    if task_id:
        payload["task_id"] = str(task_id)
    return payload


def build_doc_list_context(page, task_id):
    q_params = {}
    task = None
    if task_id:
        task = Task.objects.get_or_404(id=task_id)
        q_params["task"] = task
    return {
        "statuses": ITEM_STATUS,
        "task": task,
        "task_id": task_id,
        "docs": Item.objects(**q_params)
        .order_by("-save_time")
        .paginate(page=page, per_page=DOC_PAGE_SIZE),
    }


def serialize_doc(doc_id):
    doc = Item.objects.get_or_404(id=doc_id)
    payload = doc.to_mongo().to_dict()
    payload.pop("_id", None)
    payload["task"] = doc.task.name
    payload["status"] = ITEM_STATUS.get(doc.status, "")
    return payload


def build_run_list_context(page, task_id, status, error_code):
    q_params = {}
    task = None
    if task_id:
        task = Task.objects.get_or_404(id=task_id)
        q_params["task"] = task
    if status:
        q_params["status"] = status
    if error_code:
        q_params["last_error_code"] = error_code
    return {
        "task": task,
        "task_id": task_id,
        "status": status,
        "error_code": error_code,
        "statuses": RUN_STATUS_LABELS,
        "error_codes": RUN_ERROR_LABELS,
        "stages": RUN_STAGE_LABELS,
        "runs": TaskRun.objects(**q_params)
        .order_by("-queued_at")
        .paginate(page=page, per_page=RUN_PAGE_SIZE),
    }


def serialize_task_run(run_id):
    run = TaskRun.objects.get_or_404(id=run_id)
    payload = run.to_mongo().to_dict()
    payload.pop("_id", None)
    payload["task"] = run.task.name
    payload["status"] = RUN_STATUS_LABELS.get(run.status, run.status)
    payload["stage"] = RUN_STAGE_LABELS.get(run.stage, run.stage)
    if run.last_error_code:
        payload["last_error_code"] = RUN_ERROR_LABELS.get(
            run.last_error_code, run.last_error_code
        )
    if run.last_error_stage:
        payload["last_error_stage"] = RUN_STAGE_LABELS.get(
            run.last_error_stage, run.last_error_stage
        )
    return payload
