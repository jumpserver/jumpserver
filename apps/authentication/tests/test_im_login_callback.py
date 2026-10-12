from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase

from authentication.views.base import BaseLoginCallbackView


class DummyLoginCallbackView(BaseLoginCallbackView):
    user_type = 'slack'
    msg_client_err = 'Slack error'
    msg_user_not_bound_err = 'Slack is not bound'

    @property
    def client(self):
        return self._client


class IMLoginCallbackUserCreationTests(SimpleTestCase):
    def setUp(self):
        self.view = DummyLoginCallbackView()
        self.view._client = Mock()
        self.view._client.get_user_detail.return_value = {
            'username': 'alice',
            'name': 'Alice',
            'email': 'alice@example.com',
        }
        self.view.request = SimpleNamespace(error_message='Creation is disabled')

    @patch('authentication.views.base.bind_user_to_org_role')
    @patch('authentication.views.base.check_only_allow_exist_user_auth')
    @patch('authentication.views.base.User')
    def test_existing_username_is_not_implicitly_bound(self, user_model, check, bind):
        user_model.objects.filter.return_value.exists.return_value = True

        user, error = self.view.create_user_if_not_exist('U_ATTACKER')

        self.assertIsNone(user)
        self.assertEqual(error[0], 'Slack is not bound')
        user_model.objects.create.assert_not_called()
        check.assert_not_called()
        bind.assert_not_called()

    @patch('authentication.views.base.bind_user_to_org_role')
    @patch('authentication.views.base.check_only_allow_exist_user_auth', return_value=True)
    @patch('authentication.views.base.User')
    def test_new_external_user_is_created_with_its_provider_id(self, user_model, check, bind):
        created_user = SimpleNamespace(username='alice')
        user_model.objects.filter.return_value.exists.return_value = False
        user_model.objects.create.return_value = created_user

        user, error = self.view.create_user_if_not_exist('U_NEW')

        self.assertIs(user, created_user)
        self.assertIsNone(error)
        user_model.objects.create.assert_called_once_with(
            username='alice',
            name='Alice',
            email='alice@example.com',
            slack_id='U_NEW',
            source='slack',
        )
        check.assert_called_once_with(True)
        bind.assert_called_once_with(created_user)

    @patch('authentication.views.base.bind_user_to_org_role')
    @patch('authentication.views.base.check_only_allow_exist_user_auth', return_value=False)
    @patch('authentication.views.base.User')
    def test_auto_creation_policy_is_enforced(self, user_model, check, bind):
        user_model.objects.filter.return_value.exists.return_value = False

        user, error = self.view.create_user_if_not_exist('U_NEW')

        self.assertIsNone(user)
        self.assertEqual(error, ('Slack error', 'Creation is disabled'))
        user_model.objects.create.assert_not_called()
        check.assert_called_once_with(True)
        bind.assert_not_called()

    @patch('authentication.views.base.bind_user_to_org_role')
    @patch('authentication.views.base.check_only_allow_exist_user_auth', return_value=True)
    @patch('authentication.views.base.User')
    def test_concurrent_username_collision_fails_closed(self, user_model, check, bind):
        user_model.objects.filter.return_value.exists.return_value = False
        user_model.objects.create.side_effect = IntegrityError('duplicate username')

        user, error = self.view.create_user_if_not_exist('U_NEW')

        self.assertIsNone(user)
        self.assertEqual(error[0], 'Slack error')
        bind.assert_not_called()
