import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch
import uuid

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from ops.ansible.docker import (
    docker_extravars, prepare_isolated_ansible_runtime, use_ansible_docker_isolation,
)
from ops.ansible.execution import get_ansible_execution_backend
from ops.ansible.interface import RunnerInterface
from ops.ansible.runners.native import AnsibleNativeRunner
from ops.ansible.runners.ssh import AnsibleSSHRunner, cancel_ssh_job, localize_event, _running
from ops.ansible.runner import AdHocRunner, PlaybookRunner, UploadFileRunner


@override_settings(DEBUG_DEV=False)
class SSHBackendTest(SimpleTestCase):
    @override_settings(ANSIBLE_EXECUTION_BACKEND='', ANSIBLE_DOCKER_ENABLED=True)
    def test_existing_docker_setting_remains_the_default(self):
        self.assertEqual(get_ansible_execution_backend(), 'docker')
        with override_settings(ANSIBLE_DOCKER_ENABLED=False):
            self.assertEqual(get_ansible_execution_backend(), 'native')

    @override_settings(ANSIBLE_EXECUTION_BACKEND='ssh', ANSIBLE_DOCKER_ENABLED=True)
    def test_ssh_overrides_docker_and_stages_current_runtime(self):
        self.assertFalse(use_ansible_docker_isolation())
        self.assertIs(RunnerInterface(AnsibleNativeRunner).get_runner_type(), AnsibleSSHRunner)
        self.assertEqual(docker_extravars({})['local_python_interpreter'], '/usr/bin/python3')
        with TemporaryDirectory() as root:
            env = prepare_isolated_ansible_runtime(root)
            self.assertTrue(Path(env['ANSIBLE_CONFIG']).is_file())
            self.assertTrue((Path(env['PYTHONPATH']) / 'libs/ansible/modules').is_dir())

    @override_settings(ANSIBLE_EXECUTION_BACKEND='invalid')
    def test_invalid_backend_fails_closed(self):
        with self.assertRaises(ValueError):
            get_ansible_execution_backend()

    @override_settings(ANSIBLE_EXECUTION_BACKEND='ssh', ANSIBLE_EXECUTOR_GATEWAY_HOST='')
    def test_gateway_requires_an_address_reachable_from_executor(self):
        interface = RunnerInterface(AnsibleNativeRunner)
        with self.assertRaises(ValueError):
            interface.get_gateway_proxy_host()
        with override_settings(ANSIBLE_EXECUTOR_GATEWAY_HOST='core.internal'):
            self.assertEqual(interface.get_gateway_proxy_host(), 'core.internal')

    @override_settings(
        ANSIBLE_EXECUTION_BACKEND='ssh', ANSIBLE_EXECUTOR_HOST='executor',
        ANSIBLE_EXECUTOR_PORT=2222, ANSIBLE_EXECUTOR_PRIVATE_KEY='/service/key',
        ANSIBLE_EXECUTOR_KNOWN_HOSTS='/service/known_hosts',
        ANSIBLE_EXECUTOR_CONNECT_TIMEOUT=10, ANSIBLE_RUNNER_JOB_TIMEOUT=1800,
    )
    def test_callbacks_cancel_metadata_and_cleanup_follow_existing_contract(self):
        events, statuses = [], []
        def execute(**kwargs):
            self.assertEqual(kwargs['job_timeout'], 0)
            metadata = json.loads((Path(kwargs['private_data_dir']) / 'remote.json').read_text())
            self.assertEqual(metadata, {'backend': 'ssh', 'job_id': kwargs['job_id']})
            kwargs['event_handler']({'event': 'runner_on_start'})
            kwargs['status_handler']({'status': 'running'})
            self.assertFalse(kwargs['cancel_callback']())
            RunnerInterface(AnsibleNativeRunner).kill_process(metadata)
            self.assertTrue(kwargs['cancel_callback']())
            # A process without the in-memory registry can still cancel prefork jobs.
            _running[kwargs['job_id']].clear()
            (Path(kwargs['private_data_dir']) / f'cancel-{kwargs["job_id"]}').touch()
            self.assertTrue(kwargs['cancel_callback']())
            return 'result'
        with TemporaryDirectory() as root, patch('jms_ansible_executor.client.run', side_effect=execute):
            runner = AnsibleSSHRunner(private_data_dir=root, event_handler=events.append,
                                      status_handler=statuses.append, clean_workspace=False, timeout=0)
            self.assertEqual(runner.run(), 'result')
            self.assertEqual(statuses, [{'status': 'running', 'private_data_dir': root}])
            self.assertEqual(events, [{'event': 'runner_on_start'}])
            self.assertEqual(_running, {})
        with TemporaryDirectory() as root, patch('jms_ansible_executor.client.run', side_effect=RuntimeError):
            task = Path(root) / 'job'
            runner = AnsibleSSHRunner(private_data_dir=str(task))
            with self.assertRaises(RuntimeError):
                runner.run()
            self.assertFalse(task.exists())
            self.assertEqual(_running, {})

    def test_canceling_unknown_or_finished_job_is_harmless(self):
        cancel_ssh_job(str(uuid.uuid4()))

    @patch.dict(os.environ, {'ANSIBLE_FORCE_COLOR': 'True', 'SERVICE_SECRET': 'private'})
    def test_remote_color_setting_preserves_task_override(self):
        for color in (None, 'False'):
            env = {'TASK_VALUE': 'kept'}
            if color is not None:
                env['ANSIBLE_FORCE_COLOR'] = color
            with self.subTest(color=color), TemporaryDirectory() as root, \
                    patch('jms_ansible_executor.client.run') as execute:
                AnsibleSSHRunner(private_data_dir=root, envvars=env).run()
                self.assertEqual(execute.call_args.kwargs['envvars'], {
                    'ANSIBLE_FORCE_COLOR': color or 'True', 'TASK_VALUE': 'kept',
                })
                self.assertEqual(env.get('ANSIBLE_FORCE_COLOR'), color)

    def test_job_stop_persists_uuid_for_another_worker_process(self):
        from ops.models.job import JobExecution
        with TemporaryDirectory() as root:
            job_id = str(uuid.uuid4())
            metadata = {'backend': 'ssh', 'job_id': job_id}
            (Path(root) / 'remote.json').write_text(json.dumps(metadata))
            job = SimpleNamespace(private_dir=root, set_error=Mock())
            with patch('ops.signal_handlers.job_execution_stop_pub_sub') as notifications:
                JobExecution.stop(job)
            self.assertTrue((Path(root) / f'cancel-{job_id}').exists())
            notifications.publish.assert_called_once_with(metadata)
            job.set_error.assert_called_once()

    def test_canceled_result_remains_a_finished_job(self):
        from ops.const import JobStatus
        from ops.models.job import JobExecution
        execution = JobExecution(
            status=JobStatus.failed, summary={'error': 'Job stop by "user cancel"'},
        )
        callback = SimpleNamespace(status='canceled', summary={}, result={})
        with patch.object(JobExecution.objects, 'get', return_value=execution), \
                patch.object(execution, 'save'):
            execution.set_result(callback)
        self.assertEqual(execution.status, JobStatus.failed)
        self.assertTrue(execution.is_finished)
        self.assertIsNotNone(execution.date_finished)
        self.assertEqual(execution.summary['error'], 'Job stop by "user cancel"')

    def test_remote_task_paths_only_map_to_the_private_project(self):
        with TemporaryDirectory() as root:
            for path in ('/etc/shadow:1', '/remote/project/../../secret:2'):
                data = {'event_data': {'task_path': path}}
                self.assertNotIn('task_path', localize_event(data, Path(root))['event_data'])
            data = {'event_data': {'task_path': '/remote/project/main.yml:5'}}
            self.assertEqual(localize_event(data, Path(root))['event_data']['task_path'],
                             str((Path(root) / 'project/main.yml').resolve()) + ':5')


