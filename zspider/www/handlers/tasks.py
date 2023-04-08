# coding=utf-8
import json
import logging
from datetime import datetime
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from flask import abort
from flask import flash
from flask import get_flashed_messages
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.exceptions import NotFound

from . import app
from ..tools import get_internal_msg
from ..tools import validate_forms
from ..utils import acquire_admin
from ..utils import is_xhr
from ..utils import test_crawler
from zspider.confs.dispatcher_conf import MANAGE_KEY
from zspider.confs.dispatcher_conf import MANAGE_PORT
from zspider.confs.dispatcher_conf import STATE_DISPATCH
from zspider.models import PubSubscribe
from zspider.models import PubSubscribeForm
from zspider.utils.models import ArticleField
from zspider.utils.models import ArticleFieldForm
from zspider.utils.models import PARSER_CONF_FORM_REF
from zspider.utils.models import Task
from zspider.utils.models import TaskForm
from zspider.utils.models import User

__author__ = "zephor"

logger = logging.getLogger(__name__)


@app.route("/task/list")
def task_list():
    field = request.args.get("field", "")
    q = request.args.get("q", "")
    context = {"flashes": get_flashed_messages(with_categories=True), "prev_kwargs": {}}
    q_params = {}
    if q and field:
        if field == "task_name":
            q_params = {"name__contains": q}
        context["prev_kwargs"] = {"field": field, "q": q}
    page = int(request.args.get("page", 1))
    context.update(
        {
            "count": Task.objects(**q_params).count(),
            "running_count": Task.objects(is_active=True, **q_params).count(),
            "tasks": Task.objects(**q_params).paginate(page=page, per_page=32),
        }
    )
    if context["count"] == 0:
        context["prev_kwargs"] = {}
    return render_template("task/list.html", **context)


@app.route("/task/add", methods=["GET", "POST"])
@acquire_admin
def task_add():
    task_form = TaskForm(request.form)

    # conf part #
    parser = task_form.parser.data
    if parser not in PARSER_CONF_FORM_REF:
        parser = task_form.parser.choices[0][0]
    if is_xhr():
        parser = request.args.get("parser")

    conf_form = PARSER_CONF_FORM_REF.get(parser)
    if conf_form is None:
        abort(404)

    conf_form = conf_form(request.form, meta={"csrf": False})

    if is_xhr():
        return render_template("task/form_conf.html", conf_form=conf_form)
    # end part #

    # article fields #
    fields_len = int(request.form.get("fields_len", 0))
    article_field_forms = []
    if fields_len == 0:
        for _f in ArticleField.base_names():
            fields_len += 1
            article_field_forms.append(ArticleFieldForm(name=_f, meta={"csrf": False}))
    else:
        _parse_field_forms(article_field_forms, fields_len)
    # article fields #

    if (
        request.method == "POST"
        and validate_forms([task_form, conf_form] + article_field_forms)
        and _verify_fields(article_field_forms)
    ):

        user = User.objects.get(username=session["user"])

        task = task_form.save(commit=False)
        task.creator = user
        task.mender = user
        task.is_active = bool(request.args.get("active", type=int))
        task.save()

        conf = conf_form.save(commit=False)
        conf.id = task.id
        conf.save()

        for article_field_form in article_field_forms:
            article_field = article_field_form.save(commit=False)
            article_field.task = task
            article_field.save()

        flash(u"任务：%s 添加成功" % task.name)

        _reload_task(task)

        return redirect(url_for("task_list"))

    context = {
        "form": task_form,
        "conf_form": conf_form,
        "article_field_forms": article_field_forms,
        "is_add": True,
        "fields_len": fields_len,
        "base_fields_len": len(ArticleField.base_names()),
    }

    return render_template("task/add.html", **context)


