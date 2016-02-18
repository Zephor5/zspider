# coding=utf-8
import json
import logging
import time
import datetime
import tzlocal
import random
import threading
import memcache

from twisted.web.resource import Resource
from twisted.internet import reactor, defer
from twisted.internet.error import ReactorNotRunning
from apscheduler.schedulers.twisted import TwistedScheduler
from apscheduler.jobstores.base import JobLookupError
from pooled_pika import PooledConn

from conf import MC_SERVERS, AMQP_PARAM, TASK_Q_PARAMS, TASK_BIND_PARAMS
from dispatcher_conf import *
from utils.models import Task

__author__ = 'zephor'

logger = logging.getLogger('dispatcher')

pooled_conn = PooledConn(AMQP_PARAM)
scheduler = TwistedScheduler()

_state_ = STATE_WAITING


def _prepare_to_dispatch():
    global _state_
    _state_ = STATE_PENDING
    load_tasks()


def _start_dispatch():
    global _state_
    logger.info('start dispatch')
    scheduler.start()
    _state_ = STATE_DISPATCH


def _stop_dispatch():
    global _state_
    if _state_ == STATE_DISPATCH:
        logger.info('stop dispatch')
        scheduler.shutdown()
        _state_ = STATE_WAITING


class HeartBeat(threading.Thread):
    """
    heartbeat for dispatcher
    relying on memcache
    """

    __expire = 5 * BEAT_INTERVAL

    def __init__(self):
        super(HeartBeat, self).__init__()
        self._key = DISPATCHER_KEY
        self._mc = memcache.Client(MC_SERVERS, socket_timeout=1, cache_cas=True)
        self._expire = BEAT_INTERVAL * 2

    def _on_beat(self, rmsg):
        logger.debug('rmsg: %s' % rmsg)
        # mine = {'status': _state_, 'refresh': time.time()}
        msg = json.loads(rmsg) if rmsg else {}
        _msg = {}
        main_nodes = {}
        pending_nodes = {}

        self.__clear_expire(msg)

        if UID in msg:
            _msg = msg.pop(UID)

        for uid in msg.keys():
            _s = msg[uid].get('status')
            if _s == STATE_DISPATCH:
                main_nodes[uid] = msg.pop(uid)
            elif _s == STATE_PENDING:
                pending_nodes[uid] = msg.pop(uid)

        _len = len(main_nodes)
        if _len == 0:
            if _state_ == STATE_WAITING:
                if pending_nodes:
                    # any node is pending already
                    self.__on_keep()
                else:
                    self.__on_pending()
            elif _state_ == STATE_PENDING and _msg.get('status') == STATE_PENDING:
                self.__on_dispatch()
            else:
                self.__on_keep()
        else:
            if _state_ != STATE_WAITING:
                self.__on_waiting()
            else:
                self.__on_keep()

        message = {UID: {'status': _state_, 'refresh': time.time()}}
        message.update(msg)
        message.update(main_nodes)
        message.update(pending_nodes)
        return json.dumps(message)

    @classmethod
    def __clear_expire(cls, nodes):
        """
        clear out dates
        :param nodes:
        """
        for uid in nodes.keys():
            if time.time() - nodes[uid]['refresh'] > cls.__expire:
                nodes.pop(uid)

    @staticmethod
    def __on_waiting():
        _stop_dispatch()

    @staticmethod
    def __on_pending():
        _prepare_to_dispatch()

    @staticmethod
    def __on_dispatch():
        _start_dispatch()

    def __on_keep(self):
        pass

    def run(self):
        reties = 0
        while 1:
            rmsg = self._mc.gets(self._key)
            msg = self._on_beat(rmsg)
            if rmsg:
                if self._mc.cas(self._key, msg, self._expire):
                    reties = 0
                    time.sleep(BEAT_INTERVAL)
                else:
                    reties += 1
            else:
                if self._mc.add(self._key, msg, self._expire):
                    reties = 0
                    time.sleep(BEAT_INTERVAL)
                else:
                    reties += 1
            if reties > 3:
                logger.error('retries too much, may net error')
                _stop_dispatch()
                time.sleep(self.__expire + 1)


class Send(object):
    def __init__(self, msg, rand=False):
        self.task_id = msg['id']
        self.msgs = json.dumps(msg)
        self._doing = False
        self._rand = rand
        self._max = None

    def __call__(self):
        if self._doing:
            logger.warn('last doing, skip this', extra={'task_id': self.task_id})
        else:
            self._doing = True
            d = pooled_conn.acquire(channel=True)
            d.addCallbacks(self._on_send, self._on_err_conn)
            d.addBoth(pooled_conn.release)
            d.addErrback(self._on_err)
            if self._rand:
                self._rand_reschedule()
            logger.info('dispatch %s' % self.msgs, extra={'task_id': self.task_id})

    def _rand_reschedule(self):
        _now = datetime.datetime.now(tzlocal.get_localzone())
        if self._max is None:
            job = scheduler.get_job(self.task_id)
            r = job.next_run_time - _now
            r = round(r.total_seconds()) * 2
            self._max = r - 60 if r > 60 else 0
        next_sec = (random.random() * self._max) + 60
        job = scheduler.add_job(self, id=self.task_id, misfire_grace_time=20, replace_existing=True,
                                run_date=_now + datetime.timedelta(seconds=next_sec))
        logger.info('random schedule next run time, at %s' % job.next_run_time, extra={'task_id': self.task_id})

    def _on_err_conn(self, err):
        logger.error(err)
        self._doing = False

    def _on_err(self, err):
        logger.error(err)
        self._doing = False

    @defer.inlineCallbacks
    def _on_send(self, channel):
        logger.debug('get channel id:%s' % id(channel))
        # noinspection PyBroadException
        try:
            yield channel.basic_publish(EXCHANGE_PARAMS['exchange'],
                                        TASK_BIND_PARAMS['routing_key'],
                                        self.msgs)
        except:
            logger.exception('send gets error', extra={'task_id': self.task_id})
        finally:
            self._doing = False
            defer.returnValue(channel)


