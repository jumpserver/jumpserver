from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import include, path
from drf_spectacular.generators import SchemaGenerator
from rest_framework.request import Request
from rest_framework.routers import SimpleRouter
from rest_framework.test import APIRequestFactory

from jumpserver.views.schema import CustomAutoSchema
from ops.api.job import JobExecutionViewSet, JobViewSet


class JobExecutionSchemaTests(SimpleTestCase):
    def generate_schema(self, *, from_mcp=False, ai=False):
        schema = CustomAutoSchema()
        schema.from_mcp = from_mcp
        router = SimpleRouter()
        router.register('job-executions', JobExecutionViewSet, basename='job-executions')
        patterns = [
            path('api/v1/ops/', include(router.urls)),
            path(
                'api/v1/ops/jobs/<uuid:pk>/executions/',
                JobViewSet.as_view({'get': 'list'}),
            ),
        ]
        headers = {'HTTP_X_JMS_AI_SCHEMA': '1'} if ai else {}
        request = Request(APIRequestFactory().get('/api/docs/', **headers))
        with patch.object(JobExecutionViewSet, 'schema', schema):
            return SchemaGenerator(patterns=patterns).get_schema(request=request, public=True)

    def test_only_read_only_history_is_discoverable(self):
        for from_mcp in (False, True):
            with self.subTest(from_mcp=from_mcp):
                schema = self.generate_schema(from_mcp=from_mcp)
                self.assertEqual(
                    set(schema['paths']),
                    {
                        '/api/v1/ops/job-executions/',
                        '/api/v1/ops/job-executions/{id}/',
                    },
                )
                collection = schema['paths']['/api/v1/ops/job-executions/']
                self.assertEqual(set(collection), {'get'})
                self.assertEqual(collection['get']['operationId'], 'ops_job_executions_list')
                detail = schema['paths']['/api/v1/ops/job-executions/{id}/']
                self.assertEqual(set(detail), {'get'})
                self.assertEqual(detail['get']['operationId'], 'ops_job_executions_retrieve')

    def test_history_uses_native_filters_and_permissions(self):
        for from_mcp in (False, True):
            with self.subTest(from_mcp=from_mcp):
                schema = self.generate_schema(from_mcp=from_mcp)
                operation = schema['paths']['/api/v1/ops/job-executions/']['get']
                parameters = {parameter['name']: parameter for parameter in operation['parameters']}
                self.assertEqual(
                    parameters['job_id']['schema'], {'type': 'string', 'format': 'uuid'}
                )
                self.assertIn('ops.view_jobexecution', operation['x-jms-required-permissions'])
                self.assertTrue(operation['x-jms-rbac-protected'])

    def test_ai_schema_retains_existing_write_operations(self):
        schema = self.generate_schema(ai=True)
        self.assertIn('post', schema['paths']['/api/v1/ops/job-executions/'])
        self.assertIn('post', schema['paths']['/api/v1/ops/job-executions/stop/'])

    def test_other_execution_apis_remain_excluded(self):
        schema = CustomAutoSchema()
        schema.view = SimpleNamespace(request=SimpleNamespace(headers={}), action='list')
        schema.method = 'GET'
        for route in (
            '/api/v1/ops/task-executions/',
            '/api/v1/accounts/change-secret-executions/',
            '/api/v1/ops/jobs/{id}/executions/',
        ):
            with self.subTest(route=route):
                schema.path = route
                self.assertTrue(schema.is_excluded())

    def test_read_action_opt_in_does_not_include_write_methods(self):
        schema = CustomAutoSchema()
        schema.view = SimpleNamespace(
            request=SimpleNamespace(headers={}),
            action='list',
            schema_included_actions=('list',),
        )
        schema.path = '/api/v1/ops/job-executions/'
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with self.subTest(method=method):
                schema.method = method
                self.assertTrue(schema.is_excluded())
