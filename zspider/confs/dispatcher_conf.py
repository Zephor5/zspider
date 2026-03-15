# coding=utf-8
from zspider import settings

from .conf import EXCHANGE_PARAMS

__author__ = "zephor"

__all__ = [
    "UID",
    "DISPATCHER_KEY",
    "MANAGE_PORT",
    "MANAGE_KEY",
    "STATE_WAITING",
    "STATE_PENDING",
    "STATE_DISPATCH",
    "STATE_DICT",
    "EXCHANGE_PARAMS",
    "BEAT_INTERVAL",
]

UID = settings.DISPATCHER_UID

DISPATCHER_KEY = settings.DISPATCHER_KEY

MANAGE_PORT = settings.DISPATCHER_MANAGE_PORT

MANAGE_KEY = settings.DISPATCHER_MANAGE_KEY

# internal use
STATE_WAITING = 0x00  # stand by state
STATE_PENDING = 0x01  # ready to work
STATE_DISPATCH = 0x02  # working

STATE_DICT = {
    STATE_WAITING: "waiting",
    STATE_PENDING: "pending",
    STATE_DISPATCH: "dispatch",
}

BEAT_INTERVAL = settings.DISPATCHER_BEAT_INTERVAL
