# coding=utf-8
import json
import logging
from queue import Queue

from pooled_pika import PooledConn
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from scrapy.utils.log import log_scrapy_info
from scrapy.utils.ossignal import install_shutdown_handlers
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.error import ConnectionDone
from twisted.web.resource import Resource

from zspider import settings as app_settings
from zspider.confs.conf import AMQP_PARAM
from zspider.confs.conf import EXCHANGE_PARAMS
from zspider.confs.conf import TASK_BIND_PARAMS
from zspider.confs.conf import TASK_Q_PARAMS
from zspider.models import RUN_ERROR_CRAWL_MESSAGE
from zspider.models import RUN_ERROR_CRAWL_RUNTIME
from zspider.models import RUN_STAGE_CRAWL
from zspider.task_messages import TaskDispatchMessage
from zspider.task_messages import TaskMessageError
from zspider.task_runs import fail_task_run
from zspider.task_runs import finish_task_run
from zspider.task_runs import mark_task_run_running

__author__ = "zephor"


logger = logging.getLogger("crawler")


class TestCrawler(CrawlerProcess):
    def __init__(self):
        from zspider.confs import crawl_conf as p_settings

        settings = Settings()
        settings.setmodule(p_settings)
        super(CrawlerProcess, self).__init__(settings)
        self._initialized_reactor = False
        self.task_q = defer.DeferredQueue()
        self.res_q = Queue()
        self.task_q.get().addCallback(self.crawl)

    def crawl(self, kwargs):
        spider_name = kwargs.pop("spider_name", "")
        crawler = self._create_crawler(spider_name)

        self.crawlers.add(crawler)
        d = crawler.crawl(**kwargs)
        self._active.add(d)

        def _done(_):
            self.crawlers.discard(crawler)
            self._active.discard(d)
            try:
                result = crawler.spider.test_result
                del crawler.spider.test_result
            except AttributeError:
                result = None  # spider may be None in case Failure
            self.res_q.put(result)
            return _

        d.addBoth(_done)
        d.addErrback(lambda _: logger.error(_))
        d.addCallback(lambda _: self.task_q.get().addCallback(self.crawl))
        return d


def debug(_=None):
    """
    for debug use
    """
    import objgraph

    # with open('logs/test', 'w') as f:
    #     objs = objgraph.get_leaking_objects()
    #     for o in objs:
    #         f.write('%s\n' % o.encode('utf-8') if isinstance(o, unicode) else str(o))
    leak_ref = objgraph.by_type("Newspaper")
    objgraph.show_backrefs(leak_ref, max_depth=10, filename="my_leak.png")


