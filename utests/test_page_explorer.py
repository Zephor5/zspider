# coding=utf-8
import unittest
from unittest import mock

from zspider.services import page_explorer


STATIC_HTML = """
<html>
  <head><title>News</title></head>
  <body>
    <div class="news-list">
      <article><a href="/2026/03/story-1.html">标题一</a></article>
      <article><a href="/2026/03/story-2.html">标题二</a></article>
      <article><a href="/2026/03/story-3.html">标题三</a></article>
    </div>
    <div><a href="/about">关于我们</a></div>
  </body>
</html>
"""


DYNAMIC_HTML = """
<html>
  <head>
    <title>App</title>
    <script src="/static/app.js"></script>
    <script src="/static/chunk-a.js"></script>
    <script src="/static/chunk-b.js"></script>
    <script src="/static/chunk-c.js"></script>
    <script src="/static/chunk-d.js"></script>
  </head>
  <body>
    <div id="app"></div>
  </body>
</html>
"""


ARTICLE_HTML = """
<html>
  <head>
    <title>文章页</title>
    <meta property="og:site_name" content="示例站点" />
  </head>
  <body>
    <article>
      <h1>文章标题</h1>
      <time datetime="2026-03-17T10:00:00">2026-03-17</time>
      <p>第一段正文，包含较长内容。</p>
      <p>第二段正文，继续描述更多信息。</p>
    </article>
  </body>
</html>
"""


SINA_INDEX_HTML = """
<html>
  <body>
    <div id="j_cardlist">
      <div class="ty-card ty-card-type1 clearfix">
        <div class="ty-card-r">
          <h3><a href="/zonghe/2026-03-17/doc-a.shtml">标题一</a></h3>
          <p><a href="http://comment5.news.sina.com.cn/a">评论</a></p>
        </div>
      </div>
      <div class="ty-card ty-card-type1 clearfix">
        <div class="ty-card-r">
          <h3><a href="/zonghe/2026-03-17/doc-b.shtml">标题二</a></h3>
          <p><a href="http://comment5.news.sina.com.cn/b">评论</a></p>
        </div>
      </div>
    </div>
  </body>
</html>
"""


SINA_ARTICLE_HTML = """
<html>
  <head>
    <title>真实标题_新浪军事_新浪新闻</title>
    <meta property="og:title" content="真实标题" />
  </head>
  <body>
    <div class="path"><h1 class="channel-logo">新浪军事</h1></div>
    <div class="article-header">
      <h1 class="main-title">真实标题</h1>
    </div>
    <div id="article" class="article">
      <p>正文第一段。</p>
      <p>正文第二段。</p>
    </div>
  </body>
</html>
"""


