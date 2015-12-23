# coding=utf-8
import unittest

from zspider.parsers import get_parser

__author__ = 'zephor'


class TestNewspaper(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from www.handlers import app
        import utils
        utils.engine.init_app(app)
        parser = get_parser('5624a883bada213cd9c4e3ac', 'test', 'Newspaper')

    def test_init(self):
        pass
