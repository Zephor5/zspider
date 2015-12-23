# coding=utf-8
import json

from utils import engine, fields_models as fm
from .baseparser import BaseNewsParser

__author__ = 'zephor'


class TaskConfJSONParser(fm.BaseTaskConf):
    pre_boundary = engine.StringField(verbose_name=u'前边界')
    suf_boundary = engine.StringField(verbose_name=u'后边界')
    json_struct = engine.StringField(required=True, regex='^([\[\]\w\d-]+?->)*[\[\]\w\d-]+$', verbose_name=u'索引结构',
                                     help_text=u'例如内容{"items":[{"url":"http://example"}]}，'
                                               u'则结构为：items->[]->url或items->[0]->url')


class JSONParser(BaseNewsParser):

    CONF = TaskConfJSONParser

    def parse_index(self, response):
        body = response.body
        p_i, s_i = None, None
        if self._conf.pre_boundary:
            _l = len(self._conf.pre_boundary)
            p_i = body.find(self._conf.pre_boundary)
            p_i = p_i + _l if p_i > -1 else None
        if self._conf.suf_boundary:
            s_i = body.rfind(self._conf.suf_boundary)
            s_i = s_i if s_i > -1 else None
        data = json.loads(body[p_i:s_i])

        structs = self._conf.json_struct.split('->')

        lists = []

        def gen_lists(_data, _structs):
            while _structs:
                _p = _structs.pop(0)
                if _p.startswith('[') and _p.endswith(']'):
                    _p = _p[1:-1]
                    if _p:
                        _data = _data[int(_p)]
                    else:
                        lists.append((_data, 0, list(_structs)))
                        _data = _data[0]
                else:
                    _data = _data[_p]
            return _data

        data = gen_lists(data, structs)

        if not lists:
            yield data

        while lists:
            for i in xrange(len(lists)):
                if i == 0:
                    _list, _, structs = lists.pop(-1)
                    for data in _list:
                        for p in structs:
                            data = data[p]
                        yield data
                else:
                    _list, j, structs = lists.pop(-1)
                    if j+1 < len(_list):
                        lists.append((_list, j+1, structs))
                        gen_lists(_list[j+1], structs)
                        break

    def parse_article(self, response):
        return self._parse_article_field(response)
