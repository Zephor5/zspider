# coding=utf-8
import logging
import sys
import traceback
from collections import OrderedDict
from datetime import datetime
from queue import Empty
from queue import Queue
from threading import Thread

from mongoengine import fields

from zspider.confs.conf import INNER_IP
from zspider.confs.conf import LOG_DATEFORMAT
from zspider.utils import engine
from zspider.utils.fields_models import FBaseQuerySet
from zspider.utils.fields_models import IpField

__author__ = "zephor"

LEVELS = OrderedDict()
LEVELS[logging.NOTSET] = "NSET"
LEVELS[logging.DEBUG] = "DBUG"
LEVELS[logging.INFO] = "INFO"
LEVELS[logging.WARN] = "WARN"
LEVELS[logging.ERROR] = "ERRO"
LEVELS[logging.FATAL] = "FATL"


class BaseLog(engine.DynamicDocument):
    meta = {
        "abstract": True,
        "queryset_class": FBaseQuerySet,
        "index_background": True,
        "indexes": ["#ip", ("-time", "-msecs")],  # hashed index
    }

    ip = IpField(required=True, verbose_name="机器ip")
    pid = fields.IntField(required=True)
    pathname = fields.StringField(verbose_name="文件")
    lineno = fields.IntField(required=True, verbose_name="行号")
    level = fields.IntField(default=logging.NOTSET, choices=LEVELS.keys())
    msg = fields.StringField(verbose_name="信息")
    time = fields.DateTimeField(required=True, verbose_name="时间")
    msecs = fields.FloatField(required=True)


class LogCrawler(BaseLog):
    meta = {
        "max_size": 5 * 2**30,
        "max_documents": 10000000,
        "indexes": ["task_id", "#url", "$task_name"],
    }

    task_id = fields.ObjectIdField(verbose_name="任务ID")
    task_name = fields.StringField(max_length=32, verbose_name="任务名称")
    url = fields.URLField()


class LogDispatcher(BaseLog):
    meta = {"max_size": 512 * 2**20, "max_documents": 1000000}

    task_id = fields.ObjectIdField(verbose_name="任务ID")


class ThreadMongoHandler(logging.Handler):
    # reserve or special handled fields
    RECORD_FIELDS = {
        "threadName",
        "name",
        "thread",
        "created",
        "process",
        "processName",
        "args",
        "module",
        "filename",
        "levelno",
        "msg",
        "message",
        "exc_info",
        "funcName",
        "relativeCreated",
        "levelname",
        "asctime",
    }

    def __init__(self, log_model, max_thread=2, *args):
        super(ThreadMongoHandler, self).__init__(*args)

        assert issubclass(log_model, BaseLog), "log_model must be a subclass of BaseLog"
        assert 0 < max_thread < 6, "thread is not efficient enough, must be 1~5 threads"

        self.log_cls = log_model

        log_model.create_index(
            "#ip"
        )  # prevent bug: non-thread safe mongoengine collection creation

        self.q = Queue()
        self._r = 1
        thread_pool = self.tp = set()
        while len(thread_pool) < max_thread:
            process = Thread(target=self.record)
            process.setDaemon(True)
            thread_pool.add(process)
        for p in thread_pool:
            p.start()

    @staticmethod
    def _write(msg=None):
        if msg is None:
            msg = traceback.format_exc()
        try:
            sys.stderr.write(
                "{0}: {1}".format(datetime.now().strftime(LOG_DATEFORMAT), msg)
            )
        except Exception:
            pass

    def handle(self, record):
        rv = self.filter(record)
        if rv:
            self.emit(record)
        return rv

    def emit(self, record):
        try:
            self.format(record)
            msg = {}
            for k, v in record.__dict__.items():
                if isinstance(v, (str, int, float)):
                    msg[k] = v
            self.q.put_nowait(msg)
        except Exception:
            self.handleError(record)

    def close(self):
        self._r = 0
        for p in self.tp:
            p.join()
        self._write("exit with %d logs remained\n" % self.q.qsize())

    def record(self):
        while self._r:
            try:
                msg = self.q.get(timeout=2)
            except Empty:
                continue
            except SystemExit:
                raise
            except Exception:
                self._write()
                continue

            log = self.log_cls(
                ip=INNER_IP,
                pid=msg["process"],
                level=msg["levelno"],
                msg=msg["message"],
                time=msg["asctime"],
            )
            for k, v in msg.items():
                if k not in self.RECORD_FIELDS:
                    setattr(log, k, v)
            try:
                log.save()
            except AssertionError:
                self._write()
            except Exception:
                # this supposed to be resolved
                self._write()
