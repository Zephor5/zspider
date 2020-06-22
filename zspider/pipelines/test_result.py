# coding=utf-8

__author__ = "zephor"


class TestResultPipeLine(object):
    @classmethod
    def from_crawler(cls, crawler):
        crawler.spider.test_result = []
        return cls()

    @staticmethod
    def process_item(item, spider):
        spider.test_result.append(item)
