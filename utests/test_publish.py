# coding=utf-8
import unittest

from zspider.utils.transform import SafeTransformEvaluator


class TestSafeTransformEvaluator(unittest.TestCase):
    def test_updates_doc_with_supported_expression(self):
        doc = {"title": " hello "}

        SafeTransformEvaluator.execute(
            "doc.update({'title': doc['title'].strip()})", doc
        )

        self.assertEqual(doc["title"], "hello")

    def test_supports_filter_expression(self):
        doc = {}

        SafeTransformEvaluator.execute(
            "not doc.get('trash') and doc.update({'published': 1})", doc
        )

        self.assertEqual(doc["published"], 1)

    def test_rejects_unsafe_expression(self):
        with self.assertRaises(Exception):
            SafeTransformEvaluator.execute("__import__('os').system('id')", {})
