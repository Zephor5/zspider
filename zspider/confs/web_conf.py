# coding=utf-8
from zspider import settings

__author__ = "zephor"

FLASK_CONF = {
    "SECRET_KEY": settings.WEB_SECRET_KEY,
    "MONGODB_SETTINGS": settings.mongodb_settings(),
    "ENV": settings.ENV,
    "DEBUG": settings.DEBUG,
    "TESTING": settings.IS_TESTING,
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
}
