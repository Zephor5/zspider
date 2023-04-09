# coding=utf-8
from datetime import datetime

from flask_mongoengine.wtf import model_form
from flask_mongoengine.wtf.models import ModelForm
from mongoengine import fields

from zspider.spiders import SPIDERS
from zspider.utils.fields_models import BaseDocument
from zspider.utils.fields_models import CronField
from zspider.utils.fields_models import RegExpField
from zspider.utils.fields_models import XPathField

__author__ = "zephor"

# parser list
PARSER_CONF_FORM_REF = {}

_parsers = []


def _init():
    global _parsers

    from zspider.parsers import PARSERS

    for name, o in PARSERS.items():
        _parsers.append((name, name))
        PARSER_CONF_FORM_REF[name] = model_form(o.CONF, exclude=())


if not PARSER_CONF_FORM_REF:
    _init()


# end_tricks


class User(BaseDocument):
    username = fields.StringField(
        required=True, max_length=20, unique=True, verbose_name="用户名"
    )
    password = fields.StringField(required=True, verbose_name="密码")
    role = fields.StringField(
        required=True,
        default="user",
        choices=(("user", "普通用户"), ("admin", "管理员")),
        verbose_name="角色",
    )

    def __unicode__(self):
        return self.username


class Task(BaseDocument):
    name = fields.StringField(required=True, max_length=32, verbose_name="任务名称")
    spider = fields.StringField(required=True, verbose_name="抓取程序", choices=SPIDERS)
    parser = fields.StringField(required=True, verbose_name="解析程序", choices=_parsers)
    cron = CronField(
        default="*/5 * * * *", verbose_name="定时策略", help_text="同crontab定时配置语法"
    )
    is_login = fields.BooleanField(default=False, verbose_name="需要cookie")
    is_active = fields.BooleanField(default=False, verbose_name="激活")
    creator = fields.ReferenceField(User)
    mender = fields.ReferenceField(User)
    ctime = fields.DateTimeField(default=datetime.now, verbose_name="创建时间")
    mtime = fields.DateTimeField(default=datetime.now, verbose_name="修改时间")

    def __unicode__(self):
        return self.name


class ArticleField(BaseDocument):
    task = fields.ReferenceField(Task)
    name = fields.StringField(required=True, max_length=32, verbose_name="字段名称")
    xpath = XPathField(verbose_name="新闻字段xpath", max_length=128)
    re = RegExpField(verbose_name="字段解析正则")
    specify = fields.StringField(max_length=64, verbose_name="指定值")

    # boundaries =

    @staticmethod
    def base_names():
        return "title", "content", "src_time", "source"

    def __unicode__(self):
        return "%s.%s" % (self.task, self.name)


def _save(self, commit=True, **kwargs):
    if self.instance:
        self.populate_obj(self.instance)
    else:
        data = self.data
        data.pop("csrf_token", None)
        self.instance = self.model_class(**data)

    if commit:
        self.instance.save(**kwargs)
    return self.instance


ModelForm.save = _save

UserForm = model_form(User, exclude=("password",))
TaskForm = model_form(
    Task, exclude=("is_active", "creator", "mender", "ctime", "mtime")
)
ArticleFieldForm = model_form(ArticleField, exclude=("task",))
