# coding=utf-8
from .conf import DEBUG

__author__ = "zephor"


FLASK_CONF = {
    "SECRET_KEY": "\x02\xcf\x12\\\x95\xbe\xc0\xc4\x03\xb8\xde\x198\x04\xd7\x88\xfe\x82\xfc\xf73\xf1v\xa3",
    "MONGODB_SETTINGS": {
        "host": "mongodb://user:pwd@host:port/spider"  # mongodb for production
    },
}

if DEBUG:
    # mongodb for dev
    FLASK_CONF["MONGODB_SETTINGS"].update({"host": "mongodb://localhost:27017/spider"})
