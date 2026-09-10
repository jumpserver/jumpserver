from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account, ApplicationCredential, ClientAccessConfiguration, IntegrationApplication
from assets.const import Category
from assets.models import Asset, Platform
from orgs.models import Organization
from orgs.utils import set_current_org
from users.models import User


class CredentialTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.org = Organization.default()
        set_current_org(self.org)
        self.admin = User.objects.create_superuser(
            username='credential-admin', password='password',
            name='Credential admin', email='credential-admin@example.com',
        )
        self.platform = Platform.objects.create(
            name='CredentialTestPostgreSQL',
            category=Category.DATABASE,
            type='postgresql',
        )
        self.asset = Asset.objects.create(
            name='credential-test-pg', address='127.0.0.1',
            platform=self.platform,
        )
        self.primary = Account.objects.create(
            name='account-a', username='account-a', asset=self.asset,
            secret='primary-secret',
        )
        self.backup = Account.objects.create(
            name='account-b', username='account-b', asset=self.asset,
            secret='backup-secret',
        )
        self.application = IntegrationApplication.objects.create(
            name='order-service', secret='application-secret',
            accounts={
                'type': 'ids',
                'ids': [str(self.primary.id), str(self.backup.id)],
            },
        )
        self.credential = ApplicationCredential.objects.create(
            name='PostgreSQL primary',
            primary_account=self.primary,
            backup_account=self.backup,
            published_account=self.primary,
        )
        # State-machine tests assume successful backup verification; the real
        # preflight lifecycle is exercised separately in CredentialPreflightTests.
        from accounts.credential_rotation import CredentialRotationManager
        self.precheck_patch = patch(
            'accounts.credential_rotation.preflight.start',
            side_effect=lambda credential, operator='', operator_id=None:
                CredentialRotationManager(credential.id)._publish(credential, operator),
        )
        self.precheck_patch.start()
        self.addCleanup(self.precheck_patch.stop)

    def request(self, method, path, data=None, user=None):
        if isinstance(user, IntegrationApplication):
            configuration, _ = ClientAccessConfiguration.objects.get_or_create(
                application=user, name='Test SDK', defaults={'type': 'sdk'},
            )
            configuration.credentials.add(self.credential)
            data = dict(data or {}, configuration_id=str(configuration.id))
        creator = getattr(self.factory, method)
        request = creator(
            path, data=data or {}, format='json',
            HTTP_X_JMS_ORG=str(self.org.id),
        )
        force_authenticate(request, user=user or self.admin)
        return request
