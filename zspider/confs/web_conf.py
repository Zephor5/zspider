# coding=utf-8
from .conf import DEBUG

__author__ = "zephor"

FLASK_CONF = {
    "SECRET_KEY": "\x02\xcf\x12\\\x95\xbe\xc0\xc4\x03\xb8\xde\x198\x04\xd7\x88\xfe\x82\xfc\xf73\xf1v\xa3",
    "MONGODB_SETTINGS": {
        "db": "spider",
        "host": "host for production",
        "port": 27017,
        "username": "user",
        "password": "pwd",
        "authentication_source": "admin",
    },
}

if DEBUG:
    # mongodb for dev
    FLASK_CONF["MONGODB_SETTINGS"].update(
        {
            "host": "localhost",
            "username": "mongoadmin",
            "password": "mongopwd",
        }
    )
