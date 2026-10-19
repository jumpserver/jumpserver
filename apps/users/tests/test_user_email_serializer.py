from django.test import TestCase

from common.utils import text_hmac_sha256
from users.models import User
from users.serializers.user import UserSerializer


class UserEmailUniquenessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Avoid provisioning roles or external services; only email validation is under test.
        cls.existing, cls.edited = User.objects.bulk_create([
            User(
                username='email-existing', name='Existing user',
                email='taken@example.com',
                email_lookup=text_hmac_sha256('taken@example.com'),
            ),
            User(
                username='email-edited', name='Edited user',
                email='own@example.com',
                email_lookup=text_hmac_sha256('own@example.com'),
            ),
        ])

    def assert_duplicate_email(self, serializer):
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertEqual(serializer.errors['email'][0].code, 'unique')

    def test_partial_update_rejects_another_users_email(self):
        serializer = UserSerializer(
            instance=self.edited, data={'email': 'taken@example.com'}, partial=True,
        )
        self.assert_duplicate_email(serializer)

    def test_full_update_rejects_another_users_email(self):
        serializer = UserSerializer(instance=self.edited, data={
            'name': self.edited.name,
            'username': self.edited.username,
            'email': 'taken@example.com',
            'system_roles': [],
            'org_roles': [],
        })
        self.assert_duplicate_email(serializer)

    def test_create_rejects_an_existing_email(self):
        serializer = UserSerializer(data={
            'name': 'New user',
            'username': 'email-new',
            'email': 'taken@example.com',
            'system_roles': [],
            'org_roles': [],
        })
        self.assert_duplicate_email(serializer)

    def test_duplicate_check_uses_normalized_email(self):
        serializer = UserSerializer(
            instance=self.edited, data={'email': '  TAKEN@Example.com  '}, partial=True,
        )
        self.assert_duplicate_email(serializer)

    def test_update_accepts_own_email(self):
        serializer = UserSerializer(
            instance=self.edited, data={'email': 'own@example.com'}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_update_accepts_unused_email(self):
        serializer = UserSerializer(
            instance=self.edited, data={'email': 'unused@example.com'}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_unrelated_update_does_not_validate_email(self):
        serializer = UserSerializer(
            instance=self.edited, data={'name': 'Renamed user'}, partial=True,
        )
        with self.assertNumQueries(0):
            self.assertTrue(serializer.is_valid(), serializer.errors)
