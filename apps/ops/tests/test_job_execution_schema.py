from django.test import SimpleTestCase
from django.urls import path
from drf_spectacular.generators import SchemaGenerator

from jumpserver.views.schema import CustomAutoSchema
from ops.api.job import JobExecutionViewSet


class JobExecutionSchemaTests(SimpleTestCase):
    def setUp(self):
        patterns = [
            path('api/v1/ops/job-executions/', JobExecutionViewSet.as_view({'get': 'list', 'post': 'create'})),
            path('api/v1/ops/job-executions/<uuid:pk>/', JobExecutionViewSet.as_view({'get': 'retrieve'})),
        ]
        self.schema = SchemaGenerator(patterns=patterns).get_schema(public=True)
        self.collection = self.schema['paths']['/api/v1/ops/job-executions/']

    def test_saved_job_run_and_history_are_discoverable(self):
        self.assertEqual(self.collection['get']['operationId'], 'ops_job_executions_list')
        creation = self.collection['post']
        self.assertEqual(creation['operationId'], 'ops_job_executions_create')
        reference = creation['requestBody']['content']['application/json']['schema']['$ref']
        body = self.schema['components']['schemas'][reference.rsplit('/', 1)[-1]]
        self.assertTrue({'job', 'parameters'} <= set(body['properties']))

    def test_list_supports_job_filter_and_detail(self):
        self.assertIn('job_id', {parameter['name'] for parameter in self.collection['get']['parameters']})
        detail = self.schema['paths']['/api/v1/ops/job-executions/{id}/']
        self.assertEqual(detail['get']['operationId'], 'ops_job_executions_retrieve')

    def test_other_execution_routes_remain_excluded(self):
        for path in ['/api/v1/accounts/change-secret-executions/',
                     '/api/v1/ops/task-executions/', '/api/v1/ops/job-executions/stop/']:
            self.assertTrue(CustomAutoSchema.exclude_some_paths(path))
