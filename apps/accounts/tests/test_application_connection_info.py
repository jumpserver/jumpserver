import json
from shlex import quote
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import SimpleTestCase
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from accounts.api.account.application import IntegrationApplicationViewSet


class ApplicationConnectionInfoTests(SimpleTestCase):
    def test_secret_response_includes_the_application_org_and_sdk_endpoint(self):
        application = SimpleNamespace(id=uuid4(), org_id=uuid4(), secret='test-only-secret')
        request = APIRequestFactory().get('/api/v1/accounts/integration-applications/example/secret/')
        # Root-org administrators can view applications belonging to another org.
        request.org_id = uuid4()
        view = IntegrationApplicationViewSet()
        view.get_object = Mock(return_value=application)
        for site_url in ('https://pam.example.com:8443/', 'http://pam.example.com:8080/'):
            with self.subTest(site_url=site_url), self.settings(SITE_URL=site_url):
                response = view.get_once_secret(request)
                self.assertEqual(response.data, {
                    'id': application.id,
                    'secret': application.secret,
                    'org_id': str(application.org_id),
                    'endpoint': site_url.rstrip('/'),
                })
                self.assertEqual(response['Cache-Control'], 'no-store')

    @patch('accounts.api.account.application.record')
    def test_access_materials_use_site_url(self, record):
        application = SimpleNamespace(
            id=uuid4(), org_id=uuid4(), secret='test-only-secret',
            is_active=True, assert_account_limit=Mock(),
        )
        view = IntegrationApplicationViewSet()
        view.get_object = Mock(return_value=application)
        payloads = [{'type': 'agent', 'app_user': 'test-user', 'store_scope': 'none'}] + [
            {'type': 'sdk', 'sdk_language': language}
            for language in ('python', 'go', 'java', 'node')
        ]
        for site_url in ('https://pam.example.com:8443/', 'http://pam.example.com:8080/'):
            for payload in payloads:
                with self.subTest(site_url=site_url, payload=payload), self.settings(SITE_URL=site_url):
                    request = Request(APIRequestFactory().post('/', payload, format='json'), parsers=[JSONParser()])
                    response = view.access_materials(request)
                    endpoint = site_url.rstrip('/')
                    config = response.data['config']
                    if payload['type'] == 'agent':
                        self.assertEqual(json.loads(config)['endpoint'], endpoint)
                    elif payload['sdk_language'] == 'python':
                        self.assertIn(f"'endpoint': {endpoint!r}", config)
                    else:
                        self.assertIn(f'export JMS_ENDPOINT={quote(endpoint)}\n', config)
                    self.assertIn(endpoint + '/static/pam/', response.data['install_command'])
                    self.assertEqual(response['Cache-Control'], 'no-store')
