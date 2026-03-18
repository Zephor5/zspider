# coding=utf-8
from datetime import datetime
from urllib.parse import parse_qsl
from urllib.parse import urlencode
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

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
from zspider.confs.dispatcher_conf import STATE_DISPATCH
from zspider.models import PubSubscribeForm
from zspider.services.explorer_ai import generate_article_fields
from zspider.services.explorer_ai import generate_index_rule
from zspider.services.page_explorer import build_index_test_rows
from zspider.services.page_explorer import explore_article_page
from zspider.services.page_explorer import explore_index_page
from zspider.services.task_service import build_task_list_context
from zspider.services.task_service import delete_task_subscription
from zspider.services.task_service import get_task_or_404
from zspider.services.task_service import get_task_subscription
from zspider.services.task_service import reload_task
from zspider.services.task_service import serialize_subscription
from zspider.services.task_service import toggle_task as toggle_task_service
from zspider.utils.models import ArticleField
from zspider.utils.models import ArticleFieldForm
from zspider.utils.models import PARSER_CONF_FORM_REF
from zspider.utils.models import TaskForm
from zspider.utils.models import User

__author__ = "zephor"


@app.route("/task/list")
def task_list():
    field = request.args.get("field", "")
    q = request.args.get("q", "")
    context = {"flashes": get_flashed_messages(with_categories=True), "prev_kwargs": {}}
    context.update(build_task_list_context(field, q, int(request.args.get("page", 1))))
    return render_template("task/list.html", **context)


@app.route("/task/add", methods=["GET", "POST"])
@acquire_admin
def task_add():
    task_form = TaskForm(request.form)

    # conf part #
    parser = task_form.parser.data
    if not parser and "IndexParser" in PARSER_CONF_FORM_REF:
        parser = "IndexParser"
        task_form.parser.data = parser
    if parser not in PARSER_CONF_FORM_REF:
        parser = task_form.parser.choices[0][0]
        task_form.parser.data = parser
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
        and not _is_return_edit_post()
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

        flash("任务：%s 添加成功" % task.name)

        _reload_task(task)

        return redirect(url_for("task_list"))

    context = {
        "form": task_form,
        "conf_form": conf_form,
        "article_field_forms": article_field_forms,
        "is_add": True,
        "task": None,
        "fields_len": fields_len,
        "base_fields_len": len(ArticleField.base_names()),
        "explore_url": _resolve_explore_url(conf_form),
        "explore_result": None,
        "explore_error": "",
        "article_explore_url": "",
        "article_explore_result": None,
        "article_explore_error": "",
    }
    context.update(_build_task_editor_state(task_form, conf_form, article_field_forms))

    return render_template("task/add.html", **context)


@app.route("/task/edit/<task_id>", methods=["GET", "POST"])
@acquire_admin
def task_edit(task_id):
    task = get_task_or_404(task_id)

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
        and not _is_return_edit_post()
        and validate_forms([task_form, conf_form] + article_field_forms)
        and _verify_fields(article_field_forms)
    ):
        return _do_edit_task(
            task, parser, conf, task_form, conf_form, article_field_forms
        )

    context = {
        "task": task,
        "is_active": task.is_active,
        "form": task_form,
        "conf_form": conf_form,
        "article_field_forms": article_field_forms,
        "is_add": False,
        "fields_len": fields_len,
        "base_fields_len": len(ArticleField.base_names()),
        "explore_url": _resolve_explore_url(conf_form),
        "explore_result": None,
        "explore_error": "",
        "article_explore_url": "",
        "article_explore_result": None,
        "article_explore_error": "",
    }
    context.update(_build_task_editor_state(task_form, conf_form, article_field_forms))

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
    flash("任务：%s 更新成功" % task.name)
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
    index_result_rows = []
    article_result_rows = []
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
        if target == "index":
            index_result_rows = build_index_test_rows(
                getattr(conf, "front_url", ""),
                getattr(conf, "url_xpath", ""),
                [_extract_result_url(item) for item in res or []],
            )
        else:
            article_result_rows = _build_article_test_rows(res, article_field_forms)

    context = {
        "form": task_form,
        "conf_form": conf_form,
        "article_field_forms": article_field_forms,
        "done": done,
        "target": target,
        "res": res,
        "index_result_rows": index_result_rows,
        "article_result_rows": article_result_rows,
        "submitted_items": list(request.form.items(multi=True)),
        "return_path": _resolve_return_path(),
        "save_draft_url": _with_active(_resolve_save_path(), 0),
        "save_start_url": _with_active(_resolve_save_path(), 1),
        "test_index_url": url_for("task_test", target="index"),
        "test_article_url": url_for("task_test", target="article"),
        "modal_mode": is_xhr(),
    }
    if is_xhr():
        return render_template("task/test_result_panel.html", **context)
    return render_template("task/test.html", **context)


