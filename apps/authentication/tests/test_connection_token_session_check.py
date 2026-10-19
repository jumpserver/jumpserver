from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from assets.models import Asset
from authentication.api.connection_token import SuperConnectionTokenViewSet
from authentication.models import AdminConnectionToken, ConnectionToken
from users.models import User


class ConnectionTokenSessionCheckTests(SimpleTestCase):
    def token(self, model=ConnectionToken):
        now = timezone.now()
        token = model(
            user=User(username='admin', date_expired=now + timezone.timedelta(days=1)),
            asset=Asset(name='windows', is_active=True), account='administrator',
            protocol='winrm', connect_method='web_cli',
            date_created=now - timezone.timedelta(minutes=2),
            date_expired=now - timezone.timedelta(seconds=1),
        )
        token.get_permed_account = Mock(return_value=SimpleNamespace(
            actions=1, date_expired=now + timezone.timedelta(days=1),
        ))
        return token

    def check(self, token):
        view = SuperConnectionTokenViewSet()
        view.get_object = lambda: token
        view._validate_perm = Mock()
        return view.check(None), view

    @patch('acls.models.ConnectMethodACL.is_method_allowed', return_value=True)
    def test_consumed_token_keeps_session_checks_but_cannot_reconnect(self, _):
        for model in (ConnectionToken, AdminConnectionToken):
            with self.subTest(model=model.__name__):
                token = self.token(model)
                response, view = self.check(token)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['code'], 'perm_ok')
                self.assertTrue(response.data['expired'])
                view._validate_perm.assert_called_once_with(
                    token.user, token.asset, token.account, token.protocol,
                    token_type=token.type,
                )
                with self.assertRaises(PermissionDenied):
                    token.is_valid(include_personal_secret=True)

    @patch('acls.models.ConnectMethodACL.is_method_allowed', return_value=True)
    def test_revoked_account_permission_still_invalidates_session(self, _):
        token = self.token()
        token.get_permed_account.return_value = None
        response, _ = self.check(token)
        self.assertEqual(response.status_code, 400)
        token.get_permed_account.assert_called_once()

    @patch('acls.models.ConnectMethodACL.is_method_allowed', return_value=False)
    def test_connect_method_acl_still_invalidates_session(self, acl):
        response, _ = self.check(self.token())
        self.assertEqual(response.status_code, 400)
        acl.assert_called_once()
