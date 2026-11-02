from unittest.mock import patch

from django.test import SimpleTestCase

from authentication.backends.ukey.backends import UKeyBackend
from authentication.backends.ukey.exceptions import UkeySNMismatchError
from users.models import User
from users.serializers.user import UserSerializer


class UserUKeyUnbindTests(SimpleTestCase):
    def setUp(self):
        self.user = User(username="ukey-test", ukey_sn="original-device")
        save = patch.object(self.user, "save")
        self.save = save.start()
        self.addCleanup(save.stop)

    def update_user(self, data):
        serializer = UserSerializer(self.user, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.save.assert_called_once()
        return serializer

    def test_explicit_null_clears_binding(self):
        serializer = self.update_user({"ukey_sn": None})
        self.assertIn("ukey_sn", serializer.validated_data)
        self.assertIsNone(self.user.ukey_sn)

    def test_omitted_serial_preserves_binding(self):
        serializer = self.update_user({"comment": "Updated profile"})
        self.assertNotIn("ukey_sn", serializer.validated_data)
        self.assertEqual(self.user.ukey_sn, "original-device")
        self.assertEqual(self.user.comment, "Updated profile")

    def test_blank_serial_clears_binding(self):
        for value in ("", "   "):
            with self.subTest(value=value):
                self.user.ukey_sn = "original-device"
                self.save.reset_mock()
                self.update_user({"ukey_sn": value})
                self.assertIsNone(self.user.ukey_sn)

    def test_unbinding_an_unbound_user_is_idempotent(self):
        self.user.ukey_sn = None
        self.update_user({"ukey_sn": None})
        self.assertIsNone(self.user.ukey_sn)

    @patch("rest_framework.validators.qs_exists", return_value=False)
    def test_new_serial_can_be_bound(self, exists):
        self.update_user({"ukey_sn": "new-device"})
        self.assertEqual(self.user.ukey_sn, "new-device")
        exists.assert_called_once()

    @patch("rest_framework.validators.qs_exists", return_value=True)
    def test_duplicate_serial_is_still_rejected(self, exists):
        serializer = UserSerializer(
            self.user, data={"ukey_sn": "another-users-device"}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["ukey_sn"][0].code, "unique")
        self.assertEqual(self.user.ukey_sn, "original-device")
        self.save.assert_not_called()
        exists.assert_called_once()

    def test_unbound_user_cannot_login_with_previous_device(self):
        self.update_user({"ukey_sn": None})
        with patch.object(User.objects, "filter") as users:
            users.return_value.first.return_value = self.user
            with self.assertRaises(UkeySNMismatchError):
                UKeyBackend()._check_user_and_ukey_sn(
                    self.user.username, "original-device"
                )
