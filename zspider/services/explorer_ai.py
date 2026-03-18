# coding=utf-8
import json
import re

from lxml import html

from zspider import settings
from zspider.services import page_explorer

__author__ = "zephor"


FIELD_NAMES = ("title", "content", "src_time", "source")
DEFAULT_LLM_TIMEOUT = settings.LLM_TIMEOUT


def generate_index_rule(
    url, selected_urls, excluded_urls=None, timeout=DEFAULT_LLM_TIMEOUT
):
    url = (url or "").strip()
    if not url:
        raise ValueError("请先输入入口页地址。")

    selected_urls = _normalize_urls(url, selected_urls)
    excluded_urls = _normalize_urls(url, excluded_urls or [])
    if len(selected_urls) < 2:
        raise ValueError("请至少标注 2 个目标链接。")
    _ensure_llm_ready()

    page_variants = page_explorer._load_page_variants(url, timeout=timeout)
    final_url = page_variants["final_url"]
    static_doc = page_variants["static_doc"]
    static_candidates = page_explorer._extract_index_candidates(static_doc, final_url)
    fetch_mode = page_explorer._detect_fetch_mode(
        final_url,
        static_doc,
        static_candidates,
        timeout=timeout,
        browser_doc=page_variants["browser_doc"],
    )
    doc = page_explorer._select_effective_doc(fetch_mode, page_variants)
    rendered_html = html.tostring(doc, encoding="unicode", method="html")

    payload = {
        "page_url": final_url,
        "selected_urls": selected_urls,
        "excluded_urls": excluded_urls,
        "rendered_html": rendered_html,
    }
    result = _call_llm(
        payload,
        _index_system_prompt(),
        _index_tool_schema(),
        timeout=timeout,
    )
    rule_type = (result.get("rule_type") or "").strip().lower()
    value = (result.get("value") or "").strip()
    if rule_type not in ("xpath", "re") or not value:
        raise RuntimeError("模型没有返回可用的 index 规则。")
    parser_rule = _normalize_index_rule(rule_type, value)
    preview_rule = _preview_rule_for_index(parser_rule)
    return {
        "final_url": final_url,
        "fetch_mode": fetch_mode,
        "rule_type": parser_rule["rule_type"],
        "value": parser_rule["value"],
        "parser_rule": parser_rule,
        "preview_rule": preview_rule,
    }


def generate_article_fields(url, field_points, timeout=DEFAULT_LLM_TIMEOUT):
    url = (url or "").strip()
    if not url:
        raise ValueError("请先输入文章地址。")
    _ensure_llm_ready()

    normalized_points = _normalize_field_points(field_points or {})
    if not normalized_points:
        raise ValueError("请先点选至少一个字段样本。")

    cached_context = page_explorer.get_cached_article_context(url)
    if cached_context:
        final_url = cached_context["final_url"]
        rendered_html = cached_context["rendered_html"]
    else:
        page_variants = page_explorer._load_page_variants(url, timeout=timeout)
        final_url = page_variants["final_url"]
        static_doc = page_variants["static_doc"]
        fetch_mode = page_explorer._detect_fetch_mode(
            final_url,
            static_doc,
            [],
            timeout=timeout,
            browser_doc=page_variants["browser_doc"],
        )
        doc = page_explorer._select_effective_doc(fetch_mode, page_variants)
        rendered_html = html.tostring(doc, encoding="unicode", method="html")

    payload = {
        "page_url": final_url,
        "field_points": normalized_points,
        "rendered_html": rendered_html,
    }
    result = _call_llm(
        payload,
        _article_system_prompt(),
        _article_tool_schema(),
        timeout=timeout,
    )
    normalized = _normalize_article_result(result)
    merged = _merge_article_result_with_points(normalized, normalized_points)
    validation = _validate_article_fields(rendered_html, merged)
    if not validation["fields"]:
        raise RuntimeError("模型没有返回可用的文章字段。")
    validation["message"] = _article_result_message(
        validation["written_fields"], validation["missing_fields"]
    )
    return validation


def _ensure_llm_ready():
    if not settings.LLM_API_KEY or not settings.LLM_MODEL:
        raise RuntimeError("未配置页面探索模型。")


def _normalize_urls(base_url, urls):
    normalized = [
        page_explorer._normalize_href(item, base_url) for item in (urls or [])
    ]
    normalized = [item for item in normalized if item]
    return page_explorer._dedupe_preserve_order(normalized)


def _normalize_field_points(field_points):
    normalized = {}
    for field in FIELD_NAMES:
        point = field_points.get(field)
        if not isinstance(point, dict):
            continue
        field_type = (point.get("type") or "").strip().lower()
        text = (point.get("text") or "").strip()
        node_xpath = (point.get("node_xpath") or "").strip()
        text_xpath = (point.get("text_xpath") or "").strip()
        content_xpath = (point.get("content_xpath") or "").strip()
        value_xpath = (point.get("value_xpath") or "").strip()
        payload = {
            "type": field_type,
            "text": text,
            "node_xpath": node_xpath,
            "text_xpath": text_xpath,
            "content_xpath": content_xpath,
            "value_xpath": value_xpath,
        }
        if any(payload.values()):
            normalized[field] = payload
    return normalized


