# coding=utf-8
import re

from ..utils import fields_models as fm
from .baseparser import BaseNewsParser

__author__ = "zephor"


class TaskConfIndexParser(fm.BaseTaskConf):
    url_xpath = fm.XPathField(verbose_name=u"新闻条目xpath", help_text=u"用以提取索引页内新闻url")
    url_re = fm.RegExpField(
        group_num=1, verbose_name=u"新闻条目正则", help_text=u"用以提取索引页内新闻url，可与xpath任选其一使用"
    )


class IndexParser(BaseNewsParser):
    """
    通用索引式新闻页解析
    """

    CONF = TaskConfIndexParser

    def parse_index(self, response):
        if self._conf.url_xpath:
            for e in response.xpath(self._conf.url_xpath):
                yield e.extract()
        elif self._conf.url_re:
            r = re.compile(self._conf.url_re, re.UNICODE)
            i = r.groups
            for m in r.finditer(response.body_as_unicode()):
                yield m.group(i)

    def parse_article(self, response):
        return self._parse_article_field(response)
