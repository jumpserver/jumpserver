from django.test import SimpleTestCase
from django.urls import path, resolve
from rest_framework.test import APITestCase

from assets.models import Asset, Platform
from jumpserver.views.schema import CustomSchemaGenerator
from orgs.models import Organization
from orgs.utils import tmp_to_org
from rbac.builtin import BuiltinRole
from users.models import User


URL = '/api/v1/assets/assets/sync-platform-protocols/'


class SyncPlatformProtocolsTests(APITestCase):
    def setUp(self):
        org = Organization.default()
        user = User.objects.create(username='platform-admin')
        org.add_member(user, role=BuiltinRole.org_admin)
        self.client.force_authenticate(user)
        self.platform = Platform.objects.create(name='Sync platform', category='host', type='linux')
        self.platform.protocols.create(name='ssh', port=2222)
        with tmp_to_org(org):
            self.asset = self.create_asset('First host')

    def create_asset(self, name):
        asset = Asset.objects.create(name=name, address='192.0.2.10', platform=self.platform)
        asset.protocols.create(name='telnet', port=23)
        return asset

    def test_sync_replaces_asset_protocols_in_current_org(self):
        with tmp_to_org(Organization.default()):
            second = self.create_asset('Second host')
        with tmp_to_org(Organization.objects.create(name='Other org')):
            other = self.create_asset('Other host')

        response = self.client.post(URL, {'platform_id': self.platform.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.content, b'')
        for asset in (self.asset, second):
            self.assertEqual(list(asset.protocols.values_list('name', 'port')), [('ssh', 2222)])
        self.assertEqual(list(other.protocols.values_list('name', 'port')), [('telnet', 23)])

    def test_invalid_input_and_unknown_platform_preserve_protocols(self):
        for body in ({}, {'platform': self.platform.pk}, {'platform_id': None},
                     {'platform_id': 'abc'}, {'platform_id': {'id': self.platform.pk}}):
            with self.subTest(body=body):
                response = self.client.post(URL, body, format='json')
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn('platform_id', response.json())

        response = self.client.post(URL, {'platform_id': self.platform.pk + 1000}, format='json')
        self.assertEqual(response.status_code, 404, response.content)
        self.assertEqual(list(self.asset.protocols.values_list('name', 'port')), [('telnet', 23)])


class SyncPlatformProtocolsSchemaTests(SimpleTestCase):
    def test_generated_request_and_response(self):
        patterns = [path(URL.lstrip('/'), resolve(URL).func)]
        schema = CustomSchemaGenerator(patterns=patterns).get_schema(public=True)
        operation = schema['paths'][URL]['post']
        body = operation['requestBody']
        self.assertTrue(body['required'])
        ref = body['content']['application/json']['schema']['$ref']
        fields = schema['components']['schemas'][ref.rsplit('/', 1)[-1]]
        self.assertEqual(fields['required'], ['platform_id'])
        self.assertEqual(set(fields['properties']), {'platform_id'})
        self.assertEqual(fields['properties']['platform_id']['type'], 'integer')
        self.assertNotIn('content', operation['responses']['200'])
