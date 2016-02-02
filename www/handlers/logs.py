# coding=utf-8
from flask import request, render_template, abort, jsonify

import init
from utils.log import BaseLog, LEVELS
from utils.models import Task
from www.utils import acquire_xhr
from zspider.models import ITEM_STATUS, Item
from . import app

__author__ = 'zephor'


def _get_cls_or_404(part):
    if part not in init.INIT_CONF:
        abort(404)
    cls = init.INIT_CONF[part].get('log_model', None)
    if not (cls and issubclass(cls, BaseLog)):
        abort(404)
    return cls


@app.route('/log/<part>')
def log_list(part):
    cls = _get_cls_or_404(part)
    args = request.args
    page = int(args.get('page', 1))
    ip = args.get('ip', 'no')
    level = int(args.get('level', 0))
    task_id = args.get('task_id')
    url = args.get('url')
    q_params = {}
    if level > 0:
        q_params.update({'level__gte': level})
    if task_id:
        q_params.update({'task_id': task_id})
    if url:
        q_params.update({'url': url})
    # limit distinct to save time
    ips = cls.objects(**q_params).only('ip').order_by('-time', '-msecs').limit(1000)
    ips = set([_r['ip'] for _r in ips])
    if len(ips) == 0:
        abort(404)
    if ip != 'no':
        q_params.update({'ip': ip})
    context = {
        'part': part,
        'levels': LEVELS,
        'level': level,
        'ips': ips,
        'ip': ip,
        'url': url,
        'task_id': task_id,
        'logs': cls.objects(**q_params).order_by('-time', '-msecs').paginate(page=page, per_page=50)
    }
    return render_template('log.html', **context)


@app.route('/log/<part>/<log_id>')
@acquire_xhr
def log_get(part, log_id):
    cls = _get_cls_or_404(part)
    log = cls.objects.get_or_404(id=log_id)
    log = log.to_mongo().to_dict()
    log.pop('_id', None)
    log.pop('msecs', None)
    task_id = log.pop('task_id', None)
    if task_id:
        log['task_id'] = str(task_id)
    return jsonify(log)


@app.route('/task/doc')
def task_doc():
    args = request.args
    page = int(args.get('page', 1))
    task_id = args.get('task_id')
    q_params = {}
    task = None
    if task_id:
        task = Task.objects.get_or_404(id=task_id)
        q_params = {'task': task}
    context = {
        'statuses': ITEM_STATUS,
        'task': task,
        'task_id': task_id,
        'docs': Item.objects(**q_params).order_by('-save_time').paginate(page=page, per_page=50)
    }
    return render_template('task/doc.html', **context)


@app.route('/task/doc/<doc_id>')
@acquire_xhr
def doc_get(doc_id):
    doc = Item.objects.get_or_404(id=doc_id)
    task_name = doc.task.name
    doc = doc.to_mongo().to_dict()
    doc.pop('_id', None)
    doc['task'] = task_name
    doc['status'] = ITEM_STATUS.get(doc['status'], '')
    return jsonify(doc)
