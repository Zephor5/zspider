# coding=utf-8
import logging

from utils import models
from zspider import models as zsm
from mongoengine import ValidationError

__author__ = 'zephor'

logger = logging.getLogger(__name__)


class CappedStorePipeLine(object):
    def __init__(self, task_id):
        self.task = models.Task.objects.get(id=task_id)
        self._extra = {'task_id': task_id}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.spider.task_id)

    def process_item(self, item, spider):
        doc = zsm.Item(**item)
        doc.task = self.task
        extra = self._extra
        extra['url'] = doc.url
        try:
            doc.save()
        except ValidationError:
            logger.exception("can't save item", extra=extra)
        else:
            logger.info('save item %s ok' % doc.id, extra=extra)
