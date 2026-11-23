from unittest.mock import patch

from django.db.models import QuerySet
from django.test import TestCase, override_settings

from authentication.backends.oauth2.backends import OAuth2Backend
from authentication.utils import check_user_property_is_correct
from users.models import User


class UserPhoneTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user, = User.objects.bulk_create([
            User(username='phone-user', name='Phone user', email='phone@example.com'),
        ])

    def set_legacy_phone(self, phone='13800138000'):
        # Bypass user write hooks to represent data saved before normalization.
        QuerySet(model=User, using='default').filter(pk=self.user.pk).update(phone=phone)
        self.user.refresh_from_db()

    def test_save_normalizes_phone_in_memory_and_database(self):
        self.user.phone = '13800138000'
        self.user.save()
        self.assertEqual(self.user.phone, '+8613800138000')
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, '+8613800138000')

    def test_partial_phone_save_normalizes_without_updating_email(self):
        email = self.user.email
        self.user.phone = '13800138000'
        self.user.email = 'unsaved@example.com'
        self.user.save(update_fields=['phone'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, '+8613800138000')
        self.assertEqual(self.user.email, email)

    def test_unrelated_partial_save_does_not_rewrite_legacy_phone(self):
        self.set_legacy_phone()
        self.user.name = 'Changed'
        self.user.save(update_fields=['name'])
        self.assertEqual(self.user.phone, '13800138000')
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, '13800138000')

    def test_bulk_create_normalizes_phone(self):
        user, = User.objects.bulk_create([
            User(username='phone-bulk', email='phone-bulk@example.com', phone='13800138000'),
        ])
        user.refresh_from_db()
        self.assertEqual(user.phone, '+8613800138000')

    def test_queryset_update_normalizes_phone(self):
        User.objects.filter(pk=self.user.pk).update(phone='13800138000')
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, '+8613800138000')

    def test_empty_and_unparseable_values_do_not_break_user_saves(self):
        for phone in (None, '', 'not-a-phone'):
            with self.subTest(phone=phone):
                self.user.phone = phone
                self.user.save(update_fields=['phone'])
                self.user.refresh_from_db()
                self.assertEqual(self.user.phone, phone)

    def test_phone_matching_accepts_both_legacy_and_normalized_values(self):
        for stored in ('13800138000', '+8613800138000'):
            self.set_legacy_phone(stored)
            for supplied in ('13800138000', '+8613800138000'):
                with self.subTest(stored=stored, supplied=supplied):
                    self.assertEqual(
                        check_user_property_is_correct(self.user.username, phone=supplied), self.user,
                    )
            self.assertIsNone(check_user_property_is_correct(self.user.username, phone='+8613900138000'))
            self.assertIsNone(check_user_property_is_correct(self.user.username, phone='+113800138000'))

    def test_other_properties_and_missing_users_keep_exact_matching(self):
        self.assertIsNone(check_user_property_is_correct(self.user.username, email='PHONE@example.com'))
        self.assertIsNone(check_user_property_is_correct('missing-user', phone='13800138000'))

    @override_settings(
        AUTH_OAUTH2_USER_ATTR_MAP={'username': 'login', 'phone': 'mobile'},
        AUTH_OAUTH2_ALWAYS_UPDATE_USER=True,
        ONLY_ALLOW_EXIST_USER_AUTH=False,
    )
    @patch('users.signal_handlers.bind_user_to_org_role', return_value=[])
    def test_oauth2_creation_and_resync_keep_canonical_phone(self, bind_roles):
        backend = object.__new__(OAuth2Backend)
        cases = (
            ('13800138000', '13900139000'),
            (13800138000, 13900139000),
        )
        for index, (phone, updated_phone) in enumerate(cases):
            with self.subTest(phone=phone):
                userinfo = {'login': f'oauth-phone-{index}', 'mobile': phone}
                user, created = backend.get_or_create_user_from_userinfo(None, userinfo)
                self.assertTrue(created)
                self.assertEqual(user.phone, '+8613800138000')
                user.refresh_from_db()
                self.assertEqual(user.phone, '+8613800138000')

                userinfo['mobile'] = updated_phone
                user, created = backend.get_or_create_user_from_userinfo(None, userinfo)
                self.assertFalse(created)
                self.assertEqual(user.phone, '+8613900139000')
                user.refresh_from_db()
                self.assertEqual(user.phone, '+8613900139000')
