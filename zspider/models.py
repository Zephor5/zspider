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
        verbose_name="Python evals",
        help_text="每行为一条python eval语句，预置变量 doc、re，"
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


PubSubscribeForm = model_form(PubSubscribe)
