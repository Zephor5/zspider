# coding=utf-8
import functools

from flask import session, abort, request

__author__ = 'zephor'


def acquire_admin(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if session['role'] != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return wrap


def acquire_xhr(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not request.is_xhr:
            abort(403)
        return f(*args, **kwargs)
    return wrap
