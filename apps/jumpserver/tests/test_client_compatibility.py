from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import resolve
from rest_framework.test import APIClient, APIRequestFactory

from settings.api.settings import ClientCompatibilityView, ClientVersionView


@override_settings(VERSION='v5.1.0-rc1', MIN_CLIENT_VERSION='v5.1.0')
class ClientCompatibilityTests(SimpleTestCase):
    def test_anonymous_response_uses_runtime_version_and_minimum(self):
        request = APIRequestFactory().get('/api/v1/settings/client/compatibility/')
        with patch.dict('os.environ', {'CURRENT_VERSION': 'display-only', 'CLIENT_VERSION': 'download-only'}):
            response = ClientCompatibilityView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'schema_version': 1, 'core_version': 'v5.1.0-rc1', 'min_client_version': 'v5.1.0',
        })
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_stale_authorization_does_not_affect_anonymous_preflight(self):
        request = APIRequestFactory().get('/', HTTP_AUTHORIZATION='Bearer expired')
        response = ClientCompatibilityView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_source_version_is_not_replaced_with_target_release(self):
        with self.settings(VERSION='v2.0.0'):
            response = ClientCompatibilityView.as_view()(APIRequestFactory().get('/'))
        self.assertEqual(response.data['core_version'], 'v2.0.0')

    def test_minimum_changes_independently_of_runtime_version(self):
        with self.settings(VERSION='v5.2.3', MIN_CLIENT_VERSION='v5.1.4'):
            response = ClientCompatibilityView.as_view()(APIRequestFactory().get('/'))
        self.assertEqual(response.data['core_version'], 'v5.2.3')
        self.assertEqual(response.data['min_client_version'], 'v5.1.4')

    def test_versions_preserve_patch_prerelease_and_lts(self):
        for version in ('v5.1.0', 'v5.1.2', 'v5.1.0-rc1', 'v5.1.0-rc1+build.9', 'v5.1.0-lts', 'v5.1.0-lts+build.1'):
            with self.subTest(version=version), self.settings(VERSION=version, MIN_CLIENT_VERSION=version):
                response = ClientCompatibilityView.as_view()(APIRequestFactory().get('/'))
                self.assertEqual(response.data['core_version'], version)
                self.assertEqual(response.data['min_client_version'], version)

    def test_endpoint_is_read_only(self):
        for method in ('post', 'put', 'patch', 'delete'):
            with self.subTest(method=method):
                request = getattr(APIRequestFactory(), method)('/', {}, format='json')
                response = ClientCompatibilityView.as_view()(request)
                self.assertEqual(response.status_code, 405)

    def test_legacy_version_array_is_unchanged(self):
        response = ClientVersionView.as_view()(APIRequestFactory().get('/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, ['4.0.0', '4.1.0', '4.1.1', '4.1.2', '5.0.0', '5.1.0'])

    @override_settings(MIDDLEWARE=[], ALLOWED_HOSTS=['testserver'])
    def test_registered_routes_return_both_contracts(self):
        client = APIClient()
        path = '/api/v1/settings/client/compatibility/'
        self.assertEqual(resolve(path).url_name, 'client-compatibility')
        response = client.get(path, HTTP_AUTHORIZATION='Bearer expired')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['schema_version'], 1)
        self.assertEqual(response['Cache-Control'], 'no-store')
        legacy = client.get('/api/v1/settings/client/versions/')
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(legacy.json(), ['4.0.0', '4.1.0', '4.1.1', '4.1.2', '5.0.0', '5.1.0'])