def load_tasks(task_id=None):
    num = 0
    job = None

    trigger_keys = ('minute', 'hour', 'day', 'month', 'day_of_week')
    kwargs = dict(is_active=True, cron__ne="")
    if task_id is not None:
        kwargs['id'] = task_id
    for task in Task.objects.filter(**kwargs):
        msg = {
            "id": str(task.id),
            "name": task.name,
            "spider": task.spider,
            "parser": task.parser,
            "is_login": task.is_login
        }
        logger.debug(msg)
        trigger_kwargs = dict(zip(trigger_keys, task.cron.split(' ')))
        trigger_kwargs['second'] = str(random.random() * 60).split('.')[0]
        try:
            job = scheduler.add_job(Send(msg, rand=msg['spider'] == 'wechat'), id=msg['id'], trigger="cron",
                                    misfire_grace_time=20,
                                    replace_existing=True,
                                    **trigger_kwargs)
        except ValueError:
            logger.error('failed to add job %s' % task, extra={'task_id': msg['id']})
        else:
            logger.info('add job %s' % task, extra={'task_id': msg['id']})
            num += 1
    if task_id:
        return job
    else:
        return num


class TaskManage(Resource):
    isLeaf = True

    res = {
        "status": False,
        "data": ""
    }

    def render_GET(self, request):

        res = dict(self.res)

        request.setHeader("content-type", "application/json;charset=UTF-8")
        import urllib

        args = urllib.unquote(request.path).split('/', 3)

        if args[-1] != MANAGE_KEY:
            res['status'] = False
            res['data'] = 'no authenticated'
            return json.dumps(res)

        res['status'] = True
        args = args[1:-1]
        _l = len(args)
        if _l == 0:
            res['data'] = 'dispatcher state: %s' % STATE_DICT[_state_]
        elif _l == 1:
            if args[0] == 'reload':
                nums = load_tasks()
                res['data'] = '%s tasks loaded' % nums
        elif _l == 2:
            action, task_id = args
            if action == 'load':
                job = load_tasks(task_id)
                if job:
                    res['data'] = 'job loaded successfully, will first run at %s' % job.next_run_time
                else:
                    res['status'] = False
                    res['data'] = 'no job loaded'
            elif action == 'pause':
                try:
                    scheduler.pause_job(task_id)
                    res['data'] = 'task %s paused' % task_id
                except JobLookupError as e:
                    res['status'] = False
                    res['data'] = e.message
            elif action == 'remove':
                try:
                    scheduler.remove_job(task_id)
                    res['data'] = 'task %s removed' % task_id
                except JobLookupError as e:
                    res['status'] = False
                    res['data'] = e.message
        logger.info(res['data'], extra={'component': 'manager'})

        return json.dumps(res)


def startup(main_job):
    assert callable(main_job), 'main_job must be callable'

    @defer.inlineCallbacks
    def _set_up(channel):
        # do some setup
        yield channel.exchange_declare(**EXCHANGE_PARAMS)
        yield channel.queue_declare(**TASK_Q_PARAMS)
        yield channel.queue_bind(**TASK_BIND_PARAMS)
        defer.returnValue(channel)

    def _fatal(err=None):
        import sys
        if err is not None:
            print err
            try:
                reactor.stop()
            except ReactorNotRunning:
                pass
            finally:
                sys.exit(-1)

    def _startup(_=None):
        logger.debug('ready to beat up')
        reactor.callLater(0, main_job)

    d = pooled_conn.acquire(channel=True)
    d.addCallbacks(_set_up, _fatal)
    d.addBoth(pooled_conn.release)  # release connection
    d.addCallbacks(_startup, _fatal)
    return d


def main():
    main_job = HeartBeat()
    main_job.setDaemon(True)
    reactor.callLater(0, startup, main_job.start)

    # dispatcher http manage api
    from twisted.web.server import Site
    from twisted.internet import endpoints

    endpoints.serverFromString(reactor, "tcp:%s:interface=%s" % (MANAGE_PORT, UID)).listen(Site(TaskManage()))

    try:
        import fcntl
        from conf import DATA_PATH
        unique_f = open('%sunique' % DATA_PATH, 'w')
        fcntl.lockf(unique_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logger.error('dispatcher already running')
    else:
        logger.info('loop start')
        reactor.run()


if __name__ == '__main__':
    import init

    init.init('dispatcher')
    if init.done:
        main()
