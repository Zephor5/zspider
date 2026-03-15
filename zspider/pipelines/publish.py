# coding=utf-8
import json
import logging
import re
import urllib.parse

from lxml import etree
from mongoengine import DoesNotExist
from twisted.internet import defer

from zspider import models as zsm
from zspider.models import RUN_ERROR_PUBLISH_FILTER
from zspider.models import RUN_ERROR_PUBLISH_NO_SUBSCRIBE
from zspider.models import RUN_ERROR_PUBLISH_REQUEST
from zspider.models import RUN_ERROR_PUBLISH_RESPONSE
from zspider.models import RUN_STAGE_PUBLISH
from zspider.task_runs import increment_task_run_metric
from zspider.task_runs import mark_task_run_stage
from zspider.task_runs import record_task_run_issue
from zspider.utils import http
from zspider.utils.transform import SafeTransformEvaluator

__author__ = "zephor"

logger = logging.getLogger(__name__)


class _SkipDoc(Exception):
    pass


class PubPipeLine(object):
    PUB_PORT = ""

    TRANS_PORT = ""

    TRASH_NODES = ("iframe", "form", "script", "style", "link", "input", "select")

    REPLACE_NULL = re.compile(r"<a[^><]*>|</a>|[\t\n\r]", re.I)

    REPLACE_SPACE = re.compile(" {2,}")

    def __init__(self, task_id, run_id=None):
        self._extra = {"task_id": task_id}
        self.run_id = run_id
        try:
            pub_subscribe = zsm.PubSubscribe.objects.get(id=task_id)
        except DoesNotExist:
            self._pub = False
            record_task_run_issue(
                self.run_id,
                RUN_STAGE_PUBLISH,
                RUN_ERROR_PUBLISH_NO_SUBSCRIBE,
                "task has no subscriber",
            )
            logger.warning("task %s has no subscriber" % task_id)
        else:
            self._pub = True
            self.cids = [int(x) for x in pub_subscribe.cids.split(",")]
            self.model_id = pub_subscribe.model_id
            self.tans = filter(
                None,
                [re.sub("[\b\r\n\t]", "", s) for s in pub_subscribe.trans.split("\n")],
            )
            self.app_creator = pub_subscribe.app_creator
            self.online = pub_subscribe.online

    @classmethod
    def from_crawler(cls, crawler):
        cls.PUB_PORT = crawler.settings.get("PUB_PORT")
        cls.TRANS_PORT = crawler.settings.get("TRANS_PORT")
        return cls(crawler.spider.task_id, getattr(crawler.spider, "run_id", None))

    def process_item(self, item, _):
        d = defer.Deferred()
        extra = dict(self._extra)
        extra.update({"url": item.get("url", "")})
        mark_task_run_stage(self.run_id, RUN_STAGE_PUBLISH, item.get("url", ""))
        if self._pub:
            _doc = dict(item)
            d.addCallback(self.process_content, extra)
            d.addCallback(self.process_trans, item, extra)
            d.addCallback(self.prepare_data, item)
            d.addCallback(
                lambda doc: logger.debug(json.dumps(doc, indent=4), extra=extra) or doc
            )
            d.addCallback(
                lambda doc: http.twisted_post(
                    self.PUB_PORT, urllib.parse.urlencode({"doc": json.dumps(doc)})
                )
            )
            d.addCallback(self.after_pub, item, extra)
            d.addErrback(self.post_fail_or_skip, item, extra)
            d.callback(_doc)
        else:
            item["status"] = zsm.STATUS_NO
            item["info"] = "无发布订阅"
            increment_task_run_metric(
                self.run_id, "publish_skip_count", latest_url=item.get("url", "")
            )
            logger.info(json.dumps(item, indent=4), extra=extra)
            d.callback(item)
        return d

    def process_content(self, _doc, _):
        content = _doc.get("content", "<p></p>")
        content = self.REPLACE_NULL.sub("", content)
        content = self.REPLACE_SPACE.sub(" ", content)
        dom = etree.fromstring(
            content.encode("utf-8"),
            parser=etree.HTMLParser(encoding="utf-8"),
            base_url=_doc.get("url", ""),
        )
        self._filter_trash(dom)
        _doc["content"] = "".join(
            [
                etree.tostring(elem, method="html", encoding="utf-8")
                for elem in list(dom.find("body"))
            ]
        )
        return _doc

    def process_trans(self, _doc, item, extra):
        for x in self.tans:
            __doc = dict(_doc)
            try:
                SafeTransformEvaluator.execute(x, _doc)
            except Exception as e:
                # we skip this process when it's incorrect
                logger.warning(
                    "get error :{0:s}, when transform :{1:s}".format(e, x), extra=extra
                )
                _doc = __doc
            else:
                if "trash" in _doc:
                    logger.info(
                        "skip item :{0:s} with filter :{1:s}".format(_doc["title"], x),
                        extra=extra,
                    )
                    item["status"] = zsm.STATUS_PUB_SKIP
                    item["info"] = "发布过滤：%s" % x
                    increment_task_run_metric(
                        self.run_id,
                        "publish_skip_count",
                        latest_url=item.get("url", ""),
                    )
                    record_task_run_issue(
                        self.run_id,
                        RUN_STAGE_PUBLISH,
                        RUN_ERROR_PUBLISH_FILTER,
                        x,
                        latest_url=item.get("url", ""),
                    )
                    raise _SkipDoc
        return _doc

    def prepare_data(self, _doc, _):
        # setup some data to pub
        doc = {
            "creator": self.app_creator,
            "cIDs": self.cids,
            "modelID": self.model_id,
            "online": self.online,
        }
        doc.update(_doc)
        return doc

    def after_pub(self, res, item, extra):
        data = json.loads(res).get("result", {}).get("data")
        if isinstance(data, dict):
            item["status"] = zsm.STATUS_PUB_OK
            item["info"] = "发布成功:%s" % data
            increment_task_run_metric(
                self.run_id, "publish_ok_count", latest_url=item.get("url", "")
            )
            logger.info("发布成功: %s" % res, extra=extra)
        else:
            item["status"] = zsm.STATUS_PUB_FAIL
            item["info"] = str(data)
            increment_task_run_metric(
                self.run_id, "publish_fail_count", latest_url=item.get("url", "")
            )
            record_task_run_issue(
                self.run_id,
                RUN_STAGE_PUBLISH,
                RUN_ERROR_PUBLISH_RESPONSE,
                data,
                latest_url=item.get("url", ""),
            )
            logger.warning("发布失败：%s" % res, extra=extra)
        return item

    def post_fail_or_skip(self, failure, item, extra):
        if failure.type is _SkipDoc:
            return item
        item["status"] = zsm.STATUS_PUB_FAIL
        item["info"] = str(failure)
        increment_task_run_metric(
            self.run_id, "publish_fail_count", latest_url=item.get("url", "")
        )
        record_task_run_issue(
            self.run_id,
            RUN_STAGE_PUBLISH,
            RUN_ERROR_PUBLISH_REQUEST,
            failure,
            latest_url=item.get("url", ""),
        )
        logger.error("调用发布接口失败：{0:s}".format(failure), extra=extra)
        return item

    @classmethod
    def _filter_trash(cls, dom):
        for node in cls.TRASH_NODES:
            for t in dom.iter(node):
                t.getparent().remove(t)