@app.route("/task/explore/index", methods=["POST"])
@acquire_admin
def task_explore_index():
    front_url = request.form.get("front_url", "").strip()
    explore_result = None
    explore_error = ""
    if not front_url:
        explore_error = "请先输入入口页地址。"
    else:
        try:
            explore_result = explore_index_page(front_url)
        except Exception as exc:
            explore_error = "入口页探索失败：%s" % exc
    return render_template(
        "task/explore_panel.html",
        explore_url=front_url,
        explore_result=explore_result,
        explore_error=explore_error,
    )


@app.route("/task/explore/article", methods=["POST"])
@acquire_admin
def task_explore_article():
    article_url = request.form.get("article_url", "").strip()
    article_explore_result = None
    article_explore_error = ""
    if not article_url:
        article_explore_error = "请先输入文章地址。"
    else:
        try:
            article_explore_result = explore_article_page(article_url)
        except Exception as exc:
            article_explore_error = "文章探索失败：%s" % exc
    return render_template(
        "task/explore_article_panel.html",
        article_explore_url=article_url,
        article_explore_result=article_explore_result,
        article_explore_error=article_explore_error,
    )


@app.route("/task/explore/index/generate", methods=["POST"])
@acquire_admin
def task_explore_index_generate():
    front_url = request.form.get("front_url", "").strip()
    selected_urls = request.form.getlist("selected_urls[]") or request.form.getlist(
        "selected_urls"
    )
    excluded_urls = request.form.getlist("excluded_urls[]") or request.form.getlist(
        "excluded_urls"
    )
    if not front_url:
        return jsonify({"status": False, "message": "请先输入入口页地址。"})
    try:
        result = generate_index_rule(front_url, selected_urls, excluded_urls)
    except Exception as exc:
        if "未配置页面探索模型" in str(exc):
            return jsonify(
                {
                    "status": False,
                    "message": (
                        "生成索引规则失败：未配置页面探索模型。"
                        "请先配置 ZSPIDER_LLM_API_KEY 和 "
                        "ZSPIDER_LLM_MODEL。"
                    ),
                }
            )
        return jsonify({"status": False, "message": "生成索引规则失败：%s" % exc})
    return jsonify({"status": True, "data": result})


@app.route("/task/explore/article/generate", methods=["POST"])
@acquire_admin
def task_explore_article_generate():
    article_url = request.form.get("article_url", "").strip()
    field_points = {}
    for field in ("title", "content", "src_time", "source"):
        field_points[field] = {
            "type": request.form.get("%s_type" % field, ""),
            "text": request.form.get("%s_text" % field, ""),
            "node_xpath": request.form.get("%s_node_xpath" % field, ""),
            "text_xpath": request.form.get("%s_text_xpath" % field, ""),
            "content_xpath": request.form.get("%s_content_xpath" % field, ""),
            "value_xpath": request.form.get("%s_value_xpath" % field, ""),
        }
    if not article_url:
        return jsonify({"status": False, "message": "请先输入文章地址。"})
    try:
        result = generate_article_fields(article_url, field_points)
    except Exception as exc:
        return jsonify({"status": False, "message": "生成文章字段失败：%s" % exc})
    return jsonify({"status": True, "data": result})


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


def _build_task_editor_state(task_form, conf_form, article_field_forms):
    spider_label_map = {
        "news": "直接抓取",
        "browser": "浏览器渲染",
        "wechat": "微信抓取",
    }
    spider = getattr(task_form.spider, "data", "") or ""
    fetch_summary = "等待左侧入口页探索结果"
    fetch_reason = "系统会在你探索入口页后，自动更新抓取方式建议并同步到抓取程序字段。"
    if spider:
        fetch_summary = "%s，建议抓取程序：%s" % (
            spider_label_map.get(spider, spider),
            spider,
        )
        fetch_reason = "当前表单已选择抓取程序，重新探索入口页后会按最新页面结果更新建议。"

    stage = _infer_editor_stage(conf_form, article_field_forms)
    return {
        "initial_fetch_mode_summary": fetch_summary,
        "initial_fetch_mode_reason": fetch_reason,
        "initial_task_stage": stage,
    }


def _infer_editor_stage(conf_form, article_field_forms):
    has_index_rule = bool(
        (getattr(getattr(conf_form, "url_xpath", None), "data", "") or "").strip()
        or (getattr(getattr(conf_form, "url_re", None), "data", "") or "").strip()
    )
    core_fields = {"title": False, "content": False}
    for article_field_form in article_field_forms:
        name = (getattr(article_field_form.name, "data", "") or "").strip()
        if name not in core_fields:
            continue
        has_value = bool(
            (getattr(article_field_form.xpath, "data", "") or "").strip()
            or (getattr(article_field_form.specify, "data", "") or "").strip()
        )
        if has_value:
            core_fields[name] = True
    if core_fields["title"] and core_fields["content"]:
        return "save"
    if has_index_rule:
        return "article"
    return "index"


