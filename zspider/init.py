# coding=utf-8
import logging

from scrapy.utils import log

from zspider.confs.conf import DEFAULT_LOGGING
from zspider.confs.conf import LOG_DATEFORMAT
from zspider.confs.conf import LOG_FORMAT
from zspider.confs.conf import LOG_TOP_LEVEL
from zspider.utils import engine
from zspider.utils.log import LogCrawler
from zspider.utils.log import LogDispatcher
from zspider.utils.log import ThreadMongoHandler

__author__ = "zephor"

done = False


INIT_CONF = {
    "dispatcher": {"log_model": LogDispatcher},
    "crawler": {"log_model": LogCrawler},
    "web": {"log_model": None},
}


def init(name=None):
    global done

    if done:
        return

    import datetime  # prevent bug for non-thread safe _strptime  see #issue8098

    datetime.datetime.strptime("20100309", "%Y%m%d")

    # init Task model connection
    from zspider.www.handlers import app

    engine.init_app(app)

    log.DEFAULT_LOGGING = DEFAULT_LOGGING
    log.configure_logging(install_root_handler=False)

    logging.logThreads = 0
    logging.logMultiprocessing = 0

    logging.root.setLevel(logging.NOTSET)

    conf = INIT_CONF.get(name, {})
    log_model = conf.get("log_model", None)
    if log_model:
        handler = ThreadMongoHandler(log_model)
    else:
        handler = logging.StreamHandler()

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
    handler.setFormatter(formatter)
    handler.addFilter(log.TopLevelFormatter(LOG_TOP_LEVEL))
    logging.root.addHandler(handler)

    done = True
