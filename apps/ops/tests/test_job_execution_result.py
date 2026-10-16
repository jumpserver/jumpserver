from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.http import Http404
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ops.api.job import JobExecutionResultAPIView
from ops.models import JobExecution


class JobExecutionResultTests(SimpleTestCase):
    def setUp(self):
        self.task_id = uuid4()
        self.user = SimpleNamespace(
            pk=uuid4(), is_authenticated=True, is_anonymous=False, has_perms=lambda perms: True
        )
        self.view = JobExecutionResultAPIView.as_view(throttle_classes=[])
        self.request = APIRequestFactory().get(
            f'/api/v1/ops/job-execution/result/{self.task_id}/'
        )
        force_authenticate(self.request, user=self.user)

    def test_returns_stored_host_results_without_starting_a_job(self):
        result = {
            'ok': {'server-1': {'Check': {'rc': 0, 'stdout': 'healthy'}}},
            'failures': {'server-2': {'Check': {'rc': 1, 'stderr': 'failed'}}},
            'dark': {}, 'skipped': {},
        }
        execution = SimpleNamespace(id=self.task_id, result=result)
        with patch('ops.api.job.get_current_org', return_value='test-org'), \
             patch('ops.api.job.tmp_to_org', return_value=nullcontext()) as organization, \
             patch('ops.api.job.get_object_or_404', return_value=execution) as lookup:
            response = self.view(self.request, task_id=self.task_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'id': str(self.task_id), 'result': result})
        lookup.assert_called_once_with(JobExecution, pk=str(self.task_id), creator=self.user)
        organization.assert_called_once_with('test-org')

    def test_unavailable_result_stays_null(self):
        execution = SimpleNamespace(id=self.task_id, result=None)
        with patch('ops.api.job.get_current_org'), \
             patch('ops.api.job.tmp_to_org', return_value=nullcontext()), \
             patch('ops.api.job.get_object_or_404', return_value=execution):
            response = self.view(self.request, task_id=self.task_id)
        self.assertIsNone(response.data['result'])

    def test_missing_or_unowned_execution_is_not_disclosed(self):
        with patch('ops.api.job.get_current_org'), \
             patch('ops.api.job.tmp_to_org', return_value=nullcontext()), \
             patch('ops.api.job.get_object_or_404', side_effect=Http404):
            response = self.view(self.request, task_id=self.task_id)
        self.assertEqual(response.status_code, 404)

    def test_requires_view_permission_before_loading_results(self):
        self.user.has_perms = lambda perms: False
        with patch('ops.api.job.get_object_or_404') as lookup:
            response = self.view(self.request, task_id=self.task_id)
        self.assertEqual(response.status_code, 403)
        lookup.assert_not_called()

    def test_is_read_only(self):
        request = APIRequestFactory().post('/', {'result': {'forged': True}}, format='json')
        force_authenticate(request, user=self.user)
        response = self.view(request, task_id=self.task_id)
        self.assertEqual(response.status_code, 405)

    def test_anonymous_caller_cannot_load_results(self):
        request = APIRequestFactory().get('/')
        with patch('ops.api.job.get_object_or_404') as lookup:
            response = self.view(request, task_id=self.task_id)
        self.assertIn(response.status_code, [401, 403])
        lookup.assert_not_called()
