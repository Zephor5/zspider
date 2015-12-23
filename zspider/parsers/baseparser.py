# coding=utf-8
import datetime
import re

from utils.fields_models import BaseTaskConf
from . import BaseParser

__author__ = 'zephor'


class BaseNewsParser(BaseParser):

    CONF = BaseTaskConf     # fixme, must be set to a subclass in subclass #

    INNER_TEXT = 'text()[normalize-space()]|*//text()[normalize-space()]'

    def __init__(self, task_id, name):
        super(BaseNewsParser, self).__init__(name)
        self._get_conf(task_id)
        self.date = datetime.date.today()
        self._setup()

    def __str__(self):
        return '%s解析器' % self.name

    def __unicode__(self):
        return u'%s解析器' % self.name

    def _get_conf(self, task_id):
        # main conf init
        conf = self.CONF.objects.get(id=task_id)
        try:
            self.login_data = conf.login_data
            if conf.to_login:
                self._to_login = conf.to_login
        except AttributeError:
            pass    # some parser may not implement the login staff
        self._conf = conf

        # article_fields
        from utils.models import ArticleField
        self._article_fields = ArticleField.objects(task=task_id)

    def _setup(self):
        date = self.date
        params = {
            'year': date.year,
            'month': date.strftime('%m'),
            'day': date.strftime('%d')
        }
        self._front_url = self._conf.front_url % params

    def _parse_article_field(self, response):
        new = {'url': response.url}
        for field_conf in self._article_fields:
            val = response
            if field_conf.xpath:
                val = response.xpath(field_conf.xpath)
                val = ''.join(val.extract())
            if field_conf.re:
                r = re.compile(field_conf.re, re.UNICODE)
                if val is response:
                    val = response.body_as_unicode()
                r = r.search(val)
                try:
                    val = r.group(1)
                except IndexError:
                    val = r.group()

            if val is response:
                val = ''
            val = val.strip()
            if 'time' in field_conf.name and val:
                nums = re.findall('\d+', val)
                l = len(nums)
                if l < 3:
                    val = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                elif l < 5:
                    val = '{0:s}-{1:s}-{2:s} %s'.format(*nums[:3]) % datetime.datetime.now().strftime('%H:%M:%S')
                elif l == 5:
                    val = '{0:s}-{1:s}-{2:s} {3:s}:{4:s}:00'.format(*nums[:5])
                else:
                    val = '{0:s}-{1:s}-{2:s} {3:s}:{4:s}:{5:s}'.format(*nums[:6])
            new[field_conf.name] = val
        return new

    @property
    def need_login(self):
        return hasattr(self, '_to_login')

    def to_login(self):
        if hasattr(self, '_to_login'):
            del self._to_login

    @property
    def front_url(self):
        try:
            return self._to_login
        except AttributeError:
            return self._front_url

    def parse_index(self, response):
        # ## 该方法返回各新闻url
        raise NotImplementedError('method parse_index not implemented')

    def parse_article(self, response):
        raise NotImplementedError('method parse_article not implemented')
