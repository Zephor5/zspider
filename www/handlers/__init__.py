# coding=utf-8
from datetime import datetime
import urllib
import flask

from dispatcher_conf import STATE_DICT
from web_conf import FLASK_CONF
from utils.models import User
from www.tools import get_internal_msg

__author__ = 'zephor'

app = flask.Flask(__name__.split('.')[0])

app.config.update(FLASK_CONF)


@app.before_request
def is_login():
    if flask.request.path not in ('/login', '/logout') and 'user' not in flask.session:
        _login = urllib.basejoin(flask.request.url_root, 'login?to=%s' % flask.request.url)
        return flask.redirect(_login)


@app.route('/login')
def login():
    username = flask.request.form.get('username')
    user = None
    # noinspection PyBroadException
    try:
        user = User.objects.get(username=username)
    except:
        flask.abort(403)
    flask.session['user'] = username
    flask.session['role'] = user.role
    dst = flask.request.args.get('to', flask.url_for('index'))
    return flask.redirect(dst)


@app.route('/logout')
def logout():
    if 'user' in flask.session:
        user = flask.session['user']
        flask.session.pop('user')
        return '%s logout successfully' % user
    else:
        flask.abort(400)


@app.route('/')
def root():
    return flask.redirect(flask.url_for('index'))


@app.route('/index.html')
def index():
    msg = {}
    err = ''
    try:
        msg = get_internal_msg()
    except Exception as e:
        err = str(e)
    context = {
        'format_timestamp': lambda t: format(datetime.fromtimestamp(t), '%Y-%m-%d %H:%M:%S'),
        'state_dict': STATE_DICT,
        'states': msg,
        'err': err
    }
    return flask.render_template('index.html', **context)


@app.errorhandler(404)
def not_found(error):
    return flask.render_template('404.html'), 404


def _init():
    import os
    __file_root = os.path.dirname(os.path.abspath(__file__))
    for _, __, _fs in os.walk(__file_root):
        for m in _fs:
            if m.endswith('.py') and not m.startswith('_'):
                __import__('www.handlers.%s' % os.path.splitext(m)[0])


_init()
