# coding=utf-8
import sys
import threading

from zspider import settings
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
    port = int(sys.argv[1]) if len(sys.argv) == 2 else settings.WEB_PORT

    try:
        from waitress import serve
    except ImportError as exc:
        raise RuntimeError(
            "waitress is required to run zspider.web; install requirements first"
        ) from exc

    serve(app, host=settings.WEB_HOST, port=port, threads=settings.WEB_THREADS)


if __name__ == "__main__":
    main()
