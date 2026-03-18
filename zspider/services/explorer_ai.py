# coding=utf-8
import json
import re
from urllib import error
from urllib.request import Request
from urllib.request import urlopen

from lxml import html

from zspider import settings
from zspider.services import page_explorer

__author__ = "zephor"


FIELD_NAMES = ("title", "content", "src_time", "source")


def generate_index_rule(url, selected_urls, excluded_urls=None, timeout=30):
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
        "output_schema": {
            "rule_type": "xpath or re",
            "value": "single string only",
        },
    }
    result = _call_llm(payload, _index_system_prompt(), timeout=timeout)
    rule_type = (result.get("rule_type") or "").strip().lower()
    value = (result.get("value") or "").strip()
    if rule_type not in ("xpath", "re") or not value:
        raise RuntimeError("模型没有返回可用的 index 规则。")
    return {
        "final_url": final_url,
        "fetch_mode": fetch_mode,
        "rule_type": rule_type,
        "value": value,
    }


def generate_article_fields(url, field_points, timeout=30):
    url = (url or "").strip()
    if not url:
        raise ValueError("请先输入文章地址。")
    _ensure_llm_ready()

    normalized_points = _normalize_field_points(field_points or {})
    if not normalized_points:
        raise ValueError("请先点选至少一个字段样本。")

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
        "output_schema": {
            "title": {"mode": "xpath", "value": "string"},
            "content": {"mode": "xpath", "value": "string"},
            "src_time": {"mode": "xpath or empty", "value": "string"},
            "source": {"mode": "xpath or specify or empty", "value": "string"},
        },
    }
    result = _call_llm(payload, _article_system_prompt(), timeout=timeout)
    return _normalize_article_result(result)


def _ensure_llm_ready():
    if not settings.EXPLORER_LLM_API_KEY or not settings.EXPLORER_LLM_MODEL:
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


def _call_llm(payload, system_prompt, timeout=30):
    response_format = {"type": "json_object"}
    body = {
        "model": settings.EXPLORER_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0,
        "response_format": response_format,
    }
    if settings.EXPLORER_LLM_MAX_TOKENS:
        body["max_tokens"] = settings.EXPLORER_LLM_MAX_TOKENS

    request = Request(
        settings.EXPLORER_LLM_API_BASE.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % settings.EXPLORER_LLM_API_KEY,
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError("模型请求失败：%s %s" % (exc.code, detail[:300]))
    except Exception as exc:
        raise RuntimeError("模型请求失败：%s" % exc)

    try:
        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError("模型返回格式不可解析。")
    return _extract_json_object(content)


def _extract_json_object(content):
    if isinstance(content, list):
        text = "".join(item.get("text", "") for item in content if isinstance(item, dict))
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
        "只允许输出 JSON，对象结构固定为 {\"rule_type\":\"xpath|re\",\"value\":\"...\"}。"
        "必须二选一，只返回一个最终答案，不要解释，不要 markdown。"
        "优先返回能稳定覆盖所有 selected_urls 且避开 excluded_urls 的规则。"
        "如果 XPath 更稳，就返回 xpath；如果正则更稳，就返回 re。"
        "value 必须是可直接写入表单的字段值。"
    )


def _article_system_prompt():
    return (
        "你是文章字段抽取规则生成器。"
        "给你一个文章页完整渲染 HTML，以及用户人工点选的字段样本 field_points。"
        "你的任务是直接生成表单字段，不要生成预览，不要解释。"
        "只允许输出 JSON。"
        "JSON 可包含 title、content、src_time、source 四个键；每个键的值结构固定为 {\"mode\":\"xpath|specify\",\"value\":\"...\"}。"
        "title 和 content 只能返回 xpath。"
        "src_time 只能返回 xpath。"
        "source 可以返回 xpath 或 specify。"
        "如果某字段当前无法可靠生成，就直接省略该字段。"
        "优先利用用户点选样本提供的 node_xpath、text_xpath、content_xpath、value_xpath 作为参考，但最终必须结合整页 HTML 判断泛化规则。"
        "不要返回 markdown，不要附带原因。"
    )
