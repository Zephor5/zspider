# coding=utf-8
import mock
import unittest

from mongoengine import ValidationError
from utils import fields_models as fm
from zspider.models import PubSubscribe

__author__ = 'zephor'


class TestFieldsModels(unittest.TestCase):

    # noinspection PyUnresolvedReferences
    @mock.patch.multiple('mongoengine.document.Document', _get_collection=mock.DEFAULT, validate=mock.DEFAULT)
    def test_base_document(self, _get_collection, validate):
        class D(fm.BaseDocument):
            pass

        d = D()
        _conn = mock.Mock()
        _conn.save.return_value = 'test'
        _get_collection.return_value = _conn
        d.save()

        self.assertFalse(validate.called, "validate shouldn't be called")
        self.assertEqual(len(_get_collection.mock_calls), 3)
        self.assertEqual(d.id, 'test')

    def test_base_task_conf(self):
        class T(fm.BaseTaskConf):
            pass
        bad_tests = (
            dict(),
            dict(front_url='http:/www.baidu.com'),
            dict(login_data=(), to_login='http://www.example.com/login', front_url='http://www.example.com')
        )
        for p in bad_tests:
            t = T(**p)
            try:
                self.assertRaises(ValidationError, t.validate)
            except self.failureException as e:
                message = '{0} with {1}'.format(e, p)
                raise self.failureException(message)

        good_tests = (
            dict(front_url='http://www.baidu.com'),
            dict(login_data={}, to_login='http://www.example.com/login', front_url='http://www.example.com')
        )
        for p in good_tests:
            t = T(**p)
            self.assertIsNone(t.validate())


class TestPubSubscribe(unittest.TestCase):

    # noinspection PyUnresolvedReferences
    @mock.patch.multiple('mongoengine.document.Document', _get_collection=mock.DEFAULT, validate=mock.DEFAULT)
    def test_type(self, _get_collection, validate):

        ps = PubSubscribe(cids='1')
        _conn = mock.Mock()
        _conn.save.return_value = 'test'
        _get_collection.return_value = _conn
        ps.save()
