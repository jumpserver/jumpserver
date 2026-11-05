import json
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils.datastructures import MultiValueDict

from ops.api.job import JobViewSet
from ops.const import Types
from ops.models import JobExecution
from ops.serializers.job import FileSerializer, FileUploadCancelSerializer


class FileUploadCancelTests(TestCase):
    def setUp(self):
        self.user = SimpleNamespace(username='upload-user')
        self.job_id = uuid.uuid4()
        self.job = SimpleNamespace(
            args=json.dumps({'dst_path': 'test'}), save=Mock(), executions=Mock(),
        )
        self.job.executions.all.return_value = []
        self.view = JobViewSet()
        self.view.get_serializer = FileUploadCancelSerializer
        self.request = SimpleNamespace(user=self.user, data={'job_id': str(self.job_id)})
        lookup = patch('ops.api.job.get_object_or_404', return_value=self.job)
        self.lookup = lookup.start()
        self.addCleanup(lookup.stop)
        lock = patch('ops.api.job.Job.objects.select_for_update')
        self.lock = lock.start()
        self.addCleanup(lock.stop)

    def test_cancel_before_upload_marks_only_the_owners_upload_job(self):
        response = self.view.cancel_upload(self.request)

        self.assertEqual(response.data, {'cancelled': True})
        self.assertEqual(json.loads(self.job.args), {'dst_path': 'test', 'upload_cancelled': True})
        self.lookup.assert_called_once_with(
            self.lock.return_value, pk=self.job_id, creator=self.user, type=Types.upload_file,
        )
        self.job.save.assert_called_once_with()

    def test_cancel_stops_execution_and_revokes_queued_task_after_commit(self):
        execution = SimpleNamespace(id=uuid.uuid4(), is_finished=False, stop=Mock())
        self.job.executions.all.return_value = [execution]
        with patch('ops.api.job.AsyncResult') as task, self.captureOnCommitCallbacks(execute=True):
            self.view.cancel_upload(self.request)
            execution.stop.assert_called_once_with()
            task.assert_not_called()
        self.assertEqual(task.call_args.args[0], str(execution.id))
        task.return_value.revoke.assert_called_once_with()

    def test_finished_transfer_is_not_reported_as_cancelled(self):
        execution = SimpleNamespace(id=uuid.uuid4(), is_finished=True, stop=Mock())
        self.job.executions.all.return_value = [execution]
        response = self.view.cancel_upload(self.request)
        self.assertEqual(response.data, {'cancelled': False, 'task_id': str(execution.id)})
        execution.stop.assert_not_called()
        self.job.save.assert_not_called()

    def test_invalid_job_id_is_rejected_before_lookup(self):
        serializer = FileUploadCancelSerializer(data={'job_id': 'not-a-uuid'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('job_id', serializer.errors)

    def upload(self):
        file = SimpleUploadedFile('test.txt', b'upload cancellation test')
        request = SimpleNamespace(
            user=self.user, FILES=MultiValueDict({'files': [file]}),
            data={'job_id': str(self.job_id), 'files': file},
        )
        self.view.get_serializer = FileSerializer
        self.view.run_job = Mock()
        return self.view.upload(request)

    def test_upload_finishing_after_cancel_never_writes_or_starts_a_task(self):
        self.view.cancel_upload(self.request)
        with tempfile.TemporaryDirectory() as directory, override_settings(SHARE_DIR=directory):
            response = self.upload()
            self.assertEqual(response.status_code, 409)
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.view.run_job.assert_not_called()

    def test_normal_upload_still_saves_files_and_starts_the_task(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(SHARE_DIR=directory):
            response = self.upload()
            self.assertEqual(response.status_code, 201)
            path = Path(directory) / 'job_upload_file' / str(self.job_id) / 'test.txt'
            self.assertEqual(path.read_bytes(), b'upload cancellation test')
        self.view.run_job.assert_called_once()

    def test_queued_execution_checks_live_cancellation_before_starting(self):
        execution = JobExecution(job_id=self.job_id, job_type=Types.upload_file)
        execution.check_assets_perms = Mock()
        execution.check_assets_acls = Mock()
        with patch('ops.models.job.Job.objects.filter') as jobs:
            jobs.return_value.values_list.return_value.first.return_value = json.dumps(
                {'upload_cancelled': True}
            )
            with self.assertRaises(Exception):
                JobExecution.before_start(execution)
            jobs.assert_called_once_with(pk=self.job_id)
        execution.check_assets_perms.assert_not_called()
        execution.check_assets_acls.assert_not_called()

    def test_other_job_types_keep_existing_start_checks(self):
        execution = JobExecution(job_type=Types.adhoc)
        execution.check_assets_perms = Mock()
        execution.check_assets_acls = Mock()
        with patch('ops.models.job.Job.objects.filter') as jobs:
            JobExecution.before_start(execution)
            jobs.assert_not_called()
        execution.check_assets_perms.assert_called_once_with()
        execution.check_assets_acls.assert_called_once_with()

    def test_runner_observes_cancellation_after_start_checks_have_passed(self):
        execution = JobExecution(job_id=self.job_id, job_type=Types.upload_file)
        execution.save = Mock()
        execution.set_celery_id = Mock()
        execution.check_assets_perms = Mock()
        execution.check_assets_acls = Mock()
        execution.set_result = Mock()
        runner = Mock()
        with patch('ops.models.job.Job.objects.filter') as jobs, \
                patch('ops.models.job.SSHTunnelManager'), patch('ops.models.job.TaskLogCallback'):
            args = jobs.return_value.values_list.return_value.first
            args.return_value = '{}'

            def prepare_runner():
                args.return_value = '{"upload_cancelled": true}'
                return runner

            execution.get_runner = prepare_runner
            execution.start()
            callback = runner.run.call_args.kwargs['cancel_callback']
            self.assertTrue(callback())
            args.return_value = '{}'
            self.assertFalse(callback())
