# coding=utf-8
from datetime import datetime

from flask_mongoengine.wtf import model_form
from mongoengine import fields

from zspider.utils import engine
from zspider.utils import fields_models as fm
from zspider.utils.models import Task

__author__ = "zephor"

STATUS_NO = 0
STATUS_PUB_OK = 1
STATUS_PUB_FAIL = 2
STATUS_PUB_SKIP = 3

ITEM_STATUS = {
    STATUS_NO: "未处理",
    STATUS_PUB_OK: "发布成功",
    STATUS_PUB_FAIL: "发布失败",
    STATUS_PUB_SKIP: "发布过滤",
}

RUN_STATUS_QUEUED = "queued"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_SUCCESS = "success"
RUN_STATUS_PARTIAL = "partial"
RUN_STATUS_FAILED = "failed"

RUN_STATUS_LABELS = {
    RUN_STATUS_QUEUED: "排队中",
    RUN_STATUS_RUNNING: "运行中",
    RUN_STATUS_SUCCESS: "成功",
    RUN_STATUS_PARTIAL: "部分成功",
    RUN_STATUS_FAILED: "失败",
}

RUN_STAGE_DISPATCH = "dispatch"
RUN_STAGE_CRAWL = "crawl"
RUN_STAGE_PARSE = "parse"
RUN_STAGE_STORE = "store"
RUN_STAGE_PUBLISH = "publish"
RUN_STAGE_FINISHED = "finished"

RUN_STAGE_LABELS = {
    RUN_STAGE_DISPATCH: "调度",
    RUN_STAGE_CRAWL: "抓取",
    RUN_STAGE_PARSE: "解析",
    RUN_STAGE_STORE: "入库",
    RUN_STAGE_PUBLISH: "发布",
    RUN_STAGE_FINISHED: "完成",
}

RUN_ERROR_DISPATCH_SEND = "dispatch_send_failed"
RUN_ERROR_CRAWL_MESSAGE = "crawl_message_invalid"
RUN_ERROR_CRAWL_RUNTIME = "crawl_runtime_error"
RUN_ERROR_CRAWL_LOGIN = "crawl_login_failed"
RUN_ERROR_CRAWL_ANTI = "crawl_antispider"
RUN_ERROR_PARSE_FAILED = "parse_failed"
RUN_ERROR_STORE_VALIDATION = "store_validation_failed"
RUN_ERROR_PUBLISH_NO_SUBSCRIBE = "publish_no_subscribe"
RUN_ERROR_PUBLISH_FILTER = "publish_filtered"
RUN_ERROR_PUBLISH_RESPONSE = "publish_response_invalid"
RUN_ERROR_PUBLISH_REQUEST = "publish_request_failed"

RUN_ERROR_LABELS = {
    RUN_ERROR_DISPATCH_SEND: "调度投递失败",
    RUN_ERROR_CRAWL_MESSAGE: "抓取消息异常",
    RUN_ERROR_CRAWL_RUNTIME: "抓取执行异常",
    RUN_ERROR_CRAWL_LOGIN: "登录失败",
    RUN_ERROR_CRAWL_ANTI: "命中反爬",
    RUN_ERROR_PARSE_FAILED: "解析失败",
    RUN_ERROR_STORE_VALIDATION: "入库校验失败",
    RUN_ERROR_PUBLISH_NO_SUBSCRIBE: "未配置发布订阅",
    RUN_ERROR_PUBLISH_FILTER: "发布被过滤",
    RUN_ERROR_PUBLISH_RESPONSE: "发布响应异常",
    RUN_ERROR_PUBLISH_REQUEST: "发布请求失败",
}


