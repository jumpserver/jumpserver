from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import path
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIRequestFactory

from ops.api.playbook import PlaybookFileBrowserAPIView, PlaybookViewSet


class PlaybookSchemaTests(SimpleTestCase):
    def setUp(self):
        patterns = [
            path('api/v1/ops/playbooks/', PlaybookViewSet.as_view({'get': 'list', 'post': 'create'})),
            path('api/v1/ops/playbook/<uuid:pk>/file/', PlaybookFileBrowserAPIView.as_view()),
        ]
        self.schema = SchemaGenerator(patterns=patterns).get_schema(public=True)
        self.files = self.schema['paths']['/api/v1/ops/playbook/{id}/file/']

    def resolve(self, schema):
        return self.schema['components']['schemas'][schema['$ref'].rsplit('/', 1)[-1]]

    def request_fields(self, method):
        schema = self.files[method]['requestBody']['content']['application/json']['schema']
        return {k: v for k, v in self.resolve(schema)['properties'].items() if not v.get('readOnly')}

    def test_file_bodies_are_generated_from_method_serializers(self):
        self.assertEqual(set(self.request_fields('post')), {'key', 'name', 'is_directory', 'content'})
        self.assertEqual(set(self.request_fields('patch')), {'key', 'new_name', 'is_directory', 'content'})
        self.assertEqual(self.request_fields('post')['content']['type'], 'string')
        self.assertEqual(self.files['patch']['operationId'], 'ops_playbook_file_partial_update')

    def test_file_responses_do_not_expose_write_only_inputs(self):
        response = self.files['post']['responses']['200']['content']['application/json']['schema']
        fields = {k for k, v in self.resolve(response)['properties'].items() if not v.get('writeOnly')}
        self.assertEqual(fields, {'name', 'id', 'title', 'isParent', 'pId', 'open', 'iconSkin'})
        self.assertNotIn('content', self.files['patch']['responses']['200'])

    def test_query_parameters_use_backends_without_schema_decorators(self):
        get = {p['name']: p for p in self.files['get']['parameters']}
        self.assertTrue({'key', 'expand'} <= get.keys())
        delete = {p['name']: p for p in self.files['delete']['parameters']}
        self.assertTrue(delete['key']['required'])
        self.assertNotIn('expand', delete)
        playbooks = self.schema['paths']['/api/v1/ops/playbooks/']
        list_parameters = {p['name']: p for p in playbooks['get']['parameters']}
        self.assertEqual(list_parameters['only_mine']['schema']['type'], 'boolean')
        create_parameters = {p['name']: p for p in playbooks['post']['parameters']}
        self.assertEqual(set(create_parameters), {'clone_from'})
        self.assertEqual(create_parameters['clone_from']['schema']['format'], 'uuid')


class PlaybookFileInputTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.factory = APIRequestFactory()
        self.api = PlaybookFileBrowserAPIView.as_view(
            authentication_classes=[], permission_classes=[], throttle_classes=[],
        )
        self.playbook = SimpleNamespace(work_dir=str(self.directory))

    def call(self, method, data):
        request = getattr(self.factory, method)('/', data, format='json')
        with patch.object(PlaybookFileBrowserAPIView, 'get_playbook', return_value=self.playbook):
            return self.api(request, pk='00000000-0000-0000-0000-000000000001')

    def test_create_and_edit_preserve_yaml_whitespace_and_response(self):
        content = '\n  - name: example\n    value: yes\n\n'
        response = self.call('post', {'name': 'tasks.yml', 'content': content})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'name': 'tasks.yml', 'title': 'tasks.yml', 'id': str(Path.cwd() / 'tasks.yml'),
            'isParent': False, 'pId': 'root', 'open': True, 'iconSkin': 'file',
        })
        self.assertEqual((self.directory / 'tasks.yml').read_text(), content)
        response = self.call('patch', {'key': 'tasks.yml', 'content': content + '  '})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)
        self.assertEqual((self.directory / 'tasks.yml').read_text(), content + '  ')

    def test_default_file_creation_and_directory_rename(self):
        response = self.call('post', {})
        self.assertEqual(response.data['name'], 'new_file.yml')
        self.assertEqual((self.directory / 'new_file.yml').read_text(), '')
        response = self.call('post', {'name': 'tasks', 'is_directory': True})
        self.assertTrue(response.data['isParent'])
        self.assertNotIn('iconSkin', response.data)
        response = self.call('patch', {'key': 'tasks', 'new_name': 'roles', 'is_directory': True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue((self.directory / 'roles').is_dir())

    def test_invalid_input_does_not_write_files(self):
        response = self.call('post', {'name': 'invalid.yml', 'content': ['not', 'text']})
        self.assertEqual(response.status_code, 400)
        self.assertFalse((self.directory / 'invalid.yml').exists())
        response = self.call('patch', {'content': 'missing path'})
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.data)
