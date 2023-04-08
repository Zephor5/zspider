# coding=utf-8
import sys
import threading

from zspider.confs.conf import INNER_IP
from zspider.www.handlers import app
from zspider.www.utils import test_crawler

__author__ = "zephor"


def main():
    from zspider import init

    init.init("web")
    if not init.done:
        print("init fail")
        sys.exit(-1)
    t = threading.Thread(target=test_crawler.start, args=(False, False))
    t.setDaemon(True)
    t.start()
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
        app.run(host=INNER_IP, port=port)
    else:
        app.run(host=INNER_IP, debug=True)


if __name__ == "__main__":
    main()
