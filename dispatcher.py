# coding=utf-8
import json
import logging
import time
import datetime
import tzlocal
import random

from twisted.web.resource import Resource
from twisted.internet import reactor, defer
from twisted.internet.error import ReactorNotRunning
from apscheduler.schedulers.twisted import TwistedScheduler
from apscheduler.jobstores.base import JobLookupError

from conf import AMQP_PARAM, TASK_Q_PARAMS, TASK_BIND_PARAMS
from dispatcher_conf import *
from utils.mypika import PooledConn
from utils.errors import DeferredTimeout
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


class HeartBeat(object):
    """
    a lazy heartbeat for zspider
    relying on rabbitmq
    """

    __expire = 5 * BEAT_INTERVAL

    def __init__(self, uid=None, loop=None):
        self._uid = UID if uid is None else uid
        self._loop = reactor if loop is None else loop

        self._rmsg = None
        self._msg = None

        self.__timeout_check = None
        self.__conn = None
        self.__channel = None
        self.__res_d = None

        self.beat()

    def __del__(self):
        self._loop.callLater(BEAT_INTERVAL, HeartBeat)
        logger.debug('one beat done')

    @defer.inlineCallbacks
    def _on_get(self, conn):
        logger.debug('get conn id:%s' % id(conn))

        self.__conn = conn

        channel = yield conn.channel()

        self.__channel = channel

        queue_object, consumer_tag = yield channel.basic_consume(queue=BEAT_Q_PARAMS['queue'], no_ack=False)

        self.__res_d = queue_object
        ch, method, properties, body = yield queue_object.get()
        logger.debug('get res, ch:%s, method:%s, properties:%s, body:%s' % (ch, method, properties, body))
        self._rmsg = body
        self.__timeout_check.cancel()
        yield ch.basic_ack(delivery_tag=method.delivery_tag)

    def _on_check(self):
        """
        check the heartbeat message and determine what to do next
        """
        del self.__timeout_check  # forbid ref cycle
        if not self._rmsg:
            if self.__res_d:
                # setup
                self.__res_d.close(DeferredTimeout('fetch timeout'))
            logger.warn('no rmsg get, current state is %s' % _state_)

    def _on_err_conn(self, err):
        """ this is not the finally error handler
        :return err  but set deal
        """
        logger.fatal(err)
        if hasattr(self, '__timeout_check'):
            self.__timeout_check.cancel()
        _stop_dispatch()
        err.deal__ = True
        return err

    @staticmethod
    def _on_err(err):
        if hasattr(err, 'deal__') and err.deal__:
            return err
        if isinstance(err.value, DeferredTimeout):
            logger.info('setup heartbeat')
            return
        logger.error(err)
        _stop_dispatch()
        err.deal__ = True
        return err
        # do some clean up on err occurred

    @staticmethod
    def _clear_err(err):
        if hasattr(err, 'deal__') and err.deal__:
            return
        _stop_dispatch()
        logger.error(err)

    def _on_beat(self):
        logger.debug('rmsg: %s' % self._rmsg)
        # mine = {'status': _state_, 'refresh': time.time()}
        msg = json.loads(self._rmsg) if self._rmsg else {}
        _msg = {}
        main_nodes = {}
        pending_nodes = {}

        if self._uid in msg:
            _msg = msg.pop(self._uid)

        for uid in msg.keys():
            _s = msg[uid].get('status')
            if _s == STATE_DISPATCH:
                main_nodes[uid] = msg.pop(uid)
            elif _s == STATE_PENDING:
                pending_nodes[uid] = msg.pop(uid)

        _len = len(main_nodes)
        if _len == 0:
            if _state_ == STATE_WAITING:
                if self.__check_state(pending_nodes):
                    # any node is pending already
                    self.__on_keep()
                else:
                    self.__on_pending()
            elif _state_ == STATE_PENDING and _msg['status'] == STATE_PENDING:
                self.__on_dispatch()
            else:
                self.__on_keep()
        else:
            if self.__check_state(main_nodes):
                if _state_ != STATE_WAITING:
                    self.__on_waiting()
                else:
                    self.__on_keep()
            else:
                if _state_ == STATE_WAITING:
                    self.__on_pending(main_nodes)
                else:
                    logger.error('unexpected state:%s' % locals())
                    if _state_ == STATE_PENDING:
                        self.__on_dispatch(main_nodes)
                    else:
                        self.__on_keep(main_nodes)

        message = {self._uid: {'status': _state_, 'refresh': time.time()}}
        message.update(msg)
        message.update(main_nodes)
        message.update(pending_nodes)
        return message

    @classmethod
    def __check_state(cls, nodes):
        """
        check other nodes, clear out dates
        :param nodes:
        :return: (bool) True if someone alive
        """
        status = False
        for uid in nodes.keys():
            if time.time() - nodes[uid]['refresh'] < cls.__expire:
                status = True
            else:
                nodes.pop(uid)
        return status

    @staticmethod
    def __reset_others(out_dates):
        if out_dates:
            for uid in out_dates:
                out_dates[uid]['status'] = STATE_WAITING

    def __on_waiting(self, out_dates=None):
        self.__reset_others(out_dates)
        _stop_dispatch()

    def __on_pending(self, out_dates=None):
        self.__reset_others(out_dates)
        _prepare_to_dispatch()

    def __on_dispatch(self, out_dates=None):
        self.__reset_others(out_dates)
        _start_dispatch()

    def __on_keep(self, out_dates=None):
        self.__reset_others(out_dates)

    @defer.inlineCallbacks
    def _send(self, msg):
        yield self.__channel.basic_publish(EXCHANGE_PARAMS['exchange'],
                                           BEAT_BIND_PARAMS['routing_key'], json.dumps(msg))
        self.__channel.close()
        defer.returnValue(self.__conn)

    def beat(self):
        d = pooled_conn.acquire()
        d.addCallbacks(self._on_get, self._on_err_conn)
        d.addErrback(self._on_err)
        d.addCallback(lambda _: self._on_beat())
        d.addCallback(self._send)
        d.addBoth(pooled_conn.release)  # release what acquired anyway
        d.addErrback(self._on_err)
        d.addErrback(self._clear_err)
        self.__timeout_check = self._loop.callLater(2, self._on_check)


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


def startup(main_job=HeartBeat):
    assert callable(main_job), 'main_job must be callable'

    @defer.inlineCallbacks
    def _set_up(channel):
        # do some setup
        yield channel.exchange_declare(**EXCHANGE_PARAMS)
        yield channel.queue_declare(**BEAT_Q_PARAMS)
        yield channel.queue_bind(**BEAT_BIND_PARAMS)
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
    reactor.callLater(0, startup)

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
