# coding=utf-8
import logging
import re
from collections import OrderedDict

from utils import fields_models as fm
from .baseparser import BaseNewsParser

__author__ = 'zephor'

logger = logging.getLogger(__name__)

UNREAD = 0
READING = 1
READ = 2


class TaskConfNewspaper(fm.BaseTaskConf):
    page_title_xpath = fm.XPathField(required=True, verbose_name=u'版面标题xpath',
                                     help_text=u'版面块抬头xpath，仅包含版面号及名称')
    page_name_no_re = fm.RegExpField(required=True, group_num=2, group_names=('page_no', 'page_name'),
                                     verbose_name=u'版面名称号正则',
                                     help_text=u'提取版面号及名称的正则，包含page_no、page_name俩子匹配')
    page_news_xpath = fm.XPathField(required=True, verbose_name=u'新闻a标签xpath',
                                    help_text=u'用以提取版面内新闻a标签')


class Newspaper(BaseNewsParser):
    """
    适用于单页包含整个报纸文章索引
    """

    CONF = TaskConfNewspaper

    def __init__(self, task_id, task_name, task_conf=None, article_fields=None):
        super(self.__class__, self).__init__(task_id, task_name, task_conf, article_fields)
        self.pages = OrderedDict()

    @property
    def news(self):
        for page in self.pages.itervalues():
            for new in page['news']:
                yield new

    def _parse_page(self, page):
        page_name = ''.join(page.xpath(self.INNER_TEXT).extract())
        page_name = page_name.strip()
        page_name = re.search(self._conf.page_name_no_re, page_name).groupdict()
        page_no = page_name['page_no']
        page_name = page_name['page_name']
        logger.debug(u'parse paper page no:{0:s}, name:{1:s}'.format(page_no, page_name))
        page_news = []
        i = 0
        for new in page.xpath(self._conf.page_news_xpath):
            new = {'title': ''.join(new.xpath(self.INNER_TEXT).extract()).strip(),
                   'url': new.xpath('@href').extract_first()}
            page_news.append(new)
            # follow dict for parse_new kwargs with response.meta
            yield new['url'], {'page_no': page_no, 'page_news_i': i}
            i += 1

        page = {
            'name': page_name,
            'news': page_news,
            'status': UNREAD,
            'read': 0
        }
        self.pages.update({page_no: page})

    def parse_index(self, response):
        for page in response.xpath(self._conf.page_title_xpath):
            for tup in tuple(self._parse_page(page)):   # 确保单个版面索引解析完成
                yield tup

    def parse_article(self, response):
        page_no = response.meta['page_no']
        page_news_i = response.meta['page_news_i']
        new = self._parse_article_field(response)
        page = self.pages[page_no]
        page['news'][page_news_i].update(new)
        _status = page['status']
        page['read'] += 1
        if _status == UNREAD:
            page['status'] = READING
        elif _status == READING:
            if len(page['news']) == page['read']:
                page['status'] = READ
        return page['news'][page_news_i]
