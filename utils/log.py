# coding=utf-8
import logging
import sys
import traceback

from collections import OrderedDict
from datetime import datetime
from Queue import Queue, Empty
from threading import Thread
from utils import engine
from utils.fields_models import IpField, FBaseQuerySet
from conf import INNER_IP, LOG_DATEFORMAT

__author__ = 'zephor'

LEVELS = OrderedDict()
LEVELS[logging.NOTSET] = 'NSET'
LEVELS[logging.DEBUG] = 'DBUG'
LEVELS[logging.INFO] = 'INFO'
LEVELS[logging.WARN] = 'WARN'
LEVELS[logging.ERROR] = 'ERRO'
LEVELS[logging.FATAL] = 'FATL'


class BaseLog(engine.DynamicDocument):
    meta = {'abstract': True,
            'queryset_class': FBaseQuerySet,
            'index_background': True,
            'indexes': [
                '#ip',  # hashed index
                ('-time', '-msecs')
            ]}

    ip = IpField(required=True, verbose_name=u'机器ip')
    pid = engine.IntField(required=True)
    pathname = engine.StringField(verbose_name=u'文件')
    lineno = engine.IntField(required=True, verbose_name=u'行号')
    level = engine.IntField(default=logging.NOTSET, choices=LEVELS.keys())
    msg = engine.StringField(verbose_name=u'信息')
    time = engine.DateTimeField(required=True, verbose_name=u'时间')
    msecs = engine.FloatField(required=True)


class LogCrawler(BaseLog):
    meta = {'max_size': 5 * 2 ** 30,
            'max_documents': 10000000,
            'indexes': [
                '#url',
                '$task_name'
            ]}

    task_id = engine.ObjectIdField(verbose_name=u'任务ID')
    task_name = engine.StringField(max_length=32, verbose_name=u'任务名称')
    url = engine.URLField()


class LogDispatcher(BaseLog):
    meta = {'max_size': 512 * 2 ** 20, 'max_documents': 1000000}

    task_id = engine.ObjectIdField(verbose_name=u'任务ID')


class ThreadMongoHandler(logging.Handler):
    # reserve or special handled fields
    RECORD_FIELDS = {'threadName', 'name', 'thread', 'created', 'process', 'processName', 'args', 'module', 'filename',
                     'levelno', 'msg', 'message', 'exc_info', 'funcName', 'relativeCreated', 'levelname', 'asctime'}

    def __init__(self, log_model, max_thread=2, *args):
        super(ThreadMongoHandler, self).__init__(*args)

        assert issubclass(log_model, BaseLog), 'log_model must be a subclass of BaseLog'
        assert 0 < max_thread < 6, 'thread is not efficient enough, must be 1~5 threads'

        self.log_cls = log_model

        log_model.ensure_index('#ip')   # prevent bug: non-thread safe mongoengine collection creation

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
            sys.stderr.write('{0}: {1}'.format(datetime.now().strftime(LOG_DATEFORMAT), msg))
        except:
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
            for k, v in record.__dict__.iteritems():
                if isinstance(v, (basestring, int, long, float)):
                    msg[k] = v
            self.q.put_nowait(msg)
        except:
            self.handleError(record)

    def close(self):
        self._r = 0
        for p in self.tp:
            p.join()
        self._write('exit with %d logs remained' % self.q.qsize())

    def record(self):
        while self._r:
            try:
                msg = self.q.get(timeout=2)
            except Empty:
                continue
            except SystemExit:
                raise
            except:
                self._write()
                continue

            log = self.log_cls(
                ip=INNER_IP,
                pid=msg['process'],
                level=msg['levelno'],
                msg=msg['message'],
                time=msg['asctime']
            )
            for k, v in msg.iteritems():
                if k not in self.RECORD_FIELDS:
                    setattr(log, k, v)
            try:
                log.save()
            except AssertionError:
                self._write()
            except:
                # this supposed to be resolved
                self._write()
