# coding=utf-8
import unittest
from unittest import mock

from mongoengine import ValidationError

from zspider.models import PubSubscribe
from zspider.utils import fields_models as fm

__author__ = "zephor"


class TestFieldsModels(unittest.TestCase):
    @mock.patch("mongoengine.document.Document.save")
    def test_base_document(self, document_save):
        class D(fm.BaseDocument):
            pass

        d = D()
        d.save()

        self.assertTrue(document_save.called)
        self.assertEqual(document_save.call_args.kwargs.get("validate"), False)

    def test_base_task_conf(self):
        class T(fm.BaseTaskConf):
            pass

        bad_tests = (
            dict(),
            dict(front_url="http:/www.baidu.com"),
            dict(
                login_data=(),
                to_login="http://www.example.com/login",
                front_url="http://www.example.com",
            ),
        )
        for p in bad_tests:
            t = T(**p)
            try:
                self.assertRaises(ValidationError, t.validate)
            except self.failureException as e:
                message = "{0} with {1}".format(e, p)
                raise self.failureException(message)

        good_tests = (
            dict(front_url="http://www.baidu.com"),
            dict(
                login_data={},
                to_login="http://www.example.com/login",
                front_url="http://www.example.com",
            ),
        )
        for p in good_tests:
            t = T(**p)
            self.assertIsNone(t.validate())

    def test_cron_field_validate_cron(self):
        good = (
            "*/5 * * * *",
            "0 9 * * 1-5",
            "1,5,10 0 1 1 0",
            "1-10/2 * * * *",
        )
        for expr in good:
            fm.CronField.validate_cron(expr)

        bad = (
            "",
            "* * * *",
            "60 * * * *",
            "* 24 * * *",
            "10-1 * * * *",
            "1-10/20 * * * *",
            "abc * * * *",
        )
        for expr in bad:
            with self.assertRaises(AssertionError, msg=expr):
                fm.CronField.validate_cron(expr)

    def test_regexp_field_validate(self):
        field = fm.RegExpField(group_num=1, group_names=("id",))
        field.validate(r"(?P<id>\\d+)")

        with self.assertRaises(AssertionError):
            field.validate(r"(\\d+)-(\\w+)")

    def test_xpath_field_validate(self):
        fm.XPathField().validate("//div[@class='content']/text()")
        with self.assertRaises(AssertionError):
            fm.XPathField().validate("//div[")

    def test_xpath_and_regexp_field_default_lengths_are_large_enough(self):
        self.assertEqual(512, fm.XPathField().max_length)
        self.assertEqual(512, fm.RegExpField().max_length)


class TestPubSubscribe(unittest.TestCase):
    @mock.patch("mongoengine.document.Document.save")
    def test_type(self, document_save):
        ps = PubSubscribe(cids="1", model_id="model1")
        ps.save()

        self.assertTrue(document_save.called)
        self.assertEqual(document_save.call_args.kwargs.get("validate"), False)
