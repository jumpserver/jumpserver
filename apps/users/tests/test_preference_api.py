from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import path
from rest_framework.test import APIRequestFactory, force_authenticate

from jumpserver.views.schema import CustomSchemaGenerator
from users.api.preference import PreferenceApi
from users.models import User


class PreferenceApiTests(SimpleTestCase):
    url = '/api/v1/users/preference/'

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User(username='preference-test')

    def request(self, method, query=''):
        request = self.factory.generic(method, self.url + query)
        force_authenticate(request, user=self.user)
        return PreferenceApi.as_view()(request)

    def test_invalid_category_returns_a_field_error(self):
        for method in ('GET', 'PUT', 'PATCH', 'DELETE'):
            for query, code in (('', 'required'), ('?category=', 'invalid_choice'),
                                ('?category=basic', 'invalid_choice')):
                with self.subTest(method=method, query=query):
                    response = self.request(method, query)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.data['category'][0].code, code)

    def test_permission_check_precedes_category_validation(self):
        self.user.is_active = False
        response = self.request('GET')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'permission_denied')
        self.assertEqual(response.data, self.request('GET', '?category=lina').data)

    @patch('django.db.models.query.QuerySet.exists', return_value=False)
    def test_valid_categories_return_their_own_preferences(self, _exists):
        for category, section, field in (
            ('lina', 'basic', 'lang'),
            ('luna', 'graphics', 'rdp_resolution'),
            ('koko', 'basic', 'file_name_conflict_resolution'),
        ):
            with self.subTest(category=category):
                response = self.request('GET', '?category=' + category)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.data[section])

    def test_schema_documents_category_for_all_operations(self):
        patterns = [path(self.url.lstrip('/'), PreferenceApi.as_view())]
        operations = CustomSchemaGenerator(patterns=patterns).get_schema(public=True)['paths'][self.url]
        for method in ('get', 'put', 'patch', 'delete'):
            with self.subTest(method=method):
                params = {p['name']: p for p in operations[method].get('parameters', [])}
                self.assertIn('category', params)
                category = params['category']
                self.assertEqual(category['in'], 'query')
                self.assertTrue(category['required'])
                self.assertEqual(set(category['schema']['enum']), {'lina', 'luna', 'koko'})
