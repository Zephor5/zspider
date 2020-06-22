# coding=utf-8
import json

__author__ = "zhihui9"


def validate_forms(forms):
    for f in forms:
        if not f.validate():
            return False
    return True


def get_internal_msg():
    import memcache
    from zspider.confs.conf import MC_SERVERS
    from zspider.confs.dispatcher_conf import DISPATCHER_KEY

    mc = memcache.Client(MC_SERVERS)
    msg = mc.get(DISPATCHER_KEY)
    return json.loads(msg if msg else "{}")