def _extract_result_url(item):
    if isinstance(item, dict):
        return item.get("url")
    return getattr(item, "url", None)


def _build_article_test_rows(res, article_field_forms):
    values = {}
    if res:
        values = res[0]
    rows = []
    label_map = {
        "url": "文章地址",
        "title": "标题",
        "content": "正文",
        "src_time": "时间",
        "source": "来源",
    }
    conf_map = {}
    for article_field_form in article_field_forms:
        field_name = (getattr(article_field_form.name, "data", "") or "").strip()
        conf_map[field_name] = {
            "xpath": (getattr(article_field_form.xpath, "data", "") or "").strip(),
            "re": (getattr(article_field_form.re, "data", "") or "").strip(),
            "specify": (getattr(article_field_form.specify, "data", "") or "").strip(),
        }
    for field in ("url", "title", "content", "src_time", "source"):
        value = ""
        if isinstance(values, dict):
            value = (values.get(field) or "").strip()
        config = conf_map.get(field, {})
        rows.append(
            {
                "field": field,
                "label": label_map[field],
                "value": value,
                "missing": not bool(value),
                "config_text": _article_field_config_text(config),
            }
        )
    return rows


def _article_field_config_text(config):
    if not config:
        return ""
    if config.get("xpath"):
        return "当前 XPath：%s" % config["xpath"]
    if config.get("re"):
        return "当前正则：%s" % config["re"]
    if config.get("specify"):
        return "当前指定值：%s" % config["specify"]
    return "当前还没有配置值。"


def _resolve_explore_url(conf_form):
    field = getattr(conf_form, "front_url", None)
    if field is None:
        return ""
    return field.data or ""


def _is_return_edit_post():
    return request.form.get("_return_edit") == "1"


def _resolve_return_path():
    return request.form.get("return_path") or request.referrer or url_for("task_add")


def _resolve_save_path():
    return request.form.get("save_path") or _resolve_return_path()


def _with_active(url, active):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["active"] = str(active)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


@app.route("/task/subscribe", methods=["GET", "POST"])
@acquire_admin
def task_subscribe():
    task_id = request.args.get("task_id", None)
    task = get_task_or_404(task_id)
    pub_sbs = get_task_subscription(task_id)
    sub_form = PubSubscribeForm(request.form, obj=pub_sbs)
    if request.method == "POST" and sub_form.validate():
        if pub_sbs is None:
            pub_sbs = sub_form.save(commit=False)
            pub_sbs.id = task_id
        else:
            sub_form.populate_obj(pub_sbs)
        pub_sbs.save()
        flash("任务：%s 订阅%s成功" % (task.name, ("更新", "添加")[pub_sbs is None]))
        return redirect(url_for("task_list"))
    return render_template("task/subscribe.html", task=task, form=sub_form)


@app.route("/task/q/subscribe/<task_id>")
def task_q_subscribe(task_id):
    res = {"status": True, "data": ""}
    sub = get_task_subscription(task_id)
    if sub is None:
        res["status"] = False
        res["data"] = "没找到订阅信息"
    else:
        res["data"] = serialize_subscription(sub)
    return jsonify(res)


@app.route("/task/d/subscribe/<task_id>", methods=["POST"])
def task_d_subscribe(task_id):
    res = {"status": True, "data": ""}
    try:
        delete_task_subscription(task_id)
    except Exception as e:
        res["status"] = False
        res["data"] = str(e)
    return jsonify(res)


@app.route("/task/toggle/<task_id>", methods=["POST"])
@acquire_admin
def task_toggle(task_id):
    res = {"status": False, "data": ""}

    try:
        ip = _get_dispatcher()
    except Exception as e:
        res["data"] = "获取dispatcher地址失败，请联系管理员并保留如下原因：%s" % e
        return jsonify(res)
    try:
        res["status"], res["data"] = toggle_task_service(task_id, ip)
    except NotFound:
        res["data"] = "任务：%s 没找到" % task_id
    return jsonify(res)


def _verify_fields(article_field_forms):
    base = list(ArticleField.base_names())
    for form in article_field_forms:
        try:
            base.pop(base.index(form.name.data))
        except ValueError:
            form.may_error = True
        if not (form.xpath.data or form.re.data or form.specify.data):
            form.error = "字段解析方法至少设置一个"
            return False
    if base:
        for form in article_field_forms:
            if hasattr(form, "may_error") and form.may_error:
                form.error = "缺少基本字段：%s" % base
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
        try:
            ip = _get_dispatcher()
            flash(reload_task(task, ip))
        except Exception:
            flash("调度更新失败", category="warning")
