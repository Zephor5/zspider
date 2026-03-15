# -*- coding: utf-8 -*-
"""Sphinx configuration for the ZSpider documentation."""

from datetime import datetime


project = "ZSpider"
author = "Zephor Wu"
copyright = f"2015-{datetime.now().year}, {author}"
version = "1.0"
release = "1.0.0"

master_doc = "index"
source_suffix = ".rst"
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
html_static_path = []
todo_include_todos = True
pygments_style = "sphinx"

html_theme = "alabaster"
html_title = f"{project} Documentation"
html_short_title = project
html_show_sourcelink = False
html_last_updated_fmt = "%Y-%m-%d"
html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
    ]
}
html_theme_options = {
    "description": "Self-hosted crawling platform documentation",
    "fixed_sidebar": True,
    "page_width": "1140px",
    "sidebar_width": "260px",
}

htmlhelp_basename = "zspiderdoc"

latex_elements = {}
latex_documents = [
    (master_doc, "zspider.tex", "ZSpider Documentation", author, "manual"),
]

man_pages = [(master_doc, "zspider", "ZSpider Documentation", [author], 1)]

texinfo_documents = [
    (
        master_doc,
        "zspider",
        "ZSpider Documentation",
        author,
        "zspider",
        "Self-hosted crawling platform documentation.",
        "Miscellaneous",
    ),
]
