# coding=utf-8
from collections import OrderedDict
from difflib import SequenceMatcher
from html import escape
from time import monotonic
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.request import Request
from urllib.request import urlopen

from lxml import html

try:
    from zspider.middlewares.browser import render_page_html
except Exception:  # pragma: no cover - optional runtime dependency
    render_page_html = None

__author__ = "zephor"


STATIC_SPIDER = "news"
DYNAMIC_SPIDER = "browser"
_UNSET = object()
_ARTICLE_CONTEXT_CACHE = {}
_ARTICLE_CONTEXT_TTL = 300


def explore_index_page(url, timeout=10):
    url = (url or "").strip()
    if not url:
        raise ValueError("请先输入入口页地址。")

    page_variants = _load_page_variants(url, timeout=timeout)
    final_url = page_variants["final_url"]
    static_doc = page_variants["static_doc"]
    static_candidates = _extract_index_candidates(static_doc, final_url)
    fetch_mode = _detect_fetch_mode(
        final_url,
        static_doc,
        static_candidates,
        timeout=timeout,
        browser_doc=page_variants["browser_doc"],
    )
    doc = _select_effective_doc(fetch_mode, page_variants)
    candidates = _extract_index_candidates(doc, final_url)

    return {
        "url": url,
        "final_url": final_url,
        "title": _page_title(doc),
        "suggested_task_name": _suggest_task_name(doc, final_url),
        "fetch_mode": fetch_mode,
        "candidates": candidates,
        "primary_article_url": _primary_article_url(candidates),
        "preview_html": _build_preview_html(doc, final_url, candidates),
    }


def explore_article_page(url, timeout=10):
    url = (url or "").strip()
    if not url:
        raise ValueError("请先输入文章地址。")

    page_variants = _load_page_variants(url, timeout=timeout)
    final_url = page_variants["final_url"]
    static_doc = page_variants["static_doc"]
    fetch_mode = _detect_fetch_mode(
        final_url,
        static_doc,
        [],
        timeout=timeout,
        browser_doc=page_variants["browser_doc"],
    )
    doc = _select_effective_doc(fetch_mode, page_variants)
    rendered_html = html.tostring(doc, encoding="unicode", method="html")
    _cache_article_context(url, final_url, fetch_mode, rendered_html)
    field_candidates = {
        "title": _extract_title_candidates(doc),
        "content": _extract_content_candidates(doc),
        "src_time": _extract_time_candidates(doc),
        "source": _extract_source_candidates(doc, final_url),
    }
    preview_xpaths = []
    for field in ("title", "content", "src_time"):
        if field_candidates[field]:
            preview_xpath = field_candidates[field][0].get("preview_xpath")
            if preview_xpath:
                preview_xpaths.append(preview_xpath)
    return {
        "url": url,
        "final_url": final_url,
        "title": _page_title(doc),
        "fetch_mode": fetch_mode,
        "field_candidates": field_candidates,
        "coverage": _field_coverage(field_candidates),
        "preview_html": _build_preview_html(
            doc, final_url, [], highlight_xpaths=preview_xpaths
        ),
    }


def get_cached_article_context(url):
    key = (url or "").strip()
    if not key:
        return None
    cached = _ARTICLE_CONTEXT_CACHE.get(key)
    if not cached:
        return None
    if monotonic() - cached["saved_at"] > _ARTICLE_CONTEXT_TTL:
        _ARTICLE_CONTEXT_CACHE.pop(key, None)
        return None
    return {
        "final_url": cached["final_url"],
        "fetch_mode": cached["fetch_mode"],
        "rendered_html": cached["rendered_html"],
    }


def _cache_article_context(url, final_url, fetch_mode, rendered_html):
    payload = {
        "final_url": final_url,
        "fetch_mode": fetch_mode,
        "rendered_html": rendered_html,
        "saved_at": monotonic(),
    }
    for key in _dedupe_preserve_order([url, final_url]):
        normalized = (key or "").strip()
        if normalized:
            _ARTICLE_CONTEXT_CACHE[normalized] = payload


def infer_index_xpath(url, selected_urls, timeout=10):
    url = (url or "").strip()
    if not url:
        raise ValueError("请先输入入口页地址。")

    normalized_urls = _dedupe_preserve_order(
        [_normalize_href(item, url) for item in (selected_urls or [])]
    )
    normalized_urls = [item for item in normalized_urls if item]
    if len(normalized_urls) < 2:
        raise ValueError("请至少标注 2 个目标链接。")

    page_variants = _load_page_variants(url, timeout=timeout)
    final_url = page_variants["final_url"]
    static_doc = page_variants["static_doc"]
    static_candidates = _extract_index_candidates(static_doc, final_url)
    fetch_mode = _detect_fetch_mode(
        final_url,
        static_doc,
        static_candidates,
        timeout=timeout,
        browser_doc=page_variants["browser_doc"],
    )
    doc = _select_effective_doc(fetch_mode, page_variants)
    candidate = _infer_index_candidate(doc, final_url, normalized_urls)
    if candidate is None:
        raise ValueError("当前标注点还不足以推断出稳定的索引 XPath。")
    return {
        "final_url": final_url,
        "fetch_mode": fetch_mode,
        "candidate": candidate,
    }


def build_index_test_rows(front_url, url_xpath, urls, timeout=10):
    normalized_urls = [u for u in urls if u]
    if not normalized_urls:
        return []

    rows = [{"url": url, "title": ""} for url in normalized_urls]
    if not front_url or not url_xpath:
        return rows

    try:
        final_url, html_text = _fetch_html(front_url, timeout=timeout)
        doc = _parse_html(html_text, final_url)
        title_map = _extract_index_title_map(doc, final_url, url_xpath)
    except Exception:
        return rows

    for row in rows:
        row["title"] = title_map.get(row["url"], "")
    return rows


