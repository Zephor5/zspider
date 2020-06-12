# coding=utf-8

__author__ = "zephor"


PARSERS = {}


class BaseParser(object):
    def __init__(self, name):
        self.name = name


def _init():
    import os
    from zspider.utils.python import iter_sub_classes
    from zspider.utils.errors import DupParserNames

    __file_root = os.path.dirname(os.path.abspath(__file__))
    for _, __, _fs in os.walk(__file_root):
        for m in _fs:
            if m.endswith(".py") and not (m.startswith("_") or m.startswith("base")):
                mod = __import__(
                    "zspider.parsers.%s" % os.path.splitext(m)[0], fromlist=[""]
                )
                for o in iter_sub_classes(mod, BaseParser):
                    if o.__name__ in PARSERS:
                        raise DupParserNames("the name of parser conflict")
                    else:
                        PARSERS[o.__name__] = o


if not PARSERS:
    _init()


def get_parser(parser, task_id, task_name, task_conf=None, article_fields=None):

    return PARSERS[parser](task_id, task_name, task_conf, article_fields)