class PubSubscribe(fm.BaseDocument):
    """
    id is task id
    """

    cids = fields.StringField(
        required=True,
        max_length=64,
        regex=r"^(?:\d+,)*\d+$",
        verbose_name="cIDs",
        help_text="cids，以,分割",
    )
    model_id = fields.StringField(
        required=True, max_length=32, regex=r"^[\w\d]+$", verbose_name="模型ID"
    )
    trans = fields.StringField(
        verbose_name="转换表达式",
        help_text="每行为一条受限转换表达式，预置变量 doc、re，"
        "前者是dict类型新闻数据、后者是python正则模块，"
        "过滤器的写法示例：condition and doc.update({'trash':1})",
    )
    app_creator = fields.StringField(
        required=True,
        default="ZSPIDER",
        max_length=50,
        verbose_name="应用创建者",
        help_text="发往新发布的创建者",
    )
    online = fields.IntField(
        default=0, choices=((0, "入库"), (1, "入库并发布")), verbose_name="发布状态"
    )


class Item(engine.DynamicDocument):
    meta = {
        "collection": "spider_doc",
        "max_size": 8 * 2**30,
        "max_documents": 1000000,
    }

    title = fields.StringField(required=True, verbose_name="标题")
    content = fields.StringField(verbose_name="内容")
    src_time = fields.DateTimeField(verbose_name="源时间")
    save_time = fields.DateTimeField(default=datetime.now, verbose_name="入库时间")
    source = fields.StringField(verbose_name="媒体源")
    url = fields.URLField(required=True)
    task = fields.ReferenceField(Task)
    status = fields.IntField(required=True, choices=ITEM_STATUS.keys())
    info = fields.StringField(required=True, verbose_name="状态信息")


class TaskRun(fm.BaseDocument):
    task = fields.ReferenceField(Task, required=True)
    task_name = fields.StringField(required=True, max_length=32, verbose_name="任务名称")
    spider = fields.StringField(required=True, verbose_name="抓取程序")
    parser = fields.StringField(required=True, verbose_name="解析程序")
    trigger_type = fields.StringField(
        required=True,
        default="schedule",
        choices=(("schedule", "定时调度"), ("manual", "手动触发")),
        verbose_name="触发方式",
    )
    status = fields.StringField(
        required=True,
        default=RUN_STATUS_QUEUED,
        choices=tuple(RUN_STATUS_LABELS.keys()),
        verbose_name="运行状态",
    )
    stage = fields.StringField(
        required=True,
        default=RUN_STAGE_DISPATCH,
        choices=tuple(RUN_STAGE_LABELS.keys()),
        verbose_name="当前阶段",
    )
    worker_ip = fields.StringField(max_length=32, verbose_name="执行节点")
    queued_at = fields.DateTimeField(default=datetime.now, verbose_name="进入队列时间")
    started_at = fields.DateTimeField(verbose_name="开始执行时间")
    finished_at = fields.DateTimeField(verbose_name="结束时间")
    close_reason = fields.StringField(max_length=64, verbose_name="结束原因")
    latest_url = fields.URLField(verbose_name="最近处理URL")
    last_error_stage = fields.StringField(
        choices=tuple(RUN_STAGE_LABELS.keys()), verbose_name="最近错误阶段"
    )
    last_error_code = fields.StringField(
        choices=tuple(RUN_ERROR_LABELS.keys()), verbose_name="最近错误码"
    )
    last_error = fields.StringField(verbose_name="最近错误")
    index_count = fields.IntField(default=0, verbose_name="入口数")
    article_count = fields.IntField(default=0, verbose_name="文章数")
    stored_count = fields.IntField(default=0, verbose_name="入库成功数")
    store_fail_count = fields.IntField(default=0, verbose_name="入库失败数")
    publish_ok_count = fields.IntField(default=0, verbose_name="发布成功数")
    publish_fail_count = fields.IntField(default=0, verbose_name="发布失败数")
    publish_skip_count = fields.IntField(default=0, verbose_name="发布跳过数")

    meta = {
        "indexes": [
            "task",
            "status",
            "-queued_at",
        ]
    }


PubSubscribeForm = model_form(PubSubscribe)
