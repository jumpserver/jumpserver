import json
from unittest.mock import Mock, PropertyMock, patch

from ansible.parsing.dataloader import DataLoader
from ansible.parsing.splitter import parse_kv
from ansible.template import Templar
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from ops.ansible.exception import CommandInBlackListException
from ops.ansible.utils import escape_jinja2_syntax
from ops.models.job import Job, JobExecution


class JobVariablesTestCase(SimpleTestCase):
    def make_execution(self, args, parameters=None, module='shell'):
        job = Job(name='variable-job', args=args, module=module)
        return JobExecution(job=job, parameters=parameters or {})

    def render_ansible(self, value, variables=None):
        templar = Templar(loader=DataLoader(), variables=variables or {})
        return templar.template(value, disable_lookups=True)

    def test_parameters_and_static_variables_are_shared_without_mutating_input(self):
        parameters = {'jms_name': 'alice', 'jms_count': 0, 'jms_empty': None,
                      'jms_job_name': 'spoofed', 'ansible_connection': 'local',
                      'ANSIBLE_HOST': 'other-host'}
        execution = self.make_execution(
            '{{ jms_name }}:{{jms_count}}:{{jms_empty}}:{{jms_job_name}}', parameters,
        )

        self.assertEqual(execution.rendered_args, 'alice:0::variable-job')
        self.assertEqual(execution.extra_vars['jms_job_id'], str(execution.job.id))
        self.assertNotIn('ansible_connection', execution.extra_vars)
        self.assertNotIn('ANSIBLE_HOST', execution.extra_vars)
        self.assertEqual(parameters['jms_job_name'], 'spoofed')
        self.assertNotIn('jms_job_id', parameters)

    def test_json_parameters_and_missing_variable(self):
        execution = self.make_execution(
            'echo {{jms_name}}', json.dumps({'jms_name': 'alice'}),
        )
        self.assertEqual(execution.compile_shell(), ('shell', 'echo alice'))

        execution = self.make_execution('echo {{jms_missing}}')
        with self.assertRaisesMessage(ValueError, 'jms_missing'):
            execution.compile_shell()

    @patch('ops.models.job.AdHocRunner')
    @patch.object(Job, 'inventory', new_callable=PropertyMock)
    def test_runner_receives_the_same_parameters_used_to_render(self, inventory, runner):
        inventory.return_value.exclude_hosts = {}
        execution = self.make_execution('echo {{jms_name}}', {'jms_name': 'alice'})
        execution.date_created = timezone.now()

        self.assertIs(execution.get_runner(), runner.return_value)
        self.assertEqual(runner.call_args.kwargs['module_args'], 'echo alice')
        self.assertIs(runner.call_args.kwargs['extra_vars'], execution.extra_vars)
        self.assertEqual(runner.call_args.kwargs['execution_id'], execution.id)

    def test_variable_values_and_expressions_remain_literal(self):
        values = (
            '{{jms_other}}', '{{ 7 * 7 }}', "{{ lookup('pipe', 'id') }}",
            '{% if true %}text{% endif %}', '{# comment #}', '{{{ 7 * 7 }}}',
            '__TEMP_OPEN_BRACES__ __TEMP_CLOSE_BRACES__',
        )
        for value in values:
            with self.subTest(value=value):
                execution = self.make_execution(
                    'echo {{jms_value}}', {'jms_value': value, 'jms_other': 'expanded'},
                )
                _, args = execution.compile_shell()
                self.assertEqual(self.render_ansible(args), 'echo ' + value)

        execution = self.make_execution('echo {{ 7 * 7 }}')
        self.assertEqual(self.render_ansible(execution.compile_shell()[1]), execution.job.args)

    def test_jinja_header_cannot_change_delimiters(self):
        value = '#jinja2:variable_start_string:"[[",variable_end_string:"]]"\n[[ 7 * 7 ]]'
        self.assertEqual(self.render_ansible(escape_jinja2_syntax(value)), value)

    def test_all_adhoc_modules_receive_rendered_arguments(self):
        for module, expected_module, suffix in (
            ('shell', 'shell', ''), ('raw', 'raw', ''),
            ('win_shell', 'ansible.windows.win_shell', ''),
            ('python', 'shell', ' executable=python'),
            ('huawei', 'ce_command', ''),
        ):
            with self.subTest(module=module):
                execution = self.make_execution('echo {{jms_value}}', {'jms_value': 'alice'}, module)
                actual_module, args = execution.compile_shell()
                self.assertEqual(actual_module, expected_module)
                expected_args = 'commands="echo alice" ' if module == 'huawei' else 'echo alice' + suffix
                self.assertEqual(args, expected_args)

    def test_database_query_is_literal_but_login_variables_still_render(self):
        variables = {'login_host': 'db.example', 'login_user': 'user', 'login_password': 'secret',
                     'login_port': 3306, 'login_db': 'example',
                     'jms_asset': {'encryption': 'off', 'tds_version': '7.4'}}
        for module in ('mysql', 'postgresql', 'sqlserver'):
            with self.subTest(module=module):
                execution = self.make_execution(
                    'SELECT {{jms_value}}', {'jms_value': '{{ 7 * 7 }}'}, module,
                )
                _, args = execution.compile_shell()
                rendered = self.render_ansible(parse_kv(args), variables)
                key = 'script' if module == 'sqlserver' else 'query'
                self.assertEqual(rendered[key], 'SELECT {{ 7 * 7 }}')
                self.assertEqual(rendered['login_host'], 'db.example')

    @patch('ops.models.job.CommandExecutionAlert')
    def test_acl_rejects_the_rendered_command(self, alert):
        execution = self.make_execution('{{jms_command}}', {'jms_command': 'blocked-command'})
        acl = Mock()
        group = Mock()
        group.match.return_value = (True, None)
        acl.command_groups.all.return_value = [group]
        acl.is_action.side_effect = lambda action: action == 'reject'
        with patch.object(Job, 'assets') as assets:
            assets.all.return_value = []
            with self.assertRaisesMessage(Exception, 'command is rejected by ACL'):
                execution.match_command_group(acl, Mock())
        group.match.assert_called_once_with('blocked-command')
        alert.return_value.publish_async.assert_called_once()

    @override_settings(SECURITY_COMMAND_BLACKLIST=['blocked-command'])
    @patch('ops.models.job.CommandExecutionAlert')
    def test_blacklist_rejects_the_rendered_command(self, alert):
        execution = self.make_execution('{{jms_command}}', {'jms_command': 'blocked-command'})
        with patch.object(Job, 'assets') as assets:
            assets.all.return_value = []
            with self.assertRaisesMessage(CommandInBlackListException, 'blocked-command'):
                execution.check_command_acl()
        alert.return_value.publish_async.assert_called_once()
