# coding=utf-8
"""Set User-Agent header per spider or use a default value from settings"""
import random

__author__ = "zephor"


class RandUAMiddleware(object):
    """This middleware allows spiders to override the user_agent"""

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_%d_%d) "
        "AppleWebKit/%d.%d (KHTML, like Gecko) Chrome/%d.0.%d.86 Safari/%d.%d"
    )

    def process_request(self, request, spider):
        a = random.randint(480, 537)
        b = random.randint(27, 36)
        ua = self.USER_AGENT % (
            random.randint(1, 11),
            random.randint(1, 3),
            a,
            b,
            random.randint(42, 47),
            random.randint(2380, 2526),
            a,
            b,
        )
        request.headers.setdefault("User-Agent", ua)
