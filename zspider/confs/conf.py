# coding=utf-8
import os

import six
from pika import URLParameters

from zspider.utils import ip

__author__ = "zephor"


ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_PATH = "%s/data/" % ROOT_PATH


try:
    assert int(os.getenv("ZSPIDER_PRODUCT")) == 1
except Exception:
    DEBUG = True
else:
    DEBUG = False


LOG_TOP_LEVEL = {"scrapy", "zspider", "www", "utils"}

LOG_PRO_INFO = "DEBUG" if DEBUG else "INFO"

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


INNER_IP = ip.get_ip()

MC_SERVERS = "127.0.0.1" if DEBUG else "memcache for production use"
MC_SERVERS = (
    MC_SERVERS.split(",") if isinstance(MC_SERVERS, six.string_types) else MC_SERVERS
)

if DEBUG:
    AMQP_PARAM = URLParameters("amqp://guest:guest@127.0.0.1")
else:
    AMQP_PARAM = URLParameters("amqp://spider:spider@amqpserver.for.production/spider")

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
