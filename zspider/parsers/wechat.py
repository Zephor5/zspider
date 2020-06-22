# coding=utf-8
import re

from mongoengine import fields

from .baseparser import BaseNewsParser
from zspider.utils import fields_models as fm

__author__ = "zephor"


class TaskConfWechatParser(fm.BaseDocument):
    front_url = fields.StringField(required=True, verbose_name=u"微信id", max_length=32)
    url_re = fm.RegExpField(
        required=True,
        group_num=1,
        verbose_name=u"新闻条目正则",
        help_text=u"用以提取索引页内新闻url，可与xpath任选其一使用",
    )


class WechatParser(BaseNewsParser):
    """
    微信抓站解析
    """

    CONF = TaskConfWechatParser

    def parse_index(self, response):
        r = re.compile(self._conf.url_re, re.UNICODE)
        i = r.groups
        for m in r.finditer(response.body_as_unicode()):
            yield m.group(i)

    def parse_article(self, response):
        return self._parse_article_field(response)