def _fetch_html(url, timeout=10):
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        final_url = response.geturl()
        charset = response.headers.get_content_charset() or "utf-8"
    try:
        html_text = raw.decode(charset)
    except (LookupError, UnicodeDecodeError):
        html_text = raw.decode("utf-8", errors="ignore")
    return final_url, html_text


def _fetch_browser_html(url, timeout=10):
    if render_page_html is None:
        raise RuntimeError("browser renderer is not installed")
    return render_page_html(url, timeout=timeout)


def _dedupe_preserve_order(values):
    deduped = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _load_page_variants(url, timeout=10):
    final_url, html_text = _fetch_html(url, timeout=timeout)
    static_doc = _parse_html(html_text, final_url)
    browser_doc = None
    try:
        browser_html = _fetch_browser_html(final_url, timeout=timeout)
    except Exception:
        browser_html = ""
    if browser_html:
        try:
            browser_doc = _parse_html(browser_html, final_url)
        except Exception:
            browser_doc = None
    return {
        "final_url": final_url,
        "static_doc": static_doc,
        "browser_doc": browser_doc,
    }


def _select_effective_doc(fetch_mode, page_variants):
    if (
        fetch_mode.get("recommended_spider") == DYNAMIC_SPIDER
        and page_variants.get("browser_doc") is not None
    ):
        return page_variants["browser_doc"]
    return page_variants["static_doc"]


def _extract_index_title_map(doc, base_url, url_xpath):
    nodes = []
    href_attr_xpath = ""
    if url_xpath.endswith("/@href"):
        href_attr_xpath = url_xpath
        try:
            nodes = doc.xpath(url_xpath[:-6])
        except Exception:
            nodes = []
    else:
        try:
            nodes = doc.xpath(url_xpath)
        except Exception:
            nodes = []

    title_map = OrderedDict()
    for node in nodes:
        href = ""
        title = ""
        if isinstance(getattr(node, "tag", None), str):
            if node.tag.lower() == "a":
                href = _normalize_href(node.get("href"), base_url)
                title = " ".join(node.xpath(".//text()[normalize-space()]")).strip()
            else:
                href = _normalize_href("".join(node.xpath("./@href")).strip(), base_url)
                title = " ".join(node.xpath(".//text()[normalize-space()]")).strip()
                if not title:
                    anchor = node.xpath(".//a[@href][1]")
                    if anchor:
                        title = " ".join(
                            anchor[0].xpath(".//text()[normalize-space()]")
                        ).strip()
        if href and href not in title_map:
            title_map[href] = title[:180]

    if not title_map and href_attr_xpath:
        try:
            values = doc.xpath(href_attr_xpath)
        except Exception:
            values = []
        for value in values:
            href = _normalize_href(value, base_url)
            if href and href not in title_map:
                title_map[href] = ""
    return title_map


def _infer_index_candidate(doc, base_url, selected_urls):
    base_host = urlparse(base_url).netloc
    selected_urls = _dedupe_preserve_order(selected_urls)
    anchor_groups = OrderedDict()
    for anchor in doc.xpath("//a[@href]"):
        href = _normalize_href(anchor.get("href"), base_url)
        if href not in selected_urls:
            continue
        anchor_groups.setdefault(href, []).append(anchor)

    if len(anchor_groups) < len(selected_urls):
        return None

    candidate_sources = {}
    for href, anchors in anchor_groups.items():
        local_candidates = set()
        for anchor in anchors:
            for node in _candidate_nodes(anchor):
                local_candidates.add(_candidate_xpath(node))
                specialized = _candidate_link_xpath(node, base_url)
                if specialized:
                    local_candidates.add(specialized)
        for xpath in local_candidates:
            if not xpath:
                continue
            candidate_sources.setdefault(xpath, set()).add(href)

    inferred_candidates = []
    for xpath, matched_urls in candidate_sources.items():
        if len(matched_urls) != len(selected_urls):
            continue
        urls = _evaluate_candidate_urls(doc, base_url, xpath, base_host)
        if len(urls) < len(selected_urls):
            continue
        selected_count = sum(1 for url in selected_urls if url in urls)
        if selected_count != len(selected_urls):
            continue
        sample_texts = list(_extract_index_title_map(doc, base_url, xpath).values())[:3]
        total_count = len(urls)
        extra_count = max(0, total_count - selected_count)
        score = selected_count * 100 - extra_count * 3
        if xpath.startswith("//*[self::h1 or self::h2 or self::h3 or self::h4]"):
            score += 15
        reason = "已覆盖你标注的 %s 个目标链接，额外命中 %s 条链接。" % (selected_count, extra_count)
        inferred_candidates.append(
            {
                "xpath": xpath,
                "count": total_count,
                "sample_urls": urls[:3],
                "sample_texts": sample_texts,
                "score": score,
                "reason": reason,
            }
        )

    if not inferred_candidates:
        return None
    inferred_candidates.sort(
        key=lambda item: (-item["score"], item["count"], len(item["xpath"]))
    )
    return inferred_candidates[0]


def _parse_html(html_text, base_url):
    doc = html.fromstring(html_text)
    doc.make_links_absolute(base_url)
    return doc


def _evaluate_candidate_urls(doc, base_url, xpath, base_host):
    try:
        values = doc.xpath(xpath)
    except Exception:
        return []
    urls = []
    for value in values:
        href = value
        if not isinstance(href, str):
            href = str(href)
        href = _normalize_href(href, base_url)
        if not href:
            continue
        urls.append(href)
    return _dedupe_preserve_order(_filter_candidate_urls(urls, base_host))


def _page_title(doc):
    title = "".join(doc.xpath("//title/text()")).strip()
    return title or "未识别到页面标题"


