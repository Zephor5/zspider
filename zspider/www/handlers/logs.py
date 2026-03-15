# coding=utf-8
from flask import jsonify
from flask import render_template
from flask import request

from . import app
from zspider.services.monitor_service import build_doc_list_context
from zspider.services.monitor_service import build_log_list_context
from zspider.services.monitor_service import build_run_list_context
from zspider.services.monitor_service import serialize_doc
from zspider.services.monitor_service import serialize_log
from zspider.services.monitor_service import serialize_task_run
from zspider.www.utils import acquire_xhr

__author__ = "zephor"


@app.route("/log/<part>")
def log_list(part):
    args = request.args
    context = build_log_list_context(
        part=part,
        page=int(args.get("page", 1)),
        ip=args.get("ip", "no"),
        level=int(args.get("level", 0)),
        task_id=args.get("task_id"),
        url=args.get("url"),
    )
    return render_template("log.html", **context)


@app.route("/log/<part>/<log_id>")
@acquire_xhr
def log_get(part, log_id):
    return jsonify(serialize_log(part, log_id))


@app.route("/task/doc")
def task_doc():
    args = request.args
    context = build_doc_list_context(
        page=int(args.get("page", 1)),
        task_id=args.get("task_id"),
    )
    return render_template("task/doc.html", **context)


@app.route("/task/doc/<doc_id>")
@acquire_xhr
def doc_get(doc_id):
    return jsonify(serialize_doc(doc_id))


@app.route("/task/run")
def task_run_list():
    args = request.args
    context = build_run_list_context(
        page=int(args.get("page", 1)),
        task_id=args.get("task_id"),
        status=args.get("status", ""),
        error_code=args.get("error_code", ""),
    )
    return render_template("task/run.html", **context)


@app.route("/task/run/<run_id>")
@acquire_xhr
def task_run_get(run_id):
    return jsonify(serialize_task_run(run_id))