def _normalize_article_result(result):
    normalized = {}
    for field in FIELD_NAMES:
        item = result.get(field)
        if not isinstance(item, dict):
            continue
        mode = (item.get("mode") or "").strip().lower()
        value = (item.get("value") or "").strip()
        if not value:
            continue
        if field in ("title", "content") and mode != "xpath":
            continue
        if field == "src_time" and mode not in ("xpath",):
            continue
        if field == "source" and mode not in ("xpath", "specify"):
            continue
        normalized[field] = {"mode": mode, "value": value}
    if not normalized:
        raise RuntimeError("模型没有返回可用的文章字段。")
    return normalized


def _normalize_index_rule(rule_type, value):
    if rule_type == "xpath":
        normalized_xpath = _normalize_index_xpath_rule(value)
        if not normalized_xpath:
            raise RuntimeError("模型没有返回可用的 index XPath。")
        return {"rule_type": "xpath", "value": normalized_xpath}
    return {"rule_type": "re", "value": value}


def _normalize_index_xpath_rule(xpath):
    xpath = (xpath or "").strip()
    if not xpath:
        return ""
    if xpath.endswith("/@href"):
        return xpath
    if xpath.endswith("//a[@href]"):
        return "%s/@href" % xpath
    if xpath.endswith("//a[@href][1]"):
        return "%s/@href" % xpath
    if xpath.endswith("//a"):
        return "%s/@href" % xpath
    if re.search(r"//a(\[[^\]]+\])?$", xpath):
        return "%s/@href" % xpath
    if "/a[@href]" in xpath and not xpath.endswith("text()"):
        return "%s/@href" % xpath
    return xpath


def _preview_rule_for_index(parser_rule):
    rule_type = parser_rule["rule_type"]
    value = parser_rule["value"]
    if rule_type != "xpath":
        return {"rule_type": rule_type, "value": value}
    preview_value = value[:-6] if value.endswith("/@href") else value
    return {"rule_type": "xpath", "value": preview_value}


def _merge_article_result_with_points(result, field_points):
    merged = dict(result)
    for field in FIELD_NAMES:
        if merged.get(field):
            continue
        fallback = _field_point_fallback(field, field_points.get(field) or {})
        if fallback:
            merged[field] = fallback
    return merged


def _field_point_fallback(field, point):
    if not point:
        return None
    text_xpath = (point.get("text_xpath") or "").strip()
    content_xpath = (point.get("content_xpath") or "").strip()
    value_xpath = (point.get("value_xpath") or "").strip()
    text = (point.get("text") or "").strip()
    if field == "title" and text_xpath:
        return {"mode": "xpath", "value": text_xpath}
    if field == "content" and content_xpath:
        return {"mode": "xpath", "value": content_xpath}
    if field == "src_time":
        if value_xpath:
            return {"mode": "xpath", "value": value_xpath}
        if text_xpath:
            return {"mode": "xpath", "value": text_xpath}
    if field == "source":
        if value_xpath:
            return {"mode": "xpath", "value": value_xpath}
        if text_xpath:
            return {"mode": "xpath", "value": text_xpath}
        if text:
            return {"mode": "specify", "value": text}
    return None


def _validate_article_fields(rendered_html, fields):
    doc = html.fromstring(rendered_html)
    written_fields = []
    missing_fields = []
    normalized = {}
    for field in FIELD_NAMES:
        item = fields.get(field)
        if not isinstance(item, dict):
            missing_fields.append(field)
            continue
        mode = (item.get("mode") or "").strip().lower()
        value = (item.get("value") or "").strip()
        if not value:
            missing_fields.append(field)
            continue
        if mode == "specify":
            extracted = value
        else:
            extracted = _extract_xpath_value(doc, value)
        if not _field_value_is_valid(field, extracted):
            missing_fields.append(field)
            continue
        normalized[field] = {"mode": mode, "value": value, "preview": extracted}
        written_fields.append(field)
    return {
        "fields": normalized,
        "written_fields": written_fields,
        "missing_fields": missing_fields,
    }


def _extract_xpath_value(doc, xpath):
    try:
        values = doc.xpath(xpath)
    except Exception:
        return ""
    texts = []
    for value in values:
        if hasattr(value, "xpath"):
            text = " ".join(value.xpath(".//text()[normalize-space()]")).strip()
        else:
            text = str(value).strip()
        if text:
            texts.append(" ".join(text.split()))
    return " ".join(texts).strip()


def _field_value_is_valid(field, value):
    value = (value or "").strip()
    if not value:
        return False
    if field == "content":
        return len(value) >= 20
    return True