@app.route("/task/edit/<task_id>", methods=["GET", "POST"])
@acquire_admin
def task_edit(task_id):
    task = Task.objects.get_or_404(id=task_id)

    task_form = TaskForm(request.form, obj=task)

    # conf part #
    if is_xhr():
        parser = request.args.get("parser")
    else:
        parser = task_form.parser.data

    conf_form = PARSER_CONF_FORM_REF.get(parser)
    if conf_form is None:
        abort(404)
    try:
        conf = conf_form.model_class.objects.get_or_404(id=task_id)
    except NotFound:
        conf = None

    conf_form = conf_form(request.form, obj=conf, meta={"csrf": False})

    if is_xhr():
        return render_template("task/form_conf.html", conf_form=conf_form)
    # end part #

    # article fields #
    fields_len = int(request.form.get("fields_len", 0))
    article_field_forms = []
    if fields_len == 0:
        article_fields = ArticleField.objects(task=task).order_by("id")
        if not len(article_fields):
            abort(404)
        else:
            for article_field in article_fields:
                fields_len += 1
                article_field_forms.append(
                    ArticleFieldForm(obj=article_field, meta={"csrf": False})
                )
    else:
        _parse_field_forms(article_field_forms, fields_len)
    # article fields #

    if (
        request.method == "POST"
        and validate_forms([task_form, conf_form] + article_field_forms)
        and _verify_fields(article_field_forms)
    ):
        return _do_edit_task(
            task, parser, conf, task_form, conf_form, article_field_forms
        )

    context = {
        "is_active": task.is_active,
        "form": task_form,
        "conf_form": conf_form,
        "article_field_forms": article_field_forms,
        "is_add": False,
        "fields_len": fields_len,
        "base_fields_len": len(ArticleField.base_names()),
    }

    return render_template("task/add.html", **context)


def _do_edit_task(task, parser, conf, task_form, conf_form, article_field_forms):
    user = User.objects.get(username=session["user"])
    _parser = task.parser
    task_form.populate_obj(task)
    if _parser != parser:
        PARSER_CONF_FORM_REF.get(_parser).model_class.objects(id=task.id).delete()
    task.mtime = datetime.now()
    task.mender = user
    if request.args.get("active", type=int):
        task.is_active = True
    task.save()
    if conf is None:
        conf = conf_form.save(commit=False)
        conf.id = task.id
    else:
        conf_form.populate_obj(conf)
    conf.save()
    article_fields = list(ArticleField.objects(task=task).order_by("id"))

    def pop_by_name(name):
        for _i, _af in enumerate(article_fields):
            if _af.name == name:
                return article_fields.pop(_i)
        return article_fields.pop(0)

    _len = len(article_fields)
    for i, article_field_form in enumerate(article_field_forms):
        if i >= _len:
            article_field = article_field_form.save(commit=False)
            article_field.task = task
        else:
            article_field = pop_by_name(article_field_form.name.data)
            article_field_form.populate_obj(article_field)
        article_field.save()
    for af in article_fields:
        # delete the rest
        af.delete()
    flash(u"任务：%s 更新成功" % task.name)
    _reload_task(task)
    return redirect(url_for("task_list"))


@app.route("/task/test/<target>", methods=["GET", "POST"])
def task_test(target):
    if target not in ("index", "article"):
        abort(404)
    task_form = TaskForm(request.form, meta={"csrf": False})
    # conf part #
    parser = task_form.parser.data
    if parser not in PARSER_CONF_FORM_REF:
        parser = task_form.parser.choices[0][0]

    conf_form = PARSER_CONF_FORM_REF.get(parser)
    if conf_form is None:
        abort(404)

    conf_form = conf_form(request.form, meta={"csrf": False})
    # end part #

    # article fields #
    article_field_forms = []
    if target == "article":
        fields_len = int(request.form.get("fields_len", 0))
        _parse_field_forms(article_field_forms, fields_len)
    # article fields #
    done = False
    res = []
    if (
        request.method == "POST"
        and validate_forms([task_form, conf_form])
        and validate_forms(article_field_forms)
        and _verify_fields(article_field_forms)
    ):
        task = task_form.save(commit=False)
        conf = conf_form.save(commit=False)
        afs = []
        if target == "article":
            for article_field_form in article_field_forms:
                afs.append(article_field_form.save(commit=False))
        from twisted.internet import reactor

        test_crawler.settings.set("COOKIES_ENABLED", task.is_login)
        reactor.callFromThread(
            test_crawler.task_q.put,
            dict(
                spider_name=task.spider,
                parser=task.parser,
                task_id="test_%s" % target,
                task_name=task.name,
                task_conf=conf,
                article_fields=afs,
            ),
        )
        res = test_crawler.res_q.get()
        done = True

    context = {
        "form": task_form,
        "conf_form": conf_form,
        "article_field_forms": article_field_forms,
        "done": done,
        "target": target,
        "res": res,
    }

    return render_template("task/test.html", **context)


