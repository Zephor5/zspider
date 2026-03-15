# coding=utf-8
from pika import URLParameters

from zspider import settings

__author__ = "zephor"


ROOT_PATH = settings.ROOT_PATH

DATA_PATH = settings.DATA_PATH

DEBUG = settings.DEBUG


LOG_TOP_LEVEL = {"scrapy", "zspider", "www", "utils"}

LOG_PRO_INFO = settings.LOG_LEVEL

DEFAULT_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "scrapy": {"level": "INFO"},
        "twisted": {"level": "ERROR"},
        "pika": {"level": "ERROR"},
        "pooled_pika": {"level": "ERROR"},
        "apscheduler": {"level": "ERROR"},
        "utils": {"level": LOG_PRO_INFO},
        "zspider": {"level": LOG_PRO_INFO},
        "dispatcher": {"level": LOG_PRO_INFO},
        "crawler": {"level": LOG_PRO_INFO},
    },
}

LOG_FORMAT = "[%(name)s:%(lineno)d] %(asctime)s %(levelname)s:%(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"


INNER_IP = settings.INNER_IP

MC_SERVERS = settings.MEMCACHED_SERVERS

AMQP_PARAM = URLParameters(settings.AMQP_URL)

EXCHANGE_PARAMS = dict(exchange="spider", exchange_type="direct")

TASK_Q_PARAMS = dict(
    queue="task",
    durable=True,
    auto_delete=False,
    exclusive=False,
    arguments={"x-message-ttl": 60000},
)
TASK_BIND_PARAMS = dict(
    exchange=EXCHANGE_PARAMS["exchange"],
    queue=TASK_Q_PARAMS["queue"],
    routing_key="spider.task",
)
