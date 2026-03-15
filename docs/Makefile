# Minimal Sphinx makefile aligned with the current bilingual docs layout.

SPHINXPYTHON ?= python3
SPHINXBUILD ?= $(SPHINXPYTHON) -m sphinx
SPHINXOPTS ?=
BUILDDIR ?= _build
SOURCEDIR := .

LOCAL_SPHINX_SITEPKG := $(firstword \
	$(wildcard ../.venv/lib/python*/site-packages) \
	$(wildcard ../venv/lib/python*/site-packages))

ifneq ($(LOCAL_SPHINX_SITEPKG),)
export PYTHONPATH := $(LOCAL_SPHINX_SITEPKG)$(if $(PYTHONPATH),:$(PYTHONPATH),)
endif

.PHONY: help clean html dirhtml singlehtml epub latex text man linkcheck doctest coverage

help:
	@echo "make <target>"
	@echo
	@echo "Common targets:"
	@echo "  html       Build standalone HTML documentation"
	@echo "  dirhtml    Build directory-style HTML documentation"
	@echo "  singlehtml Build a single HTML page"
	@echo "  epub       Build EPUB output"
	@echo "  latex      Build LaTeX sources"
	@echo "  text       Build plain text output"
	@echo "  man        Build man pages"
	@echo "  linkcheck  Check external links"
	@echo "  doctest    Run doctests embedded in docs"
	@echo "  coverage   Run Sphinx coverage checks"
	@echo "  clean      Remove generated documentation"
	@echo
	@echo "Overrides:"
	@echo "  SPHINXPYTHON=$(SPHINXPYTHON)"
	@echo "  SPHINXBUILD=$(SPHINXBUILD)"
	@echo "  PYTHONPATH=$(PYTHONPATH)"

clean:
	rm -rf $(BUILDDIR)

html:
	$(SPHINXBUILD) -b html $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/html

dirhtml:
	$(SPHINXBUILD) -b dirhtml $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/dirhtml

singlehtml:
	$(SPHINXBUILD) -b singlehtml $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/singlehtml

epub:
	$(SPHINXBUILD) -b epub $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/epub

latex:
	$(SPHINXBUILD) -b latex $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/latex

text:
	$(SPHINXBUILD) -b text $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/text

man:
	$(SPHINXBUILD) -b man $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/man

linkcheck:
	$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/linkcheck

doctest:
	$(SPHINXBUILD) -b doctest $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/doctest

coverage:
	$(SPHINXBUILD) -b coverage $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/coverage
