# coding=utf-8
import os
from unittest import TestCase

from zspider import settings


class SettingsPathTest(TestCase):
    def test_data_path_points_to_package_data_directory(self):
        expected = os.path.join(settings.PACKAGE_PATH, "data")

        self.assertEqual(settings.DATA_PATH, expected)
        self.assertTrue(settings.DATA_PATH.endswith(os.path.join("zspider", "data")))
