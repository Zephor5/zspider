# coding=utf-8
import importlib
import os
import tempfile
from unittest import TestCase

from zspider import settings


class SettingsPathTest(TestCase):
    def test_data_path_points_to_package_data_directory(self):
        expected = os.path.join(settings.PACKAGE_PATH, "data")

        self.assertEqual(settings.DATA_PATH, expected)
        self.assertTrue(settings.DATA_PATH.endswith(os.path.join("zspider", "data")))

    def test_settings_load_dotenv_values_without_overriding_existing_env(self):
        env_keys = (
            "ZSPIDER_DOTENV_PATH",
            "ZSPIDER_LLM_API_KEY",
            "ZSPIDER_LLM_MODEL",
        )
        original = {key: os.environ.get(key) for key in env_keys}
        try:
            with tempfile.NamedTemporaryFile("w", delete=False) as handler:
                handler.write("ZSPIDER_LLM_API_KEY=file-key\n")
                handler.write("ZSPIDER_LLM_MODEL='file-model'\n")
                dotenv_path = handler.name

            os.environ["ZSPIDER_DOTENV_PATH"] = dotenv_path
            os.environ.pop("ZSPIDER_LLM_API_KEY", None)
            os.environ.pop("ZSPIDER_LLM_MODEL", None)

            reloaded = importlib.reload(settings)
            self.assertEqual("file-key", reloaded.LLM_API_KEY)
            self.assertEqual("file-model", reloaded.LLM_MODEL)

            os.environ["ZSPIDER_LLM_API_KEY"] = "env-key"
            reloaded = importlib.reload(settings)
            self.assertEqual("env-key", reloaded.LLM_API_KEY)
            self.assertEqual("file-model", reloaded.LLM_MODEL)
        finally:
            dotenv_path = locals().get("dotenv_path")
            if dotenv_path and os.path.exists(dotenv_path):
                os.unlink(dotenv_path)
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            importlib.reload(settings)
