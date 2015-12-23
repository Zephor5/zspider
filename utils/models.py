# coding=utf-8
from datetime import datetime
from flask.ext.mongoengine.wtf import model_form

from utils.fields_models import RegExpField, XPathField, CronField, BaseDocument
from zspider.spiders import SPIDERS
from . import engine

__author__ = 'zephor'


# parser list
PARSER_CONF_FORM_REF = {}


def _init():
    global _parsers

    from zspider.parsers import PARSERS

    _parsers = []
    for name, o in PARSERS.iteritems():
        _parsers.append((name, name))
        PARSER_CONF_FORM_REF[name] = model_form(o.CONF, exclude=())

if not PARSER_CONF_FORM_REF:
    _init()
# end_tricks


class User(BaseDocument):
    username = engine.StringField(required=True, max_length=20, unique=True,
                                  verbose_name=u'用户名', help_text=u'员工邮箱前缀')
    role = engine.StringField(required=True, default='user',
                              choices=(('user', u'普通用户'), ('admin', u'管理员')),
                              verbose_name=u'角色')

    def __unicode__(self):
        return self.username


class Task(BaseDocument):
    name = engine.StringField(required=True, max_length=32, verbose_name=u'任务名称')
    spider = engine.StringField(required=True, verbose_name=u'抓取程序', choices=SPIDERS)
    parser = engine.StringField(required=True, verbose_name=u'解析程序', choices=_parsers)
    cron = CronField(default='*/5 * * * *', verbose_name=u'定时策略', help_text=u'同crontab定时配置语法')
    is_login = engine.BooleanField(default=False, verbose_name=u'需要cookie')
    is_active = engine.BooleanField(default=False, verbose_name=u'激活')
    creator = engine.ReferenceField(User)
    mender = engine.ReferenceField(User)
    ctime = engine.DateTimeField(default=datetime.now, verbose_name=u'创建时间')
    mtime = engine.DateTimeField(default=datetime.now, verbose_name=u'修改时间')

    def __unicode__(self):
        return self.name


class ArticleField(BaseDocument):
    task = engine.ReferenceField(Task)
    name = engine.StringField(required=True, max_length=32, verbose_name=u'字段名称')
    xpath = XPathField(verbose_name=u'新闻字段xpath')
    re = RegExpField(verbose_name=u'字段解析正则')
    # boundaries =

    @staticmethod
    def base_names():
        return 'title', 'content', 'src_time', 'source'

    def __unicode__(self):
        return '%s.%s' % (self.task, self.name)


UserForm = model_form(User)
TaskForm = model_form(Task, exclude=('is_active', 'creator', 'mender', 'ctime', 'mtime'))
ArticleFieldForm = model_form(ArticleField, exclude=('task',))
