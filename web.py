# coding=utf-8
import sys
from conf import INNER_IP
from www.handlers import app

__author__ = 'zephor'

if __name__ == '__main__':
    import init
    init.init('web')
    if not init.done:
        print 'init fail'
        sys.exit(-1)
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
        app.run(host=INNER_IP, port=port)
    else:
        app.run(debug=True)