@unittest.skipUnless(os.environ.get('JMS_EXECUTOR_TEST_HOST'), 'Requires a disposable SSH executor')
@override_settings(ANSIBLE_EXECUTION_BACKEND='ssh', DEBUG_ANSIBLE=False, DEBUG_DEV=False)
class SSHRunnerIntegrationTest(SimpleTestCase):
    def setUp(self):
        self.config = override_settings(
            ANSIBLE_EXECUTOR_HOST=os.environ['JMS_EXECUTOR_TEST_HOST'],
            ANSIBLE_EXECUTOR_PORT=int(os.environ['JMS_EXECUTOR_TEST_PORT']),
            ANSIBLE_EXECUTOR_PRIVATE_KEY=os.environ['JMS_EXECUTOR_TEST_KEY'],
            ANSIBLE_EXECUTOR_KNOWN_HOSTS=os.environ['JMS_EXECUTOR_TEST_KNOWN_HOSTS'],
        )
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.private = self.root / 'job'
        self.private.mkdir()
        # Same layout as JMSInventory.write_to_file: credentials alongside inventory.
        self.inventory = self.private / 'inventory.json'
        self.inventory.write_text(json.dumps({'all': {'hosts': {'executor_test': {
            'ansible_connection': 'local', 'ansible_python_interpreter': '/usr/bin/python3',
        }}}}))

    def test_current_adhoc_callback_receives_success_and_remote_pid_is_not_local(self):
        runner = AdHocRunner(str(self.inventory), 'shell', 'command', 'id -u',
                            project_dir=str(self.private))
        # Core's Ansible fork requires explicit trusted mode for local fixtures.
        runner.envs['ANSIBLE_SUPER_MODE'] = '1'
        callback = runner.run(quiet=True, clean_workspace=False)
        self.assertTrue(callback.is_success(), callback.result)
        self.assertTrue(callback.result['ok']['executor_test'])
        self.assertFalse((self.private / 'local.pid').exists())

    def test_current_playbook_runner_custom_module_and_failed_status(self):
        source = self.root / 'source'
        (source / 'modules').mkdir(parents=True)
        (source / 'modules/runtime_check.py').write_text('''#!/usr/bin/python3
from ansible.module_utils.basic import AnsibleModule
from pathlib import Path
import libs.ansible
m = AnsibleModule(argument_spec={})
assert (Path(libs.ansible.__file__).parent / 'modules/mssql_script.py').is_file()
m.exit_json(changed=False, msg='staged JumpServer runtime loaded')
''')
        playbook = source / 'main.yml'
        playbook.write_text(json.dumps([{'hosts': 'all', 'gather_facts': False, 'tasks': [
            {'runtime_check': {}}, {'ansible.builtin.command': '/bin/false'},
        ]}]))
        runner = PlaybookRunner(str(self.inventory), str(playbook), str(self.private))
        runner.envs['ANSIBLE_SUPER_MODE'] = '1'
        callback = runner.run(quiet=True)
        self.assertEqual(callback.status, 'failed')
        self.assertTrue(callback.result['ok']['executor_test'])
        self.assertTrue(callback.result['failures']['executor_test'])
        self.assertFalse(self.private.exists())

    def test_current_upload_runner_stages_files_and_returns_callback(self):
        job_id = uuid.uuid4()
        source = self.root / 'job_upload_file' / str(job_id)
        source.mkdir(parents=True)
        (source / 'payload.txt').write_text('upload-test')
        with override_settings(SHARE_DIR=str(self.root)):
            runner = UploadFileRunner(str(self.inventory), str(self.private), job_id,
                                      'jms-upload-test-' + str(job_id))
            runner.envs['ANSIBLE_SUPER_MODE'] = '1'
            callback = runner.run(quiet=True)
        self.assertTrue(callback.is_success(), callback.result)
        self.assertFalse(source.exists())

    def test_task_log_keeps_success_changed_and_failed_colors(self):
        from ops.ansible.callback import TaskLogCallback
        project = self.private / 'project'
        project.mkdir()
        playbook = project / 'main.yml'
        playbook.write_text(json.dumps([{'hosts': 'all', 'gather_facts': False, 'tasks': [
            {'ansible.builtin.debug': {'msg': 'COLOR_OK'}},
            {'ansible.builtin.command': '/bin/true'},
            {'ansible.builtin.command': '/bin/false'},
        ]}]))
        log = self.root / 'task.log'
        runner = PlaybookRunner(
            str(self.inventory), str(playbook), str(self.private),
            callback=TaskLogCallback(str(uuid.uuid4())),
        )
        runner.envs['ANSIBLE_SUPER_MODE'] = '1'
        with patch('ops.ansible.callback.get_ansible_task_log_path', return_value=str(log)):
            callback = runner.run(quiet=True)
        self.assertEqual(callback.status, 'failed')
        output = log.read_text()
        for color in ('32', '33', '31'):
            self.assertIn(f'\x1b[0;{color}m', output)

    def test_job_stop_cancels_the_running_task_through_its_directory(self):
        from ops.models.job import JobExecution
        runner = AdHocRunner(str(self.inventory), 'shell', 'command', 'sleep 60',
                             project_dir=str(self.private))
        runner.envs['ANSIBLE_SUPER_MODE'] = '1'
        original = runner.cb.event_handler
        stopped = []
        def event_handler(data):
            original(data)
            if data['event'] == 'runner_on_start':
                job = SimpleNamespace(private_dir=str(self.private), set_error=Mock())
                # Simulate a separate web process: no local registry notification.
                with patch('ops.signal_handlers.job_execution_stop_pub_sub'):
                    JobExecution.stop(job)
                stopped.append(True)
        runner.cb.event_handler = event_handler
        callback = runner.run(quiet=True)
        self.assertTrue(stopped)
        self.assertEqual(callback.status, 'canceled')
        self.assertFalse(self.private.exists())
