# coding=utf-8
import logging

from scrapy import Request
from scrapy import Spider

__author__ = "zephor"

logger = logging.getLogger(__name__)


class BaseSpider(Spider):
    def __init__(self, parser, task_id, task_name, run_id=None, *args, **kwargs):
        super(BaseSpider, self).__init__(*args, **kwargs)
        self.task_id = task_id
        self.run_id = run_id
        from zspider.parsers import get_parser

        self.parser = get_parser(parser, task_id, task_name, **kwargs)
        self._extra = {"task_id": task_id, "task_name": task_name, "run_id": run_id}
        logger.info(
            "task {0} start with parser:{1}".format(task_name, parser),
            extra=self._extra,
        )

    def _parse_index(self, response, callback=None):
        callback = callback if callable(callback) else self._parse_article
        _extra_url = self._extra_url = dict(self._extra)
        for url in self.parser.parse_index(response):
            if isinstance(url, tuple):
                url, _meta = url
            else:
                _meta = {}
            url = response.urljoin(url)
            if self.task_id == "test_index":
                yield {"url": url}
                continue
            _extra_url["url"] = url
            from zspider.task_runs import increment_task_run_metric
            from zspider.task_runs import mark_task_run_stage

            increment_task_run_metric(self.run_id, "index_count", latest_url=url)
            mark_task_run_stage(self.run_id, "crawl", latest_url=url)
            logger.info("begin to crawl", extra=_extra_url)
            request = Request(url, callback)
            request.meta.update(_meta)
            if self.task_id == "test_article":
                request.dont_filter = True  # mark 去重
            if not self.task_id.startswith("test_"):
                request.meta["dupefilter"] = True
            yield request
            if self.task_id == "test_article":
                break

    def _parse_article(self, response):
        self._extra_url["url"] = response.url
        from zspider.task_runs import increment_task_run_metric
        from zspider.task_runs import fail_task_run
        from zspider.task_runs import mark_task_run_stage
        from zspider.models import RUN_ERROR_PARSE_FAILED

        mark_task_run_stage(self.run_id, "parse", latest_url=response.url)
        logger.info("begin to parse", extra=self._extra_url)
        try:
            item = self.parser.parse_article(response)
        except Exception as exc:
            fail_task_run(
                self.run_id,
                "parse",
                RUN_ERROR_PARSE_FAILED,
                exc,
                latest_url=response.url,
            )
            raise
        increment_task_run_metric(self.run_id, "article_count", latest_url=response.url)
        logger.info("parser ok", extra=self._extra_url)
        return item

    @property
    def logger(self):
        # 推荐使用文件顶部定义logger形式
        return logging.getLogger("spider.{0}".format(self.name))

    def parse(self, response, **kwargs):
        raise NotImplementedError("parse")
