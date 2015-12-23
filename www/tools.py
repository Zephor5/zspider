# coding=utf-8
import json

__author__ = 'zhihui9'


def validate_forms(forms):
    for f in forms:
        if not f.validate():
            return False
    return True


def get_internal_msg():
    import pika
    from conf import AMQP_PARAM
    from dispatcher_conf import BEAT_Q_PARAMS

    mq = pika.BlockingConnection(AMQP_PARAM)
    channel = mq.channel()
    _method, _p, _body = channel.basic_get(BEAT_Q_PARAMS['queue'])
    channel.basic_reject(_method.delivery_tag)
    channel.close()
    return json.loads(_body)