class TestPageExplorer(unittest.TestCase):
    def tearDown(self):
        page_explorer._ARTICLE_CONTEXT_CACHE.clear()

    @mock.patch("zspider.services.page_explorer._fetch_browser_html")
    @mock.patch("zspider.services.page_explorer._fetch_html")
    def test_explore_index_page_returns_static_candidate(
        self, fetch_html, fetch_browser_html
    ):
        fetch_html.return_value = ("https://example.com/news/", STATIC_HTML)
        fetch_browser_html.return_value = STATIC_HTML

        result = page_explorer.explore_index_page("https://example.com/news/")

        self.assertEqual("直接抓取", result["fetch_mode"]["label"])
        self.assertEqual("news", result["fetch_mode"]["recommended_spider"])
        self.assertEqual("News", result["suggested_task_name"])
        self.assertTrue(result["candidates"])
        self.assertLessEqual(len(result["candidates"][0]["xpath"]), 128)
        self.assertEqual(
            "https://example.com/2026/03/story-1.html", result["primary_article_url"]
        )
        self.assertIn("//a[@href]/@href", result["candidates"][0]["xpath"])
        self.assertIn("data-explore-hit", result["preview_html"])
        self.assertIn("preview-shell", result["preview_html"])
        self.assertIn("postMessage", result["preview_html"])
        self.assertIn("highlight-xpaths", result["preview_html"])
        self.assertIn("region_link_xpath", result["preview_html"])
        self.assertIn("页面结构基本一致", result["fetch_mode"]["reason"])

    @mock.patch("zspider.services.page_explorer._fetch_browser_html")
    @mock.patch("zspider.services.page_explorer._fetch_html")
    def test_explore_index_page_detects_dynamic_shell(
        self, fetch_html, fetch_browser_html
    ):
        fetch_html.return_value = ("https://example.com/app", DYNAMIC_HTML)
        fetch_browser_html.return_value = """
        <html>
          <head><title>动态新闻列表</title></head>
          <body>
            <div id="app">
              <div class="news-list">
                <article><a href="/news/1">标题一</a></article>
                <article><a href="/news/2">标题二</a></article>
                <article><a href="/news/3">标题三</a></article>
              </div>
            </div>
          </body>
        </html>
        """

        result = page_explorer.explore_index_page("https://example.com/app")

        self.assertEqual("浏览器渲染", result["fetch_mode"]["label"])
        self.assertEqual("browser", result["fetch_mode"]["recommended_spider"])
        self.assertIn("页面结构差异明显", result["fetch_mode"]["reason"])
        self.assertEqual("动态新闻列表", result["title"])
        self.assertEqual("动态新闻列表", result["suggested_task_name"])
        self.assertEqual("https://example.com/news/1", result["primary_article_url"])
        self.assertIn("标题一", result["preview_html"])

    def test_explore_index_page_requires_url(self):
        with self.assertRaises(ValueError):
            page_explorer.explore_index_page("")

    @mock.patch("zspider.services.page_explorer._fetch_browser_html")
    @mock.patch("zspider.services.page_explorer._fetch_html")
    def test_explore_article_page_returns_field_candidates(
        self, fetch_html, fetch_browser_html
    ):
        fetch_html.return_value = ("https://example.com/news/1", ARTICLE_HTML)
        fetch_browser_html.return_value = ARTICLE_HTML

        result = page_explorer.explore_article_page("https://example.com/news/1")

        self.assertIn("h1", result["field_candidates"]["title"][0]["rule"])
        self.assertIn("//article", result["field_candidates"]["content"][0]["rule"])
        self.assertEqual(
            "//time[@datetime][1]/@datetime",
            result["field_candidates"]["src_time"][0]["rule"],
        )
        self.assertEqual("示例站点", result["field_candidates"]["source"][0]["value"])
        self.assertEqual("ready", result["coverage"]["title"]["status"])
        self.assertEqual("ready", result["coverage"]["source"]["status"])
        self.assertIn("data-explore-hit", result["preview_html"])
        self.assertIn("data-explore-selected", result["preview_html"])
        self.assertIn("highlight-xpaths", result["preview_html"])
        self.assertIn("focused_text_xpath", result["preview_html"])
        self.assertIn("selection_quality", result["preview_html"])
        self.assertEqual("直接抓取", result["fetch_mode"]["label"])
        cached = page_explorer.get_cached_article_context("https://example.com/news/1")
        self.assertEqual("https://example.com/news/1", cached["final_url"])
        self.assertIn("<article>", cached["rendered_html"])

    @mock.patch("zspider.services.page_explorer._fetch_browser_html")
    @mock.patch("zspider.services.page_explorer._fetch_html")
    def test_explore_index_page_shortens_long_candidate_xpath(
        self, fetch_html, fetch_browser_html
    ):
        fetch_html.return_value = (
            "https://example.com/news/",
            """
            <html><body>
            <div class="animate-fade-up stagger-2">
              <div class="grid gap-px max-w-6xl">
                <article><a href="/news/1">标题一</a></article>
                <article><a href="/news/2">标题二</a></article>
              </div>
            </div>
            </body></html>
            """,
        )
        fetch_browser_html.return_value = fetch_html.return_value[1]

        result = page_explorer.explore_index_page("https://example.com/news/")

        self.assertTrue(result["candidates"])
        self.assertLessEqual(len(result["candidates"][0]["xpath"]), 128)

    @mock.patch("zspider.services.page_explorer._fetch_browser_html")
    @mock.patch("zspider.services.page_explorer._fetch_html")
    def test_explore_index_page_falls_back_when_browser_compare_unavailable(
        self, fetch_html, fetch_browser_html
    ):
        fetch_html.return_value = ("https://example.com/app", DYNAMIC_HTML)
        fetch_browser_html.side_effect = RuntimeError("playwright missing")

        result = page_explorer.explore_index_page("https://example.com/app")

        self.assertEqual("浏览器渲染", result["fetch_mode"]["label"])
        self.assertIn("优先尝试浏览器渲染", result["fetch_mode"]["reason"])

    @mock.patch("zspider.services.page_explorer._fetch_browser_html")
    @mock.patch("zspider.services.page_explorer._fetch_html")
    def test_explore_index_page_prefers_heading_article_links(
        self, fetch_html, fetch_browser_html
    ):
        fetch_html.return_value = ("https://mil.news.sina.com.cn/", SINA_INDEX_HTML)
        fetch_browser_html.return_value = SINA_INDEX_HTML

        result = page_explorer.explore_index_page("https://mil.news.sina.com.cn/")

        self.assertTrue(result["candidates"])
        self.assertEqual("新浪军事", result["suggested_task_name"])
        self.assertIn(
            "self::h1 or self::h2 or self::h3 or self::h4",
            result["candidates"][0]["xpath"],
        )
        self.assertEqual(
            [
                "https://mil.news.sina.com.cn/zonghe/2026-03-17/doc-a.shtml",
                "https://mil.news.sina.com.cn/zonghe/2026-03-17/doc-b.shtml",
            ],
            result["candidates"][0]["sample_urls"][:2],
        )

    @mock.patch("zspider.services.page_explorer._fetch_browser_html")
    @mock.patch("zspider.services.page_explorer._fetch_html")
    def test_explore_article_page_prefers_main_title_h1(
        self, fetch_html, fetch_browser_html
    ):
        fetch_html.return_value = (
            "https://mil.news.sina.com.cn/zonghe/2026-03-17/doc-a.shtml",
            SINA_ARTICLE_HTML,
        )
        fetch_browser_html.return_value = SINA_ARTICLE_HTML

        result = page_explorer.explore_article_page(
            "https://mil.news.sina.com.cn/zonghe/2026-03-17/doc-a.shtml"
        )

        self.assertEqual("真实标题", result["field_candidates"]["title"][0]["preview"])
        self.assertNotIn("新浪军事", result["field_candidates"]["title"][0]["preview"])

    def test_suggest_task_name_prefers_site_channel_over_noisy_title(self):
        doc = page_explorer._parse_html(
            "<html><head><title>icon关闭</title></head><body></body></html>",
            "https://mil.news.sina.com.cn/",
        )

        result = page_explorer._suggest_task_name(doc, "https://mil.news.sina.com.cn/")

        self.assertEqual("新浪军事", result)

    @mock.patch("zspider.services.page_explorer._fetch_browser_html")
    @mock.patch("zspider.services.page_explorer._fetch_html")
    def test_infer_index_xpath_returns_candidate_from_selected_urls(
        self, fetch_html, fetch_browser_html
    ):
        fetch_html.return_value = ("https://mil.news.sina.com.cn/", SINA_INDEX_HTML)
        fetch_browser_html.return_value = SINA_INDEX_HTML

        result = page_explorer.infer_index_xpath(
            "https://mil.news.sina.com.cn/",
            [
                "https://mil.news.sina.com.cn/zonghe/2026-03-17/doc-a.shtml",
                "https://mil.news.sina.com.cn/zonghe/2026-03-17/doc-b.shtml",
            ],
        )

        self.assertEqual("直接抓取", result["fetch_mode"]["label"])
        self.assertIn("candidate", result)
        self.assertIn("@href", result["candidate"]["xpath"])
        self.assertEqual(2, result["candidate"]["count"])

    def test_infer_index_xpath_requires_multiple_urls(self):
        with self.assertRaises(ValueError):
            page_explorer.infer_index_xpath(
                "https://mil.news.sina.com.cn/",
                ["https://mil.news.sina.com.cn/zonghe/2026-03-17/doc-a.shtml"],
            )