class CrawlerDaemon(CrawlerProcess):
    def __init__(self):
        from zspider.confs import crawl_conf as p_settings

        settings = Settings()
        settings.setmodule(p_settings)
        super(CrawlerProcess, self).__init__(
            settings
        )  # 跳过CrawlerProcess的初始日志配置，由init.py处理
        self._initialized_reactor = False
        install_shutdown_handlers(self._signal_shutdown)
        log_scrapy_info(self.settings)

        self.__task_queue = None
        self._pconn = PooledConn(AMQP_PARAM)
        self._set_up()

    def health_payload(self):
        return {
            "status": "ok",
            "service": "crawler",
            "active_crawlers": len(self.crawlers),
        }

    def readiness_payload(self):
        checks = {
            "connection": {
                "status": "ready" if hasattr(self, "_conn") else "error",
                "detail": "connected" if hasattr(self, "_conn") else "not connected",
            },
            "channel": {
                "status": "ready" if hasattr(self, "_channel") else "error",
                "detail": "open" if hasattr(self, "_channel") else "not initialized",
            },
            "task_queue": {
                "status": "ready" if self.__task_queue is not None else "error",
                "detail": "consuming"
                if self.__task_queue is not None
                else "not consuming",
            },
        }
        ready = all(item["status"] == "ready" for item in checks.values())
        payload = {
            "status": "ready" if ready else "error",
            "service": "crawler",
            "checks": checks,
            "active_crawlers": len(self.crawlers),
        }
        return ready, payload

    def _set_up(self, _=None):
        d = self._pconn.acquire()
        d.addCallbacks(self._on_conn, self._on_err_conn)
        d.addErrback(self._on_err)

    @defer.inlineCallbacks
    def _on_conn(self, conn):
        # in case the connection is lost; mostly closed by the mq server
        conn.ready.addErrback(self.__clear)
        conn.ready.addCallback(self._set_up)
        self._conn = conn
        channel = self._channel = yield conn.channel()
        # do some setup
        yield channel.exchange_declare(**EXCHANGE_PARAMS)
        yield channel.queue_declare(**TASK_Q_PARAMS)
        yield channel.queue_bind(**TASK_BIND_PARAMS)

        self.__task_queue, consumer_tag = yield channel.basic_consume(
            queue=TASK_Q_PARAMS["queue"], auto_ack=False
        )
        yield self._on_get()

    @staticmethod
    def _on_err_conn(err):
        logger.fatal(err)

    @staticmethod
    def _on_err(err):
        if err.type is ConnectionDone:
            logger.info("connection lost when waiting, handled..")
        else:
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
        logger.info("_on_msg %s" % body)
        run_id = None
        try:
            msg = TaskDispatchMessage.from_body(body)
            run_id = msg.run_id
            self.settings.set("COOKIES_ENABLED", msg.needs_login, "spider")
            d = self.crawl(
                msg.spider,
                parser=msg.parser,
                task_id=msg.task_id,
                task_name=msg.task_name,
                run_id=run_id,
            )
            # d.addCallback(lambda som: reactor.callLater(2, debug))
            d.addErrback(lambda err: logger.error(err))
        except (TaskMessageError, Exception) as e:
            fail_task_run(run_id, RUN_STAGE_CRAWL, RUN_ERROR_CRAWL_MESSAGE, repr(e))
            logger.error(repr(e))
        if len(self._active) > 1:
            return self.join()

    def __clear(self, _=None):
        if self.__task_queue is not None:
            self.__task_queue.close(ConnectionDone("done"))

    def crawl(self, spider_name, *args, **kwargs):
        crawler = self._create_crawler(spider_name)
        crawler.signals.connect(self._on_spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(self._on_spider_error, signal=signals.spider_error)
        crawler.signals.connect(self._on_spider_closed, signal=signals.spider_closed)

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
                pass  # spider may be None in case Failure
            return result

        return d.addBoth(_done)

    @staticmethod
    def _on_spider_opened(spider):
        mark_task_run_running(getattr(spider, "run_id", None))

    @staticmethod
    def _on_spider_error(failure, response, spider):
        fail_task_run(
            getattr(spider, "run_id", None),
            RUN_STAGE_CRAWL,
            RUN_ERROR_CRAWL_RUNTIME,
            failure.getErrorMessage(),
            latest_url=getattr(response, "url", None),
        )

    @staticmethod
    def _on_spider_closed(spider, reason):
        finish_task_run(getattr(spider, "run_id", None), close_reason=reason)


class CrawlerManage(Resource):
    isLeaf = True

    def __init__(self, daemon):
        super(CrawlerManage, self).__init__()
        self.daemon = daemon

    def render_GET(self, request):
        request.setHeader("content-type", "application/json;charset=UTF-8")
        path = request.path.decode("utf-8")
        if path == "/healthz":
            return self._json_response(self.daemon.health_payload())
        if path == "/readyz":
            ready, payload = self.daemon.readiness_payload()
            request.setResponseCode(200 if ready else 503)
            return self._json_response(payload)
        request.setResponseCode(404)
        return self._json_response({"status": "error", "service": "crawler"})

    @staticmethod
    def _json_response(payload):
        return json.dumps(payload).encode("utf-8")


def main():
    from zspider import init

    init.init("crawler")
    if init.done:
        p = CrawlerDaemon()
        from twisted.web.server import Site
        from twisted.internet import endpoints

        endpoints.serverFromString(
            reactor,
            "tcp:%s:interface=%s"
            % (app_settings.CRAWLER_MANAGE_PORT, app_settings.INNER_IP),
        ).listen(Site(CrawlerManage(p)))
        p.start(stop_after_crawl=False)


if __name__ == "__main__":
    main()
