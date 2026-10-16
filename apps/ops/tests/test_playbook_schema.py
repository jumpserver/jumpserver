from django.test import SimpleTestCase
from django.urls import path
from drf_spectacular.generators import SchemaGenerator

from ops.api.playbook import PlaybookFileBrowserAPIView, PlaybookViewSet


class PlaybookSchemaTests(SimpleTestCase):
    def setUp(self):
        patterns = [
            path('api/v1/ops/playbooks/', PlaybookViewSet.as_view({'get': 'list', 'post': 'create'})),
            path('api/v1/ops/playbook/<uuid:pk>/file/', PlaybookFileBrowserAPIView.as_view()),
        ]
        self.schema = SchemaGenerator(patterns=patterns).get_schema(public=True)
        self.files = self.schema['paths']['/api/v1/ops/playbook/{id}/file/']

    def body(self, method):
        reference = self.files[method]['requestBody']['content']['application/json']['schema']['$ref']
        return self.schema['components']['schemas'][reference.rsplit('/', 1)[-1]]

    def test_describes_file_creation_and_content(self):
        properties = self.body('post')['properties']
        self.assertEqual(set(properties), {'key', 'name', 'is_directory', 'content'})
        self.assertEqual(properties['content']['type'], 'string')

    def test_describes_file_update_and_preserves_operation_ids(self):
        self.assertEqual(set(self.body('patch')['properties']), {'key', 'new_name', 'is_directory', 'content'})
        self.assertEqual(self.files['patch']['operationId'], 'ops_playbook_file_partial_update')

    def test_describes_file_and_clone_query_parameters(self):
        self.assertTrue({'key', 'expand'} <= {item['name'] for item in self.files['get']['parameters']})
        deletion = next(item for item in self.files['delete']['parameters'] if item['name'] == 'key')
        self.assertTrue(deletion['required'])
        templates = self.schema['paths']['/api/v1/ops/playbooks/']
        clone = next(item for item in templates['post']['parameters'] if item['name'] == 'clone_from')
        self.assertEqual(clone['schema']['format'], 'uuid')