def _suggest_task_name(doc, final_url):
    derived = _host_channel_task_name(final_url)
    if derived:
        return derived[:64]
    title = _clean_task_title(_page_title(doc))
    if title:
        return title[:64]
    host = urlparse(final_url).netloc
    return host[:64]


def _host_channel_task_name(final_url):
    parsed = urlparse(final_url)
    host = parsed.netloc.lower()
    if not host:
        return ""
    sina_channel_map = {
        "mil": "军事",
        "news": "新闻",
        "finance": "财经",
        "tech": "科技",
        "sports": "体育",
        "ent": "娱乐",
    }
    if host.endswith("sina.com.cn"):
        labels = [item for item in host.split(".") if item]
        for label in labels:
            if label in sina_channel_map:
                return "新浪%s" % sina_channel_map[label]
        return "新浪"
    return ""


def _clean_task_title(title):
    title = (title or "").strip()
    if not title or title == "未识别到页面标题":
        return ""
    for marker in ("|", "-", "_", "—"):
        if marker in title:
            title = title.split(marker)[0].strip()
            if title:
                break
    lowered = title.lower()
    if lowered in ("icon关闭", "icon close", "close", "loading"):
        return ""
    if any(marker in lowered for marker in ("登录", "注册", "关闭", "icon")):
        return ""
    return title


def _primary_article_url(candidates):
    for candidate in candidates:
        sample_urls = candidate.get("sample_urls") or []
        if sample_urls:
            return sample_urls[0]
    return ""


def _field_coverage(field_candidates):
    coverage = OrderedDict()
    for field_name, field_label in (
        ("title", "标题"),
        ("content", "正文"),
        ("src_time", "时间"),
        ("source", "来源"),
    ):
        candidates = field_candidates.get(field_name) or []
        coverage[field_name] = {
            "label": field_label,
            "count": len(candidates),
            "status": "ready" if candidates else "missing",
        }
    return coverage


def _extract_index_candidates(doc, base_url):
    base_host = urlparse(base_url).netloc
    groups = {}
    anchors = doc.xpath("//a[@href]")
    for anchor in anchors:
        href = _normalize_href(anchor.get("href"), base_url)
        if href is None:
            continue
        text = " ".join(anchor.xpath(".//text()[normalize-space()]")).strip()
        for node in _candidate_nodes(anchor):
            xpath = _candidate_xpath(node)
            if xpath in groups:
                group = groups[xpath]
            else:
                group = groups[xpath] = {
                    "xpath": xpath,
                    "node": node,
                    "urls": OrderedDict(),
                    "texts": OrderedDict(),
                }
            group["urls"][href] = True
            if text and href not in group["texts"]:
                group["texts"][href] = text

    candidates = []
    for group in groups.values():
        xpath = _candidate_link_xpath(group["node"], base_url) or group["xpath"]
        urls = list(group["urls"].keys())
        if len(urls) < 2:
            continue
        urls = _filter_candidate_urls(urls, base_host)
        if len(urls) < 2:
            continue
        texts = list(group["texts"].values())
        score = _candidate_score(urls, texts, base_host)
        candidates.append(
            {
                "xpath": xpath,
                "count": len(urls),
                "sample_urls": urls[:3],
                "sample_texts": texts[:3],
                "score": score,
                "reason": _candidate_reason(urls, texts, base_host),
            }
        )

    candidates.sort(key=lambda item: (-item["score"], -item["count"], item["xpath"]))
    deduped = []
    seen = set()
    for index, candidate in enumerate(candidates):
        signature = tuple(candidate["sample_urls"])
        if signature in seen:
            continue
        seen.add(signature)
        candidate["key"] = "candidate-%s" % (len(deduped) + 1)
        deduped.append(candidate)
        if len(deduped) >= 5:
            break
    return deduped


def _candidate_link_xpath(node, base_url):
    heading_xpath = _candidate_heading_xpath(node, base_url)
    if heading_xpath:
        return heading_xpath
    return _candidate_xpath(node)


def _candidate_heading_xpath(node, base_url):
    element_xpath = _candidate_container_xpath(node)
    heading_xpath = (
        "%s//*[self::h1 or self::h2 or self::h3 or self::h4]//a[@href]/@href"
        % element_xpath
    )
    try:
        values = node.getroottree().xpath(heading_xpath)
    except Exception:
        return ""
    matches = []
    for value in values:
        href = _normalize_href(value, base_url)
        if _is_preferred_article_url(href, urlparse(base_url).netloc):
            matches.append(href)
    if len(set(matches)) >= 2:
        return _shorten_heading_xpath(heading_xpath)
    return ""


def _candidate_container_xpath(node):
    segments = []
    current = node
    anchored = False
    while current is not None and getattr(current, "tag", None) not in ("body", "html"):
        segment, is_specific = _selector_segment(current)
        segments.append(segment)
        anchored = anchored or is_specific
        if is_specific and len(segments) >= 2:
            break
        if len(segments) >= 4:
            break
        current = current.getparent()
    segments.reverse()
    if not segments:
        return "//body"
    if anchored:
        xpath = "//%s" % "/".join(segments)
    else:
        xpath = "//%s" % segments[-1]
    return _shorten_container_xpath(xpath)


def _filter_candidate_urls(urls, base_host):
    preferred = []
    fallback = []
    for url in urls:
        if _is_preferred_article_url(url, base_host):
            preferred.append(url)
        else:
            fallback.append(url)
    return preferred or fallback


