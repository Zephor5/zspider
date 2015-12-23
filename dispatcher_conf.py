# coding=utf-8
from conf import INNER_IP, EXCHANGE_PARAMS

__author__ = 'zephor'

__all__ = ['UID', 'MANAGE_PORT', 'MANAGE_KEY', 'STATE_WAITING', 'STATE_PENDING', 'STATE_DISPATCH', 'STATE_DICT',
           'EXCHANGE_PARAMS', 'BEAT_Q_PARAMS', 'BEAT_BIND_PARAMS', 'BEAT_INTERVAL']

UID = INNER_IP

MANAGE_PORT = 43722

MANAGE_KEY = '#managekey$$'  # you can change this as you wish

# internal use
STATE_WAITING = 0x00  # stand by state
STATE_PENDING = 0x01  # ready to work
STATE_DISPATCH = 0x02  # working

STATE_DICT = {
    STATE_WAITING: 'waiting',
    STATE_PENDING: 'pending',
    STATE_DISPATCH: 'dispatch'
}

BEAT_Q_PARAMS = dict(queue='beat', durable=True, auto_delete=False, exclusive=False)

BEAT_BIND_PARAMS = dict(exchange=EXCHANGE_PARAMS['exchange'], queue=BEAT_Q_PARAMS['queue'], routing_key='spider.beat')

BEAT_INTERVAL = 5
