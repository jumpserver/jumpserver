from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from users.models import User
from users.signal_handlers import on_ldap_create_user


class LDAPUserSourceTest(SimpleTestCase):
    @patch('users.signal_handlers.User.objects.filter')
    def test_new_user_source_matches_ldap_category(self, user_filter):
        user_filter.return_value.exists.return_value = False

        for source in (User.Source.ldap.value, User.Source.ldap_ha.value):
            with self.subTest(source=source):
                user = SimpleNamespace(
                    username='new-user', Source=User.Source, save=Mock()
                )
                ldap_user = SimpleNamespace(category=source)

                on_ldap_create_user(None, user, ldap_user)

                self.assertEqual(user.source, source)
                user.save.assert_called_once_with()
