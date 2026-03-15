# coding=utf-8
import argparse
import unittest
from unittest import mock

from zspider import auth
from zspider import bootstrap_admin


class TestBootstrapAdmin(unittest.TestCase):
    @mock.patch("zspider.init.init")
    @mock.patch("zspider.bootstrap_admin.parse_args")
    @mock.patch("zspider.bootstrap_admin.User")
    def test_main_creates_admin_with_bcrypt_password(
        self, user_model, parse_args, init_app
    ):
        parse_args.return_value = argparse.Namespace(
            username="admin", password="secret", update_password=False
        )
        user_model.objects.return_value.first.return_value = None

        with mock.patch("zspider.init.done", True):
            bootstrap_admin.main()

        user_model.assert_called_once()
        kwargs = user_model.call_args.kwargs
        self.assertEqual(kwargs["username"], "admin")
        self.assertEqual(kwargs["role"], "admin")
        self.assertTrue(auth.verify_password("secret", kwargs["password"]))
        user_model.return_value.save.assert_called_once_with()
        init_app.assert_called_once_with("web")

    @mock.patch("zspider.init.init")
    @mock.patch("zspider.bootstrap_admin.parse_args")
    def test_main_updates_existing_admin_password(self, parse_args, init_app):
        parse_args.return_value = argparse.Namespace(
            username="admin", password="secret", update_password=True
        )
        user = mock.Mock(role="user", password=auth.hash_password("old"))

        with mock.patch("zspider.bootstrap_admin.User.objects") as user_objects:
            user_objects.return_value.first.return_value = user
            with mock.patch("zspider.init.done", True):
                bootstrap_admin.main()

        self.assertEqual(user.role, "admin")
        self.assertTrue(auth.verify_password("secret", user.password))
        user.save.assert_called_once_with()
        init_app.assert_called_once_with("web")
