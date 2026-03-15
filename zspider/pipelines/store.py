# coding=utf-8
import logging

from mongoengine import ValidationError

from zspider import models as zsm
from zspider.models import RUN_ERROR_STORE_VALIDATION
from zspider.models import RUN_STAGE_STORE
from zspider.task_runs import increment_task_run_metric
from zspider.task_runs import mark_task_run_stage
from zspider.task_runs import record_task_run_issue
from zspider.utils import models

__author__ = "zephor"

logger = logging.getLogger(__name__)


class CappedStorePipeLine(object):
    def __init__(self, task_id, run_id=None):
        self.task = models.Task.objects.get(id=task_id)
        self._extra = {"task_id": task_id}
        self.run_id = run_id

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.spider.task_id, getattr(crawler.spider, "run_id", None))

    def process_item(self, item, _):
        doc = zsm.Item(**item)
        doc.task = self.task
        extra = self._extra
        extra["url"] = doc.url
        mark_task_run_stage(self.run_id, RUN_STAGE_STORE, latest_url=doc.url)
        try:
            doc.save()
        except ValidationError:
            increment_task_run_metric(
                self.run_id, "store_fail_count", latest_url=doc.url
            )
            record_task_run_issue(
                self.run_id,
                RUN_STAGE_STORE,
                RUN_ERROR_STORE_VALIDATION,
                "can't save item",
                doc.url,
            )
            logger.exception("can't save item", extra=extra)
        else:
            increment_task_run_metric(self.run_id, "stored_count", latest_url=doc.url)
            logger.info("save item %s ok" % doc.id, extra=extra)