def _parse_field_forms(article_field_forms, fields_len):
    for i in range(0, fields_len):
        form_data = ImmutableMultiDict(
            dict(
                name=request.form.get("name_%s" % i),
                xpath=request.form.get("xpath_%s" % i),
                re=request.form.get("re_%s" % i),
                specify=request.form.get("specify_%s" % i),
            )
        )
        article_field_forms.append(ArticleFieldForm(form_data, meta={"csrf": False}))


@app.route("/task/subscribe", methods=["GET", "POST"])
@acquire_admin
def task_subscribe():
    task_id = request.args.get("task_id", None)
    task = Task.objects.get_or_404(id=task_id)
    try:
        pub_sbs = PubSubscribe.objects.get_or_404(id=task_id)
    except NotFound:
        pub_sbs = None
    sub_form = PubSubscribeForm(request.form, obj=pub_sbs)
    if request.method == "POST" and sub_form.validate():
        if pub_sbs is None:
            pub_sbs = sub_form.save(commit=False)
            pub_sbs.id = task_id
        else:
            sub_form.populate_obj(pub_sbs)
        pub_sbs.save()
        flash(u"任务：%s 订阅%s成功" % (task.name, (u"更新", u"添加")[pub_sbs is None]))
        return redirect(url_for("task_list"))
    return render_template("task/subscribe.html", task=task, form=sub_form)


@app.route("/task/q/subscribe/<task_id>")
def task_q_subscribe(task_id):
    res = {"status": True, "data": ""}
    try:
        sub = PubSubscribe.objects.get_or_404(id=task_id)
    except NotFound:
        res["status"] = False
        res["data"] = u"没找到订阅信息"
    else:
        res["data"] = {"cids": sub.cids, "model_id": sub.model_id}
    return jsonify(res)


@app.route("/task/d/subscribe/<task_id>", methods=["POST"])
def task_d_subscribe(task_id):
    res = {"status": True, "data": ""}
    try:
        PubSubscribe.objects(id=task_id).delete()
    except Exception as e:
        res["status"] = False
        res["data"] = str(e)
    return jsonify(res)


@app.route("/task/toggle/<task_id>", methods=["POST"])
@acquire_admin
def task_toggle(task_id):
    res = {"status": False, "data": ""}

    try:
        task = Task.objects.get_or_404(id=task_id)
    except NotFound:
        res["data"] = u"任务：%s 没找到" % task_id
        return jsonify(res)

    try:
        ip = _get_dispatcher()
    except Exception as e:
        res["data"] = u"获取dispatcher地址失败，请联系管理员并保留如下原因：%s" % e
        return jsonify(res)

    action = "/%s/{0:s}/{1:s}".format(task_id, MANAGE_KEY)

    if task.is_active:
        task.is_active = False
        action %= "pause"
    elif task.cron:
        task.is_active = True
        action %= "load"
    else:
        res["data"] = u"必须先设置好任务定时才能启动任务"
        return jsonify(res)

    task.save()
    if ip:
        try:
            d_res = urlopen(
                "http://{0:s}:{1:d}".format(ip, MANAGE_PORT) + quote(action)
            ).read()
        except URLError:
            res["data"] = u"连接到dispatcher %s失败" % ip
        else:
            d_res = json.loads(d_res)
            res["data"] = d_res["data"]
    else:
        res["data"] = u"找不到dispatcher"
    res["status"] = True
    return jsonify(res)


def _verify_fields(article_field_forms):
    base = list(ArticleField.base_names())
    for form in article_field_forms:
        try:
            base.pop(base.index(form.name.data))
        except ValueError:
            form.may_error = True
        if not (form.xpath.data or form.re.data):
            form.error = u"字段解析方法至少设置一个"
            return False
    if base:
        for form in article_field_forms:
            if hasattr(form, "may_error") and form.may_error:
                form.error = u"缺少基本字段：%s" % base
                return False
    return True


def _get_dispatcher():
    dispatcher = None
    _t = 0
    msg = get_internal_msg()
    for ip, v in msg.items():
        if v["status"] == STATE_DISPATCH:
            if v["refresh"] > _t:
                _t = v["refresh"]
                dispatcher = ip
    return dispatcher


def _reload_task(task):
    if task.is_active:
        action = "/load/{0:s}/{1:s}".format(str(task.id), MANAGE_KEY)
        try:
            ip = _get_dispatcher()
            d_res = urlopen(
                "http://{0:s}:{1:d}".format(ip, MANAGE_PORT) + quote(action)
            ).read()
        except Exception:
            flash(u"调度更新失败", category="warning")
        else:
            d_res = json.loads(d_res)
            flash(d_res["data"])
