from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from ops.api.job import JobExecutionViewSet
from ops.api.playbook import PlaybookViewSet
from ops.models import Job, JobExecution, Playbook
from ops.serializers.job import JobExecutionSerializer
from ops.serializers.playbook import PlaybookSerializer
from users.models import User


@override_settings(SECURITY_COMMAND_EXECUTION=True, DEBUG_DEV=False)
class CreateValidationTests(SimpleTestCase):
    def setUp(self):
        self.user = User(username='create-validation')
        self.context = {'request': SimpleNamespace(user=self.user)}
        self.factory = APIRequestFactory()

    def assert_invalid_create(self, view_class, data, field, code):
        view = view_class.as_view(
            {'post': 'create'}, authentication_classes=[], permission_classes=[], throttle_classes=[],
        )
        request = self.factory.post('/', data, format='json', HTTP_ACCEPT='application/json')
        force_authenticate(request, user=self.user)
        with patch.object(view_class, 'perform_create') as create:
            response = view(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data[field][0].code, code)
        self.assertEqual(response.render()['Content-Type'], 'application/json')
        create.assert_not_called()

    def test_playbook_requires_a_nonempty_name(self):
        for data, code in [({}, 'required'), ({'name': None}, 'null'),
                           ({'name': ''}, 'blank'), ({'name': '  '}, 'blank')]:
            with self.subTest(data=data):
                self.assert_invalid_create(PlaybookViewSet, data, 'name', code)

    def test_execution_requires_a_job(self):
        for data, code in [({}, 'required'), ({'job': None}, 'null'), ({'job': ''}, 'null')]:
            with self.subTest(data=data):
                self.assert_invalid_create(JobExecutionViewSet, data, 'job', code)

    def test_playbook_accepts_explicit_and_uploaded_names(self):
        for data, name in [
            ({'name': 'Example'}, 'Example'),
            ({'path': SimpleUploadedFile('example.zip', b'archive')}, 'example'),
            ({'name': '', 'path': SimpleUploadedFile('example.zip', b'archive')}, 'example'),
        ]:
            with self.subTest(data=data), patch('django.db.models.query.QuerySet.exists', return_value=False):
                serializer = PlaybookSerializer(data=data, context=self.context)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(serializer.validated_data['name'], name)

    def test_playbook_partial_update_keeps_existing_name(self):
        playbook = Playbook(name='Example', creator=self.user)
        serializer = PlaybookSerializer(
            playbook, data={'comment': 'Updated'}, partial=True, context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('name', serializer.validated_data)

    def test_execution_accepts_owned_job_and_rejects_other_users_job(self):
        job = Job(creator=self.user)
        with patch('django.db.models.query.QuerySet.get', return_value=job), \
                patch.object(JobExecutionSerializer, 'get_job_default_parameters', return_value={}):
            serializer = JobExecutionSerializer(data={'job': str(job.id)}, context=self.context)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data['job'], job)

            job.creator = User(username='other-user')
            serializer = JobExecutionSerializer(data={'job': str(job.id)}, context=self.context)
            self.assertFalse(serializer.is_valid())
            self.assertIn('job', serializer.errors)

    def test_execution_history_can_still_have_no_job(self):
        execution = JobExecution(job=None, creator=self.user)
        execution.org = SimpleNamespace(name='Default')
        self.assertIsNone(JobExecutionSerializer(execution).data['job'])
