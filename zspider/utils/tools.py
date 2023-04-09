import base64

from scrapy.utils.request import fingerprint


def req_fingerprint(request):
    fp = fingerprint(request)
    return base64.b85encode(fp).decode()
