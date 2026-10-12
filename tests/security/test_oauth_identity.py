import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from source_boundary import load

Base = type('Base', (), {})
users = Mock()
bind = Mock()
ns = load('apps/authentication/views/base.py', ['BaseLoginCallbackView'], {
    'AuthMixin': type('AuthMixin', (), {}), 'FlashMessageMixin': type('FlashMessageMixin', (), {}),
    'IMClientMixin': type('IMClientMixin', (), {}), 'View': Base,
    '_': lambda s: s, 'User': users, 'Request': object,
    'post_save_next_to_session_if_guard_redirect': lambda f: f,
    'check_only_allow_exist_user_auth': lambda created: True,
    'bind_user_to_org_role': bind, 'ValidationError': ValidationError,
    'IntegrityError': IntegrityError, 'logger': Mock(),
})


class OAuthIdentity(unittest.TestCase):
    def test_existing_username_cannot_be_bound_by_collision(self):
        for identity in ['', None, 'another-identity']:
            user = SimpleNamespace(wecom_id=identity, save=Mock())
            users.objects.get_or_create.return_value = user, False
            view = ns['BaseLoginCallbackView']()
            view.user_type = 'wecom'
            view.client = Mock(get_user_detail=Mock(return_value={'username': 'victim'}))
            result, error = view.create_user_if_not_exist('attacker-id')
            self.assertIsNone(result)
            self.assertIsNotNone(error)
            self.assertEqual(user.wecom_id, identity)
            user.save.assert_not_called()

    def test_new_and_already_bound_identity(self):
        for created in [True, False]:
            user = SimpleNamespace(wecom_id='known-id' if not created else '', save=Mock())
            users.objects.get_or_create.return_value = user, created
            view = ns['BaseLoginCallbackView']()
            view.user_type = 'wecom'
            view.client = Mock(get_user_detail=Mock(return_value={'username': 'legitimate'}))
            result, error = view.create_user_if_not_exist('known-id')
            self.assertIs(result, user)
            self.assertIsNone(error)
            self.assertEqual(user.wecom_id, 'known-id')
            user.save.assert_called_once()


if __name__ == '__main__':
    unittest.main()
