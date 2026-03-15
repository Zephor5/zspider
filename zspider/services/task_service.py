# coding=utf-8
import json
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from werkzeug.exceptions import NotFound

from zspider.confs.dispatcher_conf import MANAGE_KEY
from zspider.confs.dispatcher_conf import MANAGE_PORT
from zspider.models import PubSubscribe
from zspider.utils.models import Task


TASK_PAGE_SIZE = 32


def build_task_list_context(field, q, page):
    q_params = {}
    prev_kwargs = {}
    if q and field:
        if field == "task_name":
            q_params = {"name__contains": q}
        prev_kwargs = {"field": field, "q": q}

    total_count = Task.objects(**q_params).count()
    running_count = Task.objects(is_active=True, **q_params).count()
    task_page = Task.objects(**q_params).paginate(page=page, per_page=TASK_PAGE_SIZE)

    context = {
        "count": total_count,
        "running_count": running_count,
        "tasks": task_page,
        "task_rows": build_task_rows(task_page.items),
        "draft_count": total_count - running_count,
        "prev_kwargs": prev_kwargs if total_count else {},
    }
    return context


def build_task_rows(tasks):
    tasks = list(tasks)
    task_ids = [task.id for task in tasks]
    subscribed_ids = set()
    if task_ids:
        subscribed_ids = {
            str(sub.id) for sub in PubSubscribe.objects(id__in=task_ids).only("id")
        }
    return [_build_task_row(task, str(task.id) in subscribed_ids) for task in tasks]


def get_task_or_404(task_id):
    return Task.objects.get_or_404(id=task_id)


def get_task_subscription(task_id):
    try:
        return PubSubscribe.objects.get_or_404(id=task_id)
    except NotFound:
        return None


def serialize_subscription(subscribe):
    return {"cids": subscribe.cids, "model_id": subscribe.model_id}


def delete_task_subscription(task_id):
    PubSubscribe.objects(id=task_id).delete()


def toggle_task(task_id, dispatcher_ip):
    task = get_task_or_404(task_id)
    action = "/%s/{0:s}/{1:s}".format(task_id, MANAGE_KEY)

    if task.is_active:
        task.is_active = False
        action %= "pause"
    elif task.cron:
        task.is_active = True
        action %= "load"
    else:
        return False, "必须先设置好任务定时才能启动任务"

    task.save()
    if not dispatcher_ip:
        return True, "找不到dispatcher"

    try:
        response = urlopen(
            "http://{0:s}:{1:d}".format(dispatcher_ip, MANAGE_PORT) + quote(action)
        ).read()
    except URLError:
        return True, "连接到dispatcher %s失败" % dispatcher_ip

    payload = json.loads(response)
    return True, payload["data"]


def reload_task(task, dispatcher_ip):
    action = "/load/{0:s}/{1:s}".format(str(task.id), MANAGE_KEY)
    response = urlopen(
        "http://{0:s}:{1:d}".format(dispatcher_ip, MANAGE_PORT) + quote(action)
    ).read()
    return json.loads(response)["data"]


def _build_task_row(task, has_subscription):
    if task.is_active:
        stage_label = "运行中"
        stage_class = "success"
        stage_hint = "重点查看最近结果和日志，确认抓取链路是否稳定。"
    elif task.cron:
        stage_label = "待启动"
        stage_class = "warning"
        stage_hint = "建议先回到编辑页做索引/新闻测试，确认后再启动。"
    else:
        stage_label = "待补配置"
        stage_class = "default"
        stage_hint = "先补齐定时策略和解析配置，再进入测试。"

    return {
        "id": task.id,
        "name": task.name or task.id,
        "cron_text": task.cron or "未设置",
        "is_active": task.is_active,
        "parser": task.parser,
        "spider": task.spider,
        "mender": task.mender,
        "mtime": task.mtime,
        "has_subscription": has_subscription,
        "stage_label": stage_label,
        "stage_class": stage_class,
        "stage_hint": stage_hint,
    }