def _is_preferred_article_url(url, base_host):
    if not url:
        return False
    parsed = urlparse(url)
    host = parsed.netloc
    if base_host and host and host != base_host:
        return False
    lowered = parsed.path.lower()
    if not lowered or lowered in ("/", ""):
        return False
    if any(
        marker in lowered
        for marker in ("/comment", "/video", "/slide", "/photo", "/collection")
    ):
        return False
    if any(marker in lowered for marker in ("doc-", ".shtml", ".html")):
        return True
    return len([part for part in parsed.path.split("/") if part]) >= 2


def _candidate_nodes(anchor):
    node = anchor.getparent()
    depth = 0
    while node is not None and depth < 3:
        if getattr(node, "tag", None) in ("body", "html"):
            break
        yield node
        node = node.getparent()
        depth += 1


def _candidate_xpath(node):
    segments = []
    current = node
    anchored = False
    while current is not None and getattr(current, "tag", None) not in ("body", "html"):
        segment, is_specific = _selector_segment(current)
        segments.append(segment)
        anchored = anchored or is_specific
        if is_specific and len(segments) >= 2:
            break
        if len(segments) >= 4:
            break
        current = current.getparent()
    segments.reverse()
    if not segments:
        return "//a[@href]/@href"
    if anchored:
        xpath = "//%s//a[@href]/@href" % "/".join(segments)
    else:
        xpath = "//%s//a[@href]/@href" % segments[-1]
    return _shorten_xpath(xpath)


def _selector_segment(node):
    node_id = (node.get("id") or "").strip()
    if node_id:
        return '%s[@id="%s"]' % (node.tag, node_id.replace('"', "")), True

    classes = [
        c
        for c in (node.get("class") or "").split()
        if c and not c.isdigit() and len(c) <= 24 and _useful_class_name(c)
    ][:1]
    if classes:
        return '%s[contains(@class, "%s")]' % (node.tag, classes[0]), True

    return node.tag, False


def _useful_class_name(class_name):
    lowered = class_name.lower()
    if len(lowered) < 4:
        return False
    if lowered.startswith(("mt-", "mb-", "ml-", "mr-", "pt-", "pb-", "pl-", "pr-")):
        return False
    if lowered.startswith(("text-", "bg-", "grid-", "flex-", "gap-", "w-", "h-")):
        return False
    if lowered in ("active", "current", "item", "list", "grid", "flex", "content"):
        return False
    return True


def _shorten_xpath(xpath, max_length=128):
    xpath = xpath or ""
    if len(xpath) <= max_length:
        return xpath

    last_segment = xpath.split("//")[-1]
    simplified = "//%s" % last_segment
    if len(simplified) <= max_length:
        return simplified

    for tag in ("article", "section", "div", "li", "ul", "main"):
        fallback = "//%s//a[@href]/@href" % tag
        if len(fallback) <= max_length:
            return fallback

    return "//a[@href]/@href"


def _shorten_container_xpath(xpath, max_length=112):
    xpath = xpath or ""
    if len(xpath) <= max_length:
        return xpath

    last_segment = xpath.split("//")[-1]
    simplified = "//%s" % last_segment
    if len(simplified) <= max_length:
        return simplified

    for tag in ("article", "section", "div", "li", "ul", "main"):
        fallback = "//%s" % tag
        if len(fallback) <= max_length:
            return fallback
    return "//body"


def _shorten_heading_xpath(xpath, max_length=160):
    xpath = xpath or ""
    if len(xpath) <= max_length:
        return xpath

    fallback = "//*[self::h1 or self::h2 or self::h3 or self::h4]//a[@href]/@href"
    if len(fallback) <= max_length:
        return fallback
    return "//h3//a[@href]/@href"


def _normalize_href(href, base_url):
    href = (href or "").strip()
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return None
    if href.startswith("mailto:") or href.startswith("tel:"):
        return None
    return urljoin(base_url, href)


def _candidate_score(urls, texts, base_host):
    count = len(urls)
    internal = 0
    article_like = 0
    for url in urls:
        parsed = urlparse(url)
        if parsed.netloc == base_host:
            internal += 1
        if len([p for p in parsed.path.split("/") if p]) >= 2:
            article_like += 1
    avg_text = 0
    if texts:
        avg_text = sum(len(text) for text in texts) / float(len(texts))

    score = count * 4
    score += internal * 2
    score += article_like * 2
    if 6 <= avg_text <= 80:
        score += 6
    if count > 30:
        score -= count // 2
    return score


def _candidate_reason(urls, texts, base_host):
    internal = sum(1 for url in urls if urlparse(url).netloc == base_host)
    if texts:
        text_hint = "链接文本可读"
    else:
        text_hint = "链接文本较少"
    return "命中 %s 条链接，其中站内链接 %s 条，%s。" % (len(urls), internal, text_hint)


def _detect_fetch_mode(url, doc, candidates, timeout=10, browser_doc=_UNSET):
    comparison = None
    if browser_doc is _UNSET:
        try:
            browser_html = _fetch_browser_html(url, timeout=timeout)
        except Exception:
            browser_html = ""
        if browser_html:
            try:
                browser_doc = _parse_html(browser_html, url)
            except Exception:
                browser_doc = None
        else:
            browser_doc = None
    if browser_doc is not None:
        comparison = _compare_fetch_versions(doc, browser_doc)
        if comparison["is_similar"]:
            if candidates:
                return _static_mode(
                    "直接请求和浏览器渲染拿到的页面结构基本一致（正文相似度 %s，链接重合度 %s），静态页面中已识别到候选链接区域，建议先直接抓取。"
                    % (comparison["text_ratio_label"], comparison["link_overlap_label"])
                )
            return _static_mode(
                "直接请求和浏览器渲染拿到的页面结构基本一致（正文相似度 %s，链接重合度 %s），建议先直接抓取。"
                % (comparison["text_ratio_label"], comparison["link_overlap_label"])
            )
        return _dynamic_mode(
            "直接请求和浏览器渲染拿到的页面结构差异明显（正文相似度 %s，链接重合度 %s），建议使用浏览器渲染。"
            % (comparison["text_ratio_label"], comparison["link_overlap_label"])
        )

    return _detect_fetch_mode_by_static_doc(doc, candidates)