def _article_result_message(written_fields, missing_fields):
    labels = {
        "title": "标题",
        "content": "正文",
        "src_time": "时间",
        "source": "来源",
    }
    written = [labels[field] for field in written_fields]
    missing = [labels[field] for field in missing_fields]
    if written and not missing:
        return "已写入：%s。" % "、".join(written)
    if written and missing:
        return "已写入：%s。仍缺少：%s。" % ("、".join(written), "、".join(missing))
    return "没有生成可用字段，请检查点选结果后重试。"


def _call_llm(payload, system_prompt, tool_schema, timeout=DEFAULT_LLM_TIMEOUT):
    client, api_error_cls, api_status_error_cls = _get_openai_client_for_timeout(
        timeout
    )
    request_kwargs = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "submit_result",
                    "description": "Return the final structured result only.",
                    "parameters": tool_schema,
                },
            }
        ],
        "tool_choice": "required",
    }
    if settings.LLM_MAX_TOKENS:
        request_kwargs["max_tokens"] = settings.LLM_MAX_TOKENS
    try:
        response = client.chat.completions.create(**request_kwargs)
    except api_status_error_cls as exc:
        raise RuntimeError(
            "模型请求失败：%s %s" % (exc.status_code, _status_error_detail(exc)[:300])
        )
    except api_error_cls as exc:
        _raise_request_error(exc, timeout)
    except Exception as exc:
        _raise_request_error(exc, timeout)

    try:
        message = response.choices[0].message
    except Exception:
        raise RuntimeError("模型返回格式不可解析。")
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        try:
            arguments = tool_calls[0].function.arguments
        except Exception:
            raise RuntimeError("模型工具返回格式不可解析。")
        return _extract_json_object(arguments)
    content = getattr(message, "content", "")
    return _extract_json_object(content)


def _status_error_detail(exc):
    response = getattr(exc, "response", None)
    detail = ""
    if response is not None:
        try:
            detail = response.text
        except Exception:
            detail = ""
        if not detail:
            try:
                detail = json.dumps(response.json(), ensure_ascii=False)
            except Exception:
                detail = str(response)
    if detail:
        return detail
    return str(exc)


def _raise_request_error(exc, timeout):
    message = str(exc)
    if "ReadTimeout" in message or "timed out" in message.lower():
        raise RuntimeError("模型请求超时，请稍后重试或调大 ZSPIDER_LLM_TIMEOUT。当前超时 %ss。" % timeout)
    raise RuntimeError("模型请求失败：%s" % exc)


def _get_openai_client_for_timeout(timeout):
    try:
        from openai import APIError
        from openai import APIStatusError
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("未安装 openai 包。请先安装依赖。")
    client = OpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE,
        timeout=float(timeout) if timeout is not None else None,
    )
    return client, APIError, APIStatusError


def _extract_json_object(content):
    if isinstance(content, list):
        text = "".join(
            item.get("text", "") for item in content if isinstance(item, dict)
        )
    else:
        text = content or ""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise RuntimeError("模型没有返回 JSON。")
    try:
        return json.loads(match.group(0))
    except Exception:
        raise RuntimeError("模型 JSON 解析失败。")


def _index_system_prompt():
    return (
        "你是网页抽取规则生成器。"
        "给你一个索引页的完整渲染 HTML、用户人工点选的正样本链接 selected_urls，以及可选的误命中反例 excluded_urls。"
        "你的唯一任务是为索引链接抽取生成一个最终规则。"
        "必须调用 submit_result 返回最终答案。"
        "优先返回能稳定覆盖所有 selected_urls 且避开 excluded_urls 的规则。"
        "如果 XPath 更稳，就返回 xpath；如果正则更稳，就返回 re。"
        "返回值必须是可直接写入表单的字段值。"
    )


def _article_system_prompt():
    return (
        "你是文章字段抽取规则生成器。"
        "给你一个文章页完整渲染 HTML，以及用户人工点选的字段样本 field_points。"
        "你的任务是直接生成表单字段，不要生成预览，不要解释。"
        "必须调用 submit_result 返回最终答案。"
        "title 和 content 只能返回 xpath。"
        "src_time 只能返回 xpath。"
        "source 可以返回 xpath 或 specify。"
        "如果某字段当前无法可靠生成，就直接省略该字段。"
        "优先利用用户点选样本提供的 node_xpath、text_xpath、content_xpath、value_xpath 作为参考，但最终必须结合整页 HTML 判断泛化规则。"
        "不要返回 markdown，不要附带原因。"
    )


def _index_tool_schema():
    return {
        "type": "object",
        "properties": {
            "rule_type": {
                "type": "string",
                "enum": ["xpath", "re"],
            },
            "value": {
                "type": "string",
                "description": "The final rule string to write into the form.",
            },
        },
        "required": ["rule_type", "value"],
        "additionalProperties": False,
    }


def _article_tool_schema():
    field_schema = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["xpath", "specify"],
            },
            "value": {
                "type": "string",
            },
        },
        "required": ["mode", "value"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "title": field_schema,
            "content": field_schema,
            "src_time": field_schema,
            "source": field_schema,
        },
        "additionalProperties": False,
    }
