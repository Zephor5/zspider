# coding=utf-8
import re
from wtforms import fields, ValidationError
from . import engine

__author__ = 'zephor'


class BaseValidateField(engine.StringField):

    def __init__(self, extra_validator=None, **kwargs):
        assert extra_validator is None or callable(extra_validator), 'extra_validator must be None or callable'
        self.extra_validator = extra_validator
        super(BaseValidateField, self).__init__(**kwargs)

    def to_form_field(self, model, kwargs):
        # compatible with flask-mongoengine model_form

        kwargs['validators'].append(self.form_validate)
        return fields.StringField(**kwargs)

    def form_validate(self, form, field):
        try:
            self.validate(field.data)
            if self.extra_validator is not None:
                self.extra_validator(form, field)
        except AssertionError as e:
            raise ValidationError(e)


class RegExpField(BaseValidateField):

    def __init__(self, group_num=None, group_names=None, **kwargs):
        assert group_num is None or (isinstance(group_num, int) and group_num >= 0)
        assert group_names is None or isinstance(group_names, (tuple, list, set)), 'group_names must be None or set'
        self.group_num = group_num
        self.group_names = group_names
        kwargs.setdefault('max_length', 64)
        super(RegExpField, self).__init__(**kwargs)

    def validate(self, value):
        super(RegExpField, self).validate(value)
        import re
        try:
            r = re.compile(value)
        except re.error:
            self.error('Invalid python re compatible regular expression')
        else:
            if self.group_num is not None:
                assert r.groups == self.group_num, 'Invalid group number in re'
            if self.group_names is not None:
                for name in self.group_names:
                    assert name in r.groupindex, 'Missing group index: %s' % name


class XPathField(BaseValidateField):

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 64)
        super(XPathField, self).__init__(**kwargs)

    def validate(self, value):
        super(XPathField, self).validate(value)
        from lxml import etree
        try:
            etree.XPath(value)
        except etree.XPathSyntaxError:
            self.error('Invalid xpath expression')


class CronField(BaseValidateField):

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 64)
        super(CronField, self).__init__(**kwargs)

    def validate(self, value):
        super(CronField, self).validate(value)
        self.validate_cron(value)

    @staticmethod
    def validate_cron(value):
        dfs = value.split(' ')
        assert len(dfs) == 5, 'cron expr must be 5 fields separated by a blank'
        re_p = re.compile(r'^(?:\*|(\d+)-(\d+))(?:/(\d+))?$|^(\d+)$')
        limits = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
        for i, f in enumerate(dfs):
            assert f, 'Invalid cron expression'
            for p in f.split(','):
                res = re_p.match(p)
                assert res, 'Invalid cron expression'
                nums = res.groups()
                for j, num in enumerate(nums):
                    if num is not None:
                        assert limits[i][0] <= int(num) <= limits[i][1], 'Invalid num in cron expression'
                        if j == 2:
                            assert int(num), 'Invalid num in cron expression'
                if nums[0] is not None:
                    assert int(nums[0]) < int(nums[1]), 'Invalid num period in cron expression'
                    if nums[2] is not None:
                        assert int(nums[2]) <= int(nums[1]) - int(nums[0]), 'Invalid divide num in cron expression'


class IpField(BaseValidateField):

    def __init__(self, **kwargs):
        kwargs.setdefault('regex', r'^((\d|[1-9]\d|1\d{2}|2[0-4]\d|25[0-5])\.){3}(\d|[1-9]\d|1\d{2}|2[0-4]\d|25[0-5])$')
        super(IpField, self).__init__(**kwargs)


class BaseDocument(engine.Document):

    meta = {'abstract': True}

    def save(self, **kwargs):
        kwargs.setdefault('validate', False)
        super(BaseDocument, self).save(**kwargs)


class BaseTaskConf(BaseDocument):

    meta = {'abstract': True}

    login_data = engine.DictField(verbose_name=u'登录数据',
                                  help_text=u'抓取网页登录数据dict，注意使用英文双引号，若无需登录则为空')
    to_login = engine.URLField(verbose_name=u'登录页', help_text=u'登陆页面，若无需登录则为空')
    front_url = engine.URLField(required=True, verbose_name=u'入口url',
                                help_text=u'索引列表页，支持一些python式预定义参数，如：%(year)s，包括:year,month,day')
