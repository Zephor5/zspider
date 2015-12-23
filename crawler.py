# coding=utf-8
import logging
import json
import scrapy

from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from scrapy.utils.log import log_scrapy_info
from scrapy.utils.ossignal import install_shutdown_handlers
from twisted.internet import defer

from conf import AMQP_PARAM, EXCHANGE_PARAMS, TASK_Q_PARAMS, TASK_BIND_PARAMS
from utils.mypika import PooledConn

__author__ = 'zephor'


logger = logging.getLogger('crawler')
scrapy.optional_features.discard('boto')


class CrawlerDaemon(CrawlerProcess):

    def __init__(self):
        import crawl_conf as p_settings

        settings = Settings()
        settings.setmodule(p_settings)
        super(CrawlerProcess, self).__init__(settings)  # 跳过CrawlerProcess的初始日志配置，由init.py处理
        install_shutdown_handlers(self._signal_shutdown)
        log_scrapy_info(self.settings)

        self._pconn = PooledConn(AMQP_PARAM)
        self._set_up()

    def _set_up(self, _=None):
        d = self._pconn.acquire()
        d.addCallbacks(self._on_conn, self._on_err_conn)
        d.addErrback(self._on_err)

    @defer.inlineCallbacks
    def _on_conn(self, conn):
        self._conn = conn
        channel = self._channel = yield conn.channel()
        # do some setup
        yield channel.exchange_declare(**EXCHANGE_PARAMS)
        yield channel.queue_declare(**TASK_Q_PARAMS)
        yield channel.queue_bind(**TASK_BIND_PARAMS)

        self.__task_queue, consumer_tag = yield channel.basic_consume(queue=TASK_Q_PARAMS['queue'], no_ack=False)
        yield self._on_get()

    @staticmethod
    def _on_err_conn(err):
        logger.fatal(err)

    @staticmethod
    def _on_err(err):
        logger.error(err)

    @defer.inlineCallbacks
    def _on_get(self):
        ch, method, properties, body = yield self.__task_queue.get()
        d = self._on_msg(body)
        yield ch.basic_ack(delivery_tag=method.delivery_tag)
        if isinstance(d, defer.Deferred):
            self._channel.close()
            self._pconn.release(self._conn)
            d.addCallback(self._set_up)
        else:
            d = self._on_get()
        yield d

    def _on_msg(self, body):
        logger.info('_on_msg %s' % body)
        try:
            msg = json.loads(body)
            self.settings.set('COOKIES_ENABLED', msg['is_login'], 'spider')
            d = self.crawl(msg['spider'], task_id=msg['id'], task_name=msg['name'], parser=msg['parser'])
            d.addErrback(lambda err: logger.error(err))
        except Exception as e:
            logger.error(repr(e))
        if len(self._active) > 1:
            return self.join()

    def crawl(self, spider_name, *args, **kwargs):
        crawler = self._create_crawler(spider_name)

        self.crawlers.add(crawler)
        d = crawler.crawl(*args, **kwargs)
        self._active.add(d)

        def _done(result):
            self.crawlers.discard(crawler)
            self._active.discard(d)
            # parser may hold large memory, release it manually
            try:
                del crawler.spider.parser
            except AttributeError:
                pass    # spider may be None in case Failure
            return result

        return d.addBoth(_done)


if __name__ == '__main__':
    import init
    init.init('crawler')
    if init.done:
        p = CrawlerDaemon()
        p.start(stop_after_crawl=False)
