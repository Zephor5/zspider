# coding=utf-8
import unittest
from unittest import mock

from zspider import auth


class TestAuth(unittest.TestCase):
    def test_hash_password_uses_bcrypt(self):
        password_hash = auth.hash_password("secret")

        self.assertTrue(auth.verify_password("secret", password_hash))

    def test_verify_password_rejects_non_bcrypt_hash(self):
        with self.assertRaises(ValueError):
            auth.verify_password("secret", "legacy-sha256-hash")


class TestLogin(unittest.TestCase):
    def setUp(self):
        from zspider.www.handlers import app

        self.client = app.test_client()

    @mock.patch("zspider.www.handlers.User")
    def test_login_accepts_bcrypt_password(self, user_model):
        user = mock.Mock(password=auth.hash_password("secret"), role="admin")
        user_model.objects.get.return_value = user

        response = self.client.post(
            "/login", data={"username": "admin", "password": "secret"}
        )

        self.assertEqual(response.status_code, 302)
        user.save.assert_not_called()

    @mock.patch("zspider.www.handlers.User")
    def test_login_rejects_invalid_password(self, user_model):
        user_model.objects.get.return_value = mock.Mock(
            password=auth.hash_password("secret"), role="admin"
        )

        response = self.client.post(
            "/login", data={"username": "admin", "password": "wrong"}
        )

        self.assertEqual(response.status_code, 403)

    @mock.patch("zspider.www.handlers.User")
    def test_login_rejects_non_bcrypt_password_hash(self, user_model):
        user_model.objects.get.return_value = mock.Mock(
            password="legacy-sha256-hash", role="admin"
        )

        response = self.client.post(
            "/login", data={"username": "admin", "password": "secret"}
        )

        self.assertEqual(response.status_code, 403)