def _detect_fetch_mode_by_static_doc(doc, candidates):
    metrics = _doc_metrics(doc)

    if not candidates and metrics["script_count"] >= 5 and metrics["body_length"] < 400:
        return _dynamic_mode("页面正文和候选链接都偏少，脚本较多，优先尝试浏览器渲染。")
    if (
        metrics["shell_nodes"]
        and metrics["script_count"] >= 5
        and metrics["link_count"] < 8
    ):
        return _dynamic_mode("页面存在典型应用壳节点，且静态链接偏少，优先尝试浏览器渲染。")
    if candidates:
        return _static_mode("静态页面中已识别到候选链接区域，建议先直接抓取。")
    if metrics["link_count"] >= 8 and metrics["body_length"] >= 400:
        return _static_mode("页面静态内容较完整，建议先直接抓取。")
    return _static_mode("当前页面可先按直接抓取尝试；若候选结果偏少，再切换浏览器渲染。")


def _compare_fetch_versions(static_doc, browser_doc):
    static_metrics = _doc_metrics(static_doc)
    browser_metrics = _doc_metrics(browser_doc)

    text_ratio = _sequence_ratio(
        static_metrics["body_excerpt"], browser_metrics["body_excerpt"]
    )
    title_ratio = _sequence_ratio(static_metrics["title"], browser_metrics["title"])
    body_length_ratio = _count_ratio(
        static_metrics["body_length"], browser_metrics["body_length"]
    )
    link_overlap = _overlap_ratio(
        static_metrics["link_hrefs"], browser_metrics["link_hrefs"]
    )
    link_count_ratio = _count_ratio(
        static_metrics["link_count"], browser_metrics["link_count"]
    )
    score = (
        text_ratio * 0.45
        + body_length_ratio * 0.2
        + link_overlap * 0.2
        + link_count_ratio * 0.1
        + title_ratio * 0.05
    )
    is_similar = score >= 0.72 or (
        text_ratio >= 0.8 and (link_overlap >= 0.5 or link_count_ratio >= 0.75)
    )

    return {
        "is_similar": is_similar,
        "score": score,
        "text_ratio": text_ratio,
        "link_overlap": link_overlap,
        "text_ratio_label": _ratio_label(text_ratio),
        "link_overlap_label": _ratio_label(link_overlap),
    }


def _doc_metrics(doc):
    body_text = _normalize_text(
        " ".join(doc.xpath("//body//text()[normalize-space()]"))
    )
    link_hrefs = []
    for href in doc.xpath("//a[@href]/@href"):
        href = (href or "").strip()
        if href and href not in link_hrefs:
            link_hrefs.append(href)

    return {
        "title": _normalize_text(_page_title(doc)),
        "body_excerpt": body_text[:2000],
        "body_length": len(body_text),
        "script_count": len(doc.xpath("//script")),
        "link_count": len(link_hrefs),
        "link_hrefs": link_hrefs[:80],
        "shell_nodes": doc.xpath(
            '//*[@id="app" or @id="root" or @id="__next" or @id="main"]'
        ),
    }


def _normalize_text(text):
    return " ".join((text or "").split())


def _sequence_ratio(left, right):
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _count_ratio(left, right):
    if left == right == 0:
        return 1.0
    if not left or not right:
        return 0.0
    return min(left, right) / float(max(left, right))


def _overlap_ratio(left, right):
    left_set = set(left or [])
    right_set = set(right or [])
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / float(max(len(left_set), len(right_set)))


def _ratio_label(value):
    return "%s%%" % int(round((value or 0) * 100))


def _static_mode(reason):
    return {
        "label": "直接抓取",
        "recommended_spider": STATIC_SPIDER,
        "recommended_spider_label": "NewsSpider",
        "reason": reason,
    }


def _dynamic_mode(reason):
    return {
        "label": "浏览器渲染",
        "recommended_spider": DYNAMIC_SPIDER,
        "recommended_spider_label": "BrowserSpider",
        "reason": reason,
    }


