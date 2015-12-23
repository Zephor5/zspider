# coding=utf-8
import logging
import thread

from contextlib import contextmanager
from pika.adapters import TwistedProtocolConnection
from pika.adapters.twisted_connection import TwistedChannel
from pika.connection import Parameters
from twisted.internet import reactor, defer
from twisted.internet.protocol import ClientCreator

__author__ = 'zephor'

logger = logging.getLogger(__name__)

__lock = thread.allocate_lock()


@contextmanager
def _lock():
    __lock.acquire()
    try:
        yield
    finally:
        __lock.release()


class PooledConn(object):
    """
    """

    _my_params = {}
    _my_pools = ({}, {})
    _my_channels = {}
    _timeout = {}
    _max_size = {}
    _waiting = {}

    max_size = 100

    # retry once by default
    retry = True

    timeout_conn = 1

    loop = reactor

    def __new__(cls, params, timeout_conn=None, max_size=None):
        """
        :param cls:
        :param params: connection params
        :param timeout_conn: connection timeout
        :param max_size: max pool size for each connection
        :return: PoolConn instance
        """
        if isinstance(params, Parameters):
            _id = repr(params)  # take repr of params for id to identify the pool
            instance = super(PooledConn, cls).__new__(cls)
            if _id in cls._my_params:
                # always update the params instance
                cls._my_params[_id] = params
            else:
                cls._my_params[_id] = params
                cls._my_pools[0][_id] = {}
                cls._my_pools[1][_id] = {}
                cls._my_channels[_id] = {}
                cls._max_size[_id] = max_size if max_size else cls.max_size
                cls._timeout[_id] = timeout_conn if timeout_conn > 0 else cls.timeout_conn
                cls._waiting[_id] = []
                # only works when first created
            instance.__params = cls._my_params[_id]
            instance.__max_size = cls._max_size[_id]
            instance.timeout_conn = cls._timeout[_id]
            instance.__idle_pool, instance.__using_pool = (cls._my_pools[i][_id] for i in (0, 1))
            instance.__channel_pool = cls._my_channels[_id]
            instance.waiting = cls._waiting[_id]
            return instance
        else:
            raise TypeError('only accept pika Parameters type')

    def __init__(self, *args, **kwargs):
        """
        :param args: to keep with the __new__
        :param kwargs: to keep with the __new__
        :return:
        """
        # self.__params
        # self.__max_size
        # self.timeout_conn
        # self.__idle_pool
        # self.__using_pool
        # self.__channel_pool

    def __connect(self, retrying=False):
        params = self.__params
        cc = ClientCreator(self.loop, TwistedProtocolConnection, params)
        _d = cc.connectTCP(params.host, params.port, timeout=self.timeout_conn)
        _d.addCallback(lambda p: p.ready)
        _d.addCallbacks(self._in_pool,
                        lambda err: err if retrying or not self.retry else self.__connect(True))  # retry once when err
        return _d

    def _in_pool(self, conn):
        assert isinstance(conn, TwistedProtocolConnection), 'conn must be TwistedProtocolConnection'
        logger.debug('in pool : %s' % conn)

        _id = id(conn)

        if self.size < self.__max_size:
            # add hook to clear the bad connection object in the pool
            conn.ready = defer.Deferred()
            conn.ready.addErrback(self._clear, self.__idle_pool, self.__using_pool, self.__channel_pool, _id)
            # add new conn in using pool
            self.__using_pool[_id] = conn
        else:
            raise RuntimeError('_in_pool, unexpected reach')

        return conn

    @staticmethod
    def _clear(reason, idle_pool, using_pool, channel_pool, conn_id):
        """
        clear the bad connection
        :param reason:
        :param idle_pool:
        :param using_pool:
        :param channel_pool:
        :param conn_id:
        :return:
        """
        logger.info('connection lost, reason:%s' % reason)
        with _lock():
            try:
                idle_pool.pop(conn_id)
            except KeyError:
                using_pool.pop(conn_id, None)
            finally:
                channel_pool.pop(conn_id, None)

    def _get_channel(self, conn):
        _id = id(conn)
        d = None
        p = self.__channel_pool
        if _id in p:
            channel = p[_id]
            if channel.is_open:
                d = defer.Deferred()
                d.callback(p[_id])
        if d is None:
            d = conn.channel()
            d.addCallback(lambda ch: p.update({_id: ch}) or setattr(ch, 'pool_id_', _id) or ch)
        return d

    def acquire(self, channel=False):
        d = defer.Deferred()
        if channel:
            d.addCallback(self._get_channel)
        with _lock():
            if self.__idle_pool:
                _id, conn = self.__idle_pool.popitem()
                self.__using_pool[_id] = conn
                self.loop.callLater(0, d.callback, conn)
                return d
        if self.size >= self.__max_size:
            self.waiting.append(d)
        else:
            self.__connect().chainDeferred(d)
        return d

    def release(self, c):
        if isinstance(c, TwistedProtocolConnection):
            _id = id(c)
        elif isinstance(c, TwistedChannel):
            _id = c.pool_id_
        else:
            return c
        if _id in self.__using_pool:
            if self.waiting:
                self.waiting.pop(0).callback(c)
            else:
                with _lock():
                    # put the conn back to idle
                    self.__idle_pool[_id] = self.__using_pool.pop(_id)

    @property
    def size(self):
        with _lock():
            return len(self.__idle_pool) + len(self.__using_pool)


if __name__ == '__main__':
    with _lock():
        print PooledConn.__mro__
