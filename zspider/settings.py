# coding=utf-8
import os

from zspider.utils import ip


def _get_env(name, default=None):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return value


def _get_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return int(value)


def _split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(ROOT_PATH, "data")

ENV = _get_env("ZSPIDER_ENV", "development").lower()
DEBUG = _get_bool("ZSPIDER_DEBUG", ENV == "development")
IS_TESTING = ENV == "testing"
IS_PRODUCTION = ENV == "production"


def _default_bind_ip():
    try:
        return ip.get_ip()
    except Exception:
        return "127.0.0.1"


INNER_IP = _get_env("ZSPIDER_BIND_IP", _default_bind_ip())

LOG_LEVEL = _get_env("ZSPIDER_LOG_LEVEL", "DEBUG" if DEBUG else "INFO")

AMQP_URL = _get_env("ZSPIDER_AMQP_URL", "amqp://guest:guest@127.0.0.1/")
MEMCACHED_SERVERS = _split_csv(_get_env("ZSPIDER_MEMCACHED_SERVERS", "127.0.0.1:11211"))

MONGODB_DB = _get_env("ZSPIDER_MONGODB_DB", "spider")
MONGODB_URI = _get_env("ZSPIDER_MONGODB_URI")
MONGODB_HOST = _get_env("ZSPIDER_MONGODB_HOST", "localhost")
MONGODB_PORT = _get_int("ZSPIDER_MONGODB_PORT", 27017)
MONGODB_USERNAME = _get_env("ZSPIDER_MONGODB_USERNAME", "mongoadmin")
MONGODB_PASSWORD = _get_env("ZSPIDER_MONGODB_PASSWORD", "mongopwd")
MONGODB_AUTH_SOURCE = _get_env("ZSPIDER_MONGODB_AUTH_SOURCE", "admin")

WEB_HOST = _get_env("ZSPIDER_WEB_HOST", "127.0.0.1" if DEBUG else "0.0.0.0")
WEB_PORT = _get_int("ZSPIDER_WEB_PORT", 5000)
WEB_THREADS = _get_int("ZSPIDER_WEB_THREADS", 4)
WEB_SECRET_KEY = _get_env(
    "ZSPIDER_SECRET_KEY",
    "zspider-dev-secret-key-change-me",
)

DISPATCHER_UID = _get_env("ZSPIDER_DISPATCHER_UID", INNER_IP)
DISPATCHER_KEY = _get_env("ZSPIDER_DISPATCHER_KEY", "_zspider_cluster")
DISPATCHER_MANAGE_PORT = _get_int("ZSPIDER_MANAGE_PORT", 43722)
CRAWLER_MANAGE_PORT = _get_int("ZSPIDER_CRAWLER_MANAGE_PORT", 43723)
DISPATCHER_MANAGE_KEY = _get_env("ZSPIDER_MANAGE_KEY", "managekey-change-me")
DISPATCHER_BEAT_INTERVAL = _get_int("ZSPIDER_BEAT_INTERVAL", 5)

PUBLISH_URL = _get_env("ZSPIDER_PUBLISH_URL", "http://pubserver.com")
TRANSFORM_URL = _get_env(
    "ZSPIDER_TRANSFORM_URL",
    "http://image.server.com/totranslate/images",
)


def mongodb_settings():
    if MONGODB_URI:
        return {"db": MONGODB_DB, "host": MONGODB_URI}

    return {
        "db": MONGODB_DB,
        "host": MONGODB_HOST,
        "port": MONGODB_PORT,
        "username": MONGODB_USERNAME,
        "password": MONGODB_PASSWORD,
        "authentication_source": MONGODB_AUTH_SOURCE,
    }