def _build_preview_html(doc, base_url, candidates, highlight_xpaths=None):
    preview_doc = html.fromstring(html.tostring(doc, encoding="unicode"))
    _sanitize_preview_doc(preview_doc)

    highlight_urls = set()
    if candidates:
        highlight_urls.update(candidates[0]["sample_urls"])
    for anchor in preview_doc.xpath("//a[@href]"):
        href = _normalize_href(anchor.get("href"), base_url)
        if href in highlight_urls:
            anchor.set("data-explore-hit", "1")
    for xpath in highlight_xpaths or []:
        try:
            for node in preview_doc.xpath(xpath):
                if getattr(node, "set", None):
                    node.set("data-explore-hit", "1")
        except Exception:
            continue

    body = preview_doc.xpath("//body")
    preview_body = body[0] if body else preview_doc
    body_html = html.tostring(preview_body, encoding="unicode")
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <base href="{base_url}">
    <style>
        * {{
            box-sizing: border-box;
        }}
        html {{
            background: #eef3f8;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 14px;
            line-height: 1.6;
            margin: 0;
            padding: 18px;
            background: #eef3f8;
            color: #243447;
        }}
        .preview-shell {{
            max-width: 960px;
            margin: 0 auto;
            padding: 20px 24px 40px;
            background: #ffffff;
            border: 1px solid #dce8f1;
            border-radius: 8px;
            box-shadow: 0 10px 24px rgba(24, 53, 82, 0.08);
        }}
        a {{
            color: #0b5cad;
            text-decoration: none;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        pre {{
            white-space: pre-wrap;
            word-break: break-word;
        }}
        [hidden],
        template {{
            display: none !important;
        }}
        [data-explore-hover="1"] {{
            outline: 2px solid #6db3ff;
            outline-offset: 2px;
            background: rgba(109, 179, 255, 0.12);
            cursor: crosshair;
        }}
        [data-explore-hit="1"] {{
            background: #fff2be;
            color: #8a5d00;
            outline: 2px solid #f0c24b;
            border-radius: 2px;
        }}
        [data-explore-selected="1"] {{
            outline: 3px solid #ff8a3d;
            outline-offset: 2px;
            background: rgba(255, 138, 61, 0.14);
        }}
    </style>
</head>
<body>
    <div class="preview-shell">
        {body_html}
    </div>
    <script>
    (function() {{
        var currentHover = null;
        var currentSelected = null;
        var hitAttr = 'data-explore-hit';

        function cssEscape(value) {{
            return String(value).replace(/"/g, '\\"');
        }}

        function clearAppliedHighlights() {{
            var nodes = document.querySelectorAll('[' + hitAttr + '="1"]');
            Array.prototype.forEach.call(nodes, function(node) {{
                node.removeAttribute(hitAttr);
            }});
        }}

        function highlightNode(node) {{
            if (!node || node.nodeType !== 1) {{
                return;
            }}
            node.setAttribute(hitAttr, '1');
        }}

        function highlightResultValue(value) {{
            if (!value) {{
                return;
            }}
            if (value.nodeType === 1) {{
                highlightNode(value);
                return;
            }}
            if (value.nodeType === 2 && value.ownerElement) {{
                highlightNode(value.ownerElement);
                return;
            }}
            if (value.nodeType === 3 && value.parentElement) {{
                highlightNode(value.parentElement);
            }}
        }}

        function evaluateAndHighlight(xpath) {{
            if (!xpath) {{
                return 0;
            }}
            var count = 0;
            try {{
                var result = document.evaluate(
                    xpath,
                    document,
                    null,
                    XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                    null
                );
                for (var i = 0; i < result.snapshotLength; i += 1) {{
                    highlightResultValue(result.snapshotItem(i));
                    count += 1;
                }}
                if (count) {{
                    return count;
                }}
            }} catch (error) {{}}

            try {{
                var valueResult = document.evaluate(
                    xpath,
                    document,
                    null,
                    XPathResult.ANY_TYPE,
                    null
                );
                var node = valueResult.iterateNext ? valueResult.iterateNext() : null;
                while (node) {{
                    highlightResultValue(node);
                    count += 1;
                    node = valueResult.iterateNext();
                }}
            }} catch (error) {{}}
            return count;
        }}

        function applyHighlights(items) {{
            clearAppliedHighlights();
            Array.prototype.forEach.call(items || [], function(item) {{
                if (!item) {{
                    return;
                }}
                if (item.xpath) {{
                    evaluateAndHighlight(item.xpath);
                    return;
                }}
                if (item.regex) {{
                    highlightAnchorsByRegex(item.regex);
                }}
            }});
        }}

        function highlightAnchorsByRegex(pattern) {{
            if (!pattern) {{
                return 0;
            }}
            var regex = null;
            var count = 0;
            try {{
                regex = new RegExp(pattern);
            }} catch (error) {{
                return 0;
            }}
            Array.prototype.forEach.call(document.querySelectorAll('a[href]'), function(anchor) {{
                if (!anchor || !anchor.href) {{
                    return;
                }}
                regex.lastIndex = 0;
                if (!regex.test(anchor.href)) {{
                    return;
                }}
                highlightNode(anchor);
                count += 1;
            }});
            return count;
        }}

        function xpathFor(node) {{
            if (!node || node.nodeType !== 1) {{
                return '';
            }}
            if (node.id) {{
                return '//*[@id="' + cssEscape(node.id) + '"]';
            }}
            var segments = [];
            var current = node;
            while (current && current.nodeType === 1 && current.tagName.toLowerCase() !== 'html') {{
                var tag = current.tagName.toLowerCase();
                var index = 1;
                var sibling = current.previousElementSibling;
                while (sibling) {{
                    if (sibling.tagName === current.tagName) {{
                        index += 1;
                    }}
                    sibling = sibling.previousElementSibling;
                }}
                segments.unshift(tag + '[' + index + ']');
                current = current.parentElement;
            }}
            return '//' + segments.join('/');
        }}

        function selectorSegment(node) {{
            if (!node || node.nodeType !== 1) {{
                return '';
            }}
            if (node.id) {{
                return node.tagName.toLowerCase() + '[@id="' + cssEscape(node.id) + '"]';
            }}
            var classNames = (node.className || '').split(/\\s+/).filter(function(name) {{
                return name && !/^\\d+$/.test(name) && name.length <= 24 && usefulClassName(name);
            }}).slice(0, 1);
            if (classNames.length) {{
                return node.tagName.toLowerCase() + '[contains(@class, "' + cssEscape(classNames[0]) + '")]';
            }}
            return node.tagName.toLowerCase();
        }}

        function usefulClassName(name) {{
            var lowered = String(name || '').toLowerCase();
            if (lowered.length < 4) {{
                return false;
            }}
            if (/^(mt|mb|ml|mr|pt|pb|pl|pr)-/.test(lowered)) {{
                return false;
            }}
            if (/^(text|bg|grid|flex|gap|w|h)-/.test(lowered)) {{
                return false;
            }}
            return ['active', 'current', 'item', 'list', 'grid', 'flex', 'content'].indexOf(lowered) === -1;
        }}

        function shortenXpath(xpath) {{
            if (!xpath || xpath.length <= 128) {{
                return xpath;
            }}
            var parts = xpath.split('//');
            var simplified = '//' + parts[parts.length - 1];
            if (simplified.length <= 128) {{
                return simplified;
            }}
            return '//a[@href]/@href';
        }}

        function regionLinkCandidates(node) {{
            var candidates = [];
            var seen = {{}};
            var current = node;
            var depth = 0;
            while (current && current.nodeType === 1 && current.tagName.toLowerCase() !== 'body' && depth < 4) {{
                if (current.querySelectorAll('a[href]').length >= 2) {{
                    var segments = [];
                    var walk = current;
                    var anchored = false;
                    var limit = 0;
                    while (walk && walk.nodeType === 1 && walk.tagName.toLowerCase() !== 'body' && limit < 4) {{
                        var segment = selectorSegment(walk);
                        segments.unshift(segment);
                        if (walk.id || ((walk.className || '').trim())) {{
                            anchored = true;
                        }}
                        if (anchored && segments.length >= 2) {{
                            break;
                        }}
                        walk = walk.parentElement;
                        limit += 1;
                    }}
                    if (segments.length) {{
                        var xpath = '//' + (anchored ? segments.join('/') : segments[segments.length - 1]) + '//a[@href]/@href';
                        xpath = shortenXpath(xpath);
                        if (!seen[xpath]) {{
                            seen[xpath] = true;
                            candidates.push(xpath);
                        }}
                    }}
                }}
                current = current.parentElement;
                depth += 1;
            }}
            return candidates.slice(0, 3);
        }}

        function contentRoot(node) {{
            var current = node;
            while (current && current.parentElement) {{
                var tag = current.tagName.toLowerCase();
                var parent = current.parentElement;
                if ((tag === 'p' || tag === 'li') && parent.querySelectorAll('p, li').length > 1) {{
                    return parent;
                }}
                current = parent;
                if (!current || current.tagName.toLowerCase() === 'body') {{
                    return node;
                }}
                if (/^(article|main|section)$/i.test(current.tagName)) {{
                    return current;
                }}
            }}
            return node;
        }}

        function closestSelectable(node) {{
            var element = node && node.nodeType === 1 ? node : node.parentElement;
            if (!element) {{
                return null;
            }}
            return element.closest('a, h1, h2, h3, h4, h5, h6, article, main, section, div, p, li, time, span, strong, em') || element;
        }}

        function setHover(element) {{
            if (currentHover && currentHover !== currentSelected) {{
                currentHover.removeAttribute('data-explore-hover');
            }}
            currentHover = element;
            if (currentHover && currentHover !== currentSelected) {{
                currentHover.setAttribute('data-explore-hover', '1');
            }}
        }}

        function setSelected(element) {{
            if (currentSelected) {{
                currentSelected.removeAttribute('data-explore-selected');
            }}
            currentSelected = element;
            if (currentHover && currentHover !== currentSelected) {{
                currentHover.removeAttribute('data-explore-hover');
            }}
            if (currentSelected) {{
                currentSelected.setAttribute('data-explore-selected', '1');
            }}
        }}

        function payloadFor(element) {{
            var anchor = element.closest('a[href]');
            var linkXpath = anchor ? xpathFor(anchor) + '/@href' : '';
            var regionCandidates = regionLinkCandidates(anchor ? anchor.parentElement || anchor : element);
            var valueXpath = '';
            if (element.tagName.toLowerCase() === 'time' && element.getAttribute('datetime')) {{
                valueXpath = xpathFor(element) + '/@datetime';
            }}
            var text = (element.textContent || '').replace(/\\s+/g, ' ').trim();
            var selectedXpath = xpathFor(element);
            var contentNode = contentRoot(element);
            return {{
                source: 'zspider-preview-select',
                tag: element.tagName.toLowerCase(),
                text: text.slice(0, 400),
                href: anchor ? anchor.href : '',
                node_xpath: selectedXpath,
                text_xpath: selectedXpath + '//text()',
                content_xpath: xpathFor(contentNode) + '//*[self::p or self::li]//text()',
                value_xpath: valueXpath,
                link_xpath: linkXpath,
                region_link_xpath: regionCandidates[0] || '',
                region_link_candidates: regionCandidates
            }};
        }}

        document.addEventListener('mouseover', function(event) {{
            var element = closestSelectable(event.target);
            if (!element) {{
                return;
            }}
            setHover(element);
        }}, true);

        document.addEventListener('click', function(event) {{
            event.preventDefault();
            event.stopPropagation();
            var element = closestSelectable(event.target);
            if (!element) {{
                return;
            }}
            setSelected(element);
            window.parent.postMessage(payloadFor(element), '*');
        }}, true);

        window.addEventListener('message', function(event) {{
            var payload = event.data || {{}};
            if (payload.source !== 'zspider-preview-command') {{
                return;
            }}
            if (payload.action === 'highlight-xpaths') {{
                applyHighlights(payload.items || []);
            }}
        }});
    }})();
    </script>
</body>
</html>
""".strip().format(
        base_url=escape(base_url, quote=True), body_html=body_html
    )


def _sanitize_preview_doc(preview_doc):
    for node in preview_doc.xpath("//script|//noscript|//iframe|//style|//link"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)

    for node in preview_doc.iter():
        if not isinstance(getattr(node, "tag", None), str):
            continue
        for attr in list(node.attrib.keys()):
            attr_name = attr.lower()
            if attr_name.startswith("on"):
                node.attrib.pop(attr, None)
                continue
            if attr_name in (
                "style",
                "srcset",
                "loading",
                "decoding",
                "fetchpriority",
                "integrity",
                "crossorigin",
                "referrerpolicy",
            ):
                node.attrib.pop(attr, None)
                continue
            if attr_name in ("width", "height", "sizes"):
                node.attrib.pop(attr, None)


def _extract_title_candidates(doc):
    h1_candidate = _best_title_element_candidate(doc)
    candidates = [
        h1_candidate,
        _value_xpath_candidate(
            doc,
            "title",
            '//meta[@property="og:title"]/@content',
            "优先使用页面声明的 og:title。",
        ),
        _value_xpath_candidate(
            doc,
            "title",
            "//title/text()",
            "页面 title 可作为标题兜底。",
        ),
    ]
    return _compact_candidates(candidates)


def _best_title_element_candidate(doc):
    best = None
    for node in doc.xpath("//h1[normalize-space()]"):
        text = " ".join(node.xpath(".//text()[normalize-space()]")).strip()
        if not text:
            continue
        score = len(text)
        class_name = (node.get("class") or "").lower()
        node_id = (node.get("id") or "").lower()
        if "main-title" in class_name:
            score += 80
        if "title" in class_name or "title" in node_id:
            score += 30
        if any(marker in text for marker in ("_", "|", "新浪")):
            score -= 20
        if len(text) <= 4:
            score -= 40
        if best is None or score > best[0]:
            best = (score, node, text)
    if best is None:
        return None
    _, node, text = best
    preview_xpath = _element_preview_xpath(node)
    rule = "%s//text()" % preview_xpath
    return {
        "field": "title",
        "mode": "xpath",
        "rule": rule,
        "preview": text[:180],
        "reason": "优先命中详情页主标题节点。",
        "preview_xpath": preview_xpath,
    }


def _extract_time_candidates(doc):
    candidates = [
        _value_xpath_candidate(
            doc,
            "src_time",
            "//time[@datetime][1]/@datetime",
            "优先使用 time 标签中的 datetime 属性。",
            preview_xpath="//time[1]",
        ),
        _element_text_candidate(
            doc,
            "src_time",
            "//time[normalize-space()][1]",
            "//time[1]/text()",
            "页面存在 time 标签文本，可直接作为时间来源。",
        ),
        _value_xpath_candidate(
            doc,
            "src_time",
            '//meta[@property="article:published_time"]/@content',
            "页面声明了 article:published_time 元信息。",
        ),
    ]
    return _compact_candidates(candidates)


def _extract_content_candidates(doc):
    candidates = []
    for xpath in ("//article[1]", "//main[1]"):
        candidate = _content_candidate(doc, xpath)
        if candidate is not None:
            candidates.append(candidate)

    scored_nodes = []
    for node in doc.xpath("//div|//section"):
        text = " ".join(node.xpath(".//p//text()[normalize-space()]")).strip()
        p_count = len(node.xpath(".//p[normalize-space()]"))
        if p_count < 2 or len(text) < 20:
            continue
        score = len(text) + p_count * 60
        scored_nodes.append((score, node))
    scored_nodes.sort(key=lambda item: item[0], reverse=True)
    for _, node in scored_nodes[:2]:
        candidate = _content_candidate(doc, _element_preview_xpath(node))
        if candidate is not None:
            candidates.append(candidate)
    return _compact_candidates(candidates)


def _extract_source_candidates(doc, final_url):
    candidates = [
        _specify_candidate(
            "source",
            "".join(doc.xpath('//meta[@property="og:site_name"]/@content')).strip(),
            "优先使用页面声明的站点名称。",
        )
    ]
    host = urlparse(final_url).netloc
    if host:
        candidates.append(_specify_candidate("source", host, "站点域名可作为来源兜底。"))
    return _compact_candidates(candidates)


def _content_candidate(doc, node_xpath):
    try:
        nodes = doc.xpath(node_xpath)
    except Exception:
        return None
    if not nodes:
        return None
    node = nodes[0]
    preview = " ".join(
        node.xpath(".//*[self::p or self::li]//text()[normalize-space()]")
    )
    preview = " ".join(preview.split())
    if len(preview) < 20:
        return None
    return {
        "field": "content",
        "mode": "xpath",
        "rule": "%s//*[self::p or self::li]//text()" % node_xpath,
        "preview": preview[:180],
        "reason": "这块区域包含较长正文段落，适合作为正文主容器。",
        "preview_xpath": node_xpath,
    }


def _element_text_candidate(doc, field, element_xpath, rule, reason):
    try:
        nodes = doc.xpath(element_xpath)
    except Exception:
        return None
    if not nodes:
        return None
    node = nodes[0]
    value = " ".join(node.xpath(".//text()[normalize-space()]")).strip()
    if not value:
        return None
    return {
        "field": field,
        "mode": "xpath",
        "rule": rule,
        "preview": value[:180],
        "reason": reason,
        "preview_xpath": _element_preview_xpath(node),
    }


def _value_xpath_candidate(doc, field, rule, reason, preview_xpath=None):
    try:
        values = doc.xpath(rule)
    except Exception:
        return None
    if not values:
        return None
    value = values[0]
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    return {
        "field": field,
        "mode": "xpath",
        "rule": rule,
        "preview": value[:180],
        "reason": reason,
        "preview_xpath": preview_xpath,
    }


def _specify_candidate(field, value, reason):
    value = (value or "").strip()
    if not value:
        return None
    return {
        "field": field,
        "mode": "specify",
        "value": value,
        "preview": value,
        "reason": reason,
        "preview_xpath": None,
    }


def _compact_candidates(candidates):
    deduped = []
    seen = set()
    for candidate in candidates:
        if candidate is None:
            continue
        signature = (candidate["mode"], candidate.get("rule"), candidate.get("value"))
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(candidate)
    return deduped[:3]


def _element_preview_xpath(node):
    return node.getroottree().getpath(node)
