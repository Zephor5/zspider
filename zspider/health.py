# coding=utf-8
import memcache
from mongoengine.connection import get_db
from pika import BlockingConnection
from pika import URLParameters

from zspider import settings


def _error_message(exc):
    if isinstance(exc, PermissionError):
        return "network access not permitted in current environment"
    return str(exc)


def check_mongodb():
    try:
        get_db().command("ping")
    except Exception as exc:
        message = _error_message(exc)
        if "default connection" in message:
            message = "application is not initialized"
        return False, message
    return True, "ok"


def check_memcached():
    try:
        client = memcache.Client(settings.MEMCACHED_SERVERS, socket_timeout=1)
        stats = client.get_stats()
        if not stats:
            return False, "no response from memcached"
    except Exception as exc:
        return False, _error_message(exc)
    return True, "ok"


def check_rabbitmq():
    try:
        params = URLParameters(settings.AMQP_URL)
        params.socket_timeout = 2
        params.connection_attempts = 1
        params.blocked_connection_timeout = 2
        conn = BlockingConnection(params)
        conn.close()
    except Exception as exc:
        return False, _error_message(exc)
    return True, "ok"


def web_readiness():
    checks = {}

    ok, message = check_mongodb()
    checks["mongodb"] = {"status": "ready" if ok else "error", "detail": message}

    ok, message = check_memcached()
    checks["memcached"] = {"status": "ready" if ok else "error", "detail": message}

    ok, message = check_rabbitmq()
    checks["rabbitmq"] = {"status": "ready" if ok else "error", "detail": message}

    ready = all(item["status"] == "ready" for item in checks.values())
    return ready, checks
